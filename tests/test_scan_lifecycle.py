from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.lifecycle import (
    derive_scan_status,
    get_or_create_scanner_run,
    mark_scanner_run_completed,
    mark_scanner_run_failed,
    mark_scanner_run_running,
    refresh_scan_status,
)
from app.db.models import (
    Base,
    Repository,
    Scan,
    ScanStatus,
    ScannerName,
    ScannerRun,
    ScannerRunStatus,
    User,
)


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


def make_run(status: ScannerRunStatus) -> ScannerRun:
    return ScannerRun(scan_id=1, scanner_name=ScannerName.SEMGREP.value, status=status.value)


def test_scan_status_is_derived_from_scanner_runs() -> None:
    assert derive_scan_status([]) == ScanStatus.QUEUED
    assert derive_scan_status([make_run(ScannerRunStatus.QUEUED)]) == ScanStatus.QUEUED
    assert derive_scan_status([make_run(ScannerRunStatus.RUNNING)]) == ScanStatus.RUNNING
    assert derive_scan_status(
        [make_run(ScannerRunStatus.COMPLETED), make_run(ScannerRunStatus.COMPLETED)]
    ) == ScanStatus.COMPLETED
    assert derive_scan_status(
        [make_run(ScannerRunStatus.COMPLETED), make_run(ScannerRunStatus.FAILED)]
    ) == ScanStatus.PARTIAL
    assert derive_scan_status(
        [make_run(ScannerRunStatus.TIMEOUT), make_run(ScannerRunStatus.FAILED)]
    ) == ScanStatus.FAILED


@pytest.mark.asyncio
async def test_scanner_run_lifecycle_and_scan_status(db: AsyncSession) -> None:
    user = User(name="Owner", email="owner@example.com", password_hash="hash")
    db.add(user)
    await db.flush()
    repository = Repository(
        name="repo",
        github_url="https://github.com/example/repo",
        owner_id=user.id,
        default_branch="main",
    )
    db.add(repository)
    await db.flush()
    scan = Scan(repository_id=repository.id, requested_by=user.id, target_branch="main")
    db.add(scan)
    await db.flush()

    scanner_run = await get_or_create_scanner_run(
        db, scan_id=scan.id, scanner_name=ScannerName.SEMGREP
    )
    await mark_scanner_run_running(db, scanner_run=scanner_run)
    assert scanner_run.attempt_count == 1
    assert scanner_run.status == ScannerRunStatus.RUNNING.value
    assert await refresh_scan_status(db, scan=scan) == ScanStatus.RUNNING

    await mark_scanner_run_completed(db, scanner_run=scanner_run, finding_count=2)
    assert await refresh_scan_status(db, scan=scan) == ScanStatus.COMPLETED
    assert scan.completed_at is not None


@pytest.mark.asyncio
async def test_scanner_run_creation_is_idempotent(db: AsyncSession) -> None:
    user = User(name="Owner", email="owner@example.com", password_hash="hash")
    db.add(user)
    await db.flush()
    repository = Repository(
        name="repo",
        github_url="https://github.com/example/repo",
        owner_id=user.id,
    )
    db.add(repository)
    await db.flush()
    scan = Scan(repository_id=repository.id, requested_by=user.id, target_branch="main")
    db.add(scan)
    await db.flush()

    first = await get_or_create_scanner_run(
        db, scan_id=scan.id, scanner_name=ScannerName.GITLEAKS
    )
    second = await get_or_create_scanner_run(
        db, scan_id=scan.id, scanner_name=ScannerName.GITLEAKS
    )

    assert first.id == second.id


@pytest.mark.asyncio
async def test_failed_scanner_run_produces_partial_scan(db: AsyncSession) -> None:
    user = User(name="Owner", email="owner@example.com", password_hash="hash")
    db.add(user)
    await db.flush()
    repository = Repository(
        name="repo",
        github_url="https://github.com/example/repo",
        owner_id=user.id,
    )
    db.add(repository)
    await db.flush()
    scan = Scan(repository_id=repository.id, requested_by=user.id, target_branch="main")
    db.add(scan)
    await db.flush()
    scanner_run = ScannerRun(
        scan_id=scan.id,
        scanner_name=ScannerName.TRIVY.value,
        status=ScannerRunStatus.RUNNING.value,
    )
    db.add(scanner_run)
    await db.flush()

    await mark_scanner_run_failed(
        db,
        scanner_run=scanner_run,
        error_summary="scanner process exited unexpectedly",
    )
    assert await refresh_scan_status(db, scan=scan) == ScanStatus.FAILED

    successful_run = ScannerRun(
        scan_id=scan.id,
        scanner_name=ScannerName.SEMGREP.value,
        status=ScannerRunStatus.COMPLETED.value,
        finding_count=1,
    )
    db.add(successful_run)
    await db.flush()
    assert await refresh_scan_status(db, scan=scan) == ScanStatus.PARTIAL
