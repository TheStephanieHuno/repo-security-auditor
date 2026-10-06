from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.lifecycle import (
    create_scan_with_scanner_runs,
    mark_scan_running,
    mark_scanner_run_running,
    record_scanner_run_success,
)
from app.db.models import (
    Base,
    Repository,
    ScanStatus,
    ScannerName,
    ScannerRun,
    ScannerRunStatus,
    User,
)
from app.db.queries import (
    get_latest_repository_scan,
    get_owned_scan_progress,
    list_repository_scans,
    list_scan_scanner_runs,
)

ALL_SCANNERS = [
    ScannerName.SEMGREP,
    ScannerName.GITLEAKS,
    ScannerName.TRIVY,
    ScannerName.CHECKOV,
]


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def create_owner_and_repository(
    db: AsyncSession, *, email: str
) -> tuple[User, Repository]:
    user = User(name="Owner", email=email, password_hash="hash")
    db.add(user)
    await db.flush()
    repository = Repository(
        name="repo",
        github_url=f"https://github.com/example/{email.split('@')[0]}",
        owner_id=user.id,
        default_branch="main",
    )
    db.add(repository)
    await db.flush()
    return user, repository


@pytest.mark.asyncio
async def test_scan_creation_creates_one_queued_run_per_scanner(db: AsyncSession) -> None:
    """T-019: Scan creates ScannerRuns, one current row per scanner."""
    user, repository = await create_owner_and_repository(db, email="owner@example.com")

    scan = await create_scan_with_scanner_runs(
        db,
        user_id=user.id,
        repository_id=repository.id,
        target_branch="main",
        scanner_names=[*ALL_SCANNERS, ScannerName.SEMGREP],
    )

    assert scan is not None
    assert scan.status == ScanStatus.QUEUED.value
    runs = await list_scan_scanner_runs(db, user_id=user.id, scan_id=scan.id)
    assert sorted(run.scanner_name for run in runs) == sorted(s.value for s in ALL_SCANNERS)
    assert all(run.status == ScannerRunStatus.QUEUED.value for run in runs)
    assert all(run.attempt_count == 0 for run in runs)


@pytest.mark.asyncio
async def test_scan_creation_rejects_unowned_repository_and_invalid_input(
    db: AsyncSession,
) -> None:
    owner, repository = await create_owner_and_repository(db, email="owner@example.com")
    intruder, _ = await create_owner_and_repository(db, email="intruder@example.com")

    assert (
        await create_scan_with_scanner_runs(
            db,
            user_id=intruder.id,
            repository_id=repository.id,
            target_branch="main",
            scanner_names=ALL_SCANNERS,
        )
        is None
    )
    with pytest.raises(ValueError):
        await create_scan_with_scanner_runs(
            db,
            user_id=owner.id,
            repository_id=repository.id,
            target_branch="main",
            scanner_names=[],
        )
    with pytest.raises(ValueError):
        await create_scan_with_scanner_runs(
            db,
            user_id=owner.id,
            repository_id=repository.id,
            target_branch="   ",
            scanner_names=ALL_SCANNERS,
        )
    with pytest.raises(ValueError):
        await create_scan_with_scanner_runs(
            db,
            user_id=owner.id,
            repository_id=repository.id,
            target_branch="main",
            scanner_names=ALL_SCANNERS,
            commit_sha="main; rm -rf /",
        )
    run_count = await db.scalar(select(func.count()).select_from(ScannerRun))
    assert run_count == 0


@pytest.mark.asyncio
async def test_scan_progress_is_owner_scoped(db: AsyncSession) -> None:
    """T-020 persistence side: a claimed scan reports RUNNING progress to its owner only."""
    owner, repository = await create_owner_and_repository(db, email="owner@example.com")
    intruder, _ = await create_owner_and_repository(db, email="intruder@example.com")
    scan = await create_scan_with_scanner_runs(
        db,
        user_id=owner.id,
        repository_id=repository.id,
        target_branch="main",
        scanner_names=[ScannerName.SEMGREP],
    )
    assert scan is not None

    assert await mark_scan_running(db, scan=scan) is True
    assert scan.status == ScanStatus.RUNNING.value
    assert scan.started_at is not None

    db.expunge_all()
    progress = await get_owned_scan_progress(db, user_id=owner.id, scan_id=scan.id)
    assert progress is not None
    assert progress.status == ScanStatus.RUNNING.value
    # Eagerly loaded, so reading runs outside the query does not lazy-load.
    assert [run.scanner_name for run in progress.scanner_runs] == ["SEMGREP"]

    assert await get_owned_scan_progress(db, user_id=intruder.id, scan_id=scan.id) is None
    assert await list_scan_scanner_runs(db, user_id=intruder.id, scan_id=scan.id) == []


@pytest.mark.asyncio
async def test_scan_history_preserves_previous_scans(db: AsyncSession) -> None:
    """T-027: completing a new scan leaves earlier scans unchanged."""
    owner, repository = await create_owner_and_repository(db, email="owner@example.com")
    intruder, _ = await create_owner_and_repository(db, email="intruder@example.com")

    first = await create_scan_with_scanner_runs(
        db,
        user_id=owner.id,
        repository_id=repository.id,
        target_branch="main",
        scanner_names=[ScannerName.SEMGREP],
    )
    assert first is not None
    first_run = (await list_scan_scanner_runs(db, user_id=owner.id, scan_id=first.id))[0]
    await mark_scan_running(db, scan=first)
    await mark_scanner_run_running(db, scanner_run=first_run)
    await record_scanner_run_success(db, scanner_run=first_run, findings=[])
    first_completed_at = first.completed_at

    second = await create_scan_with_scanner_runs(
        db,
        user_id=owner.id,
        repository_id=repository.id,
        target_branch="develop",
        scanner_names=[ScannerName.GITLEAKS],
    )
    assert second is not None

    history = await list_repository_scans(
        db, user_id=owner.id, repository_id=repository.id
    )
    assert [scan.id for scan in history] == [second.id, first.id]
    assert history[1].status == ScanStatus.COMPLETED.value
    assert history[1].completed_at == first_completed_at
    assert history[1].target_branch == "main"

    latest = await get_latest_repository_scan(
        db, user_id=owner.id, repository_id=repository.id
    )
    assert latest is not None and latest.id == second.id

    completed = await list_repository_scans(
        db,
        user_id=owner.id,
        repository_id=repository.id,
        status=ScanStatus.COMPLETED,
    )
    assert [scan.id for scan in completed] == [first.id]

    page = await list_repository_scans(
        db, user_id=owner.id, repository_id=repository.id, limit=1, offset=1
    )
    assert [scan.id for scan in page] == [first.id]

    assert (
        await list_repository_scans(db, user_id=intruder.id, repository_id=repository.id)
        == []
    )
    assert (
        await get_latest_repository_scan(
            db, user_id=intruder.id, repository_id=repository.id
        )
        is None
    )
    with pytest.raises(ValueError):
        await list_repository_scans(
            db, user_id=owner.id, repository_id=repository.id, limit=0
        )
