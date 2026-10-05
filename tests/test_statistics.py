from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import (
    Base,
    Finding,
    FindingCategory,
    FindingReviewStatus,
    Repository,
    Scan,
    ScanStatus,
    ScannerName,
    ScannerRun,
    ScannerRunStatus,
    User,
)
from app.db.statistics import UserStatistics, get_user_statistics


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


async def add_scan(
    db: AsyncSession,
    *,
    user: User,
    repository: Repository,
    status: ScanStatus,
    scan_number: int,
) -> tuple[Scan, ScannerRun]:
    scan = Scan(
        repository_id=repository.id,
        requested_by=user.id,
        status=status.value,
        target_branch="main",
    )
    db.add(scan)
    await db.flush()
    scanner_run = ScannerRun(
        scan_id=scan.id,
        scanner_name=f"{ScannerName.SEMGREP.value}" if scan_number == 1 else ScannerName.TRIVY.value,
        status=ScannerRunStatus.COMPLETED.value,
    )
    db.add(scanner_run)
    await db.flush()
    return scan, scanner_run


@pytest.mark.asyncio
async def test_statistics_are_scoped_to_one_user(db: AsyncSession) -> None:
    user = User(name="Owner", email="owner@example.com", password_hash="hash")
    other_user = User(name="Other", email="other@example.com", password_hash="hash")
    db.add_all([user, other_user])
    await db.flush()
    repository = Repository(
        name="owned-repo",
        github_url="https://github.com/example/owned-repo",
        owner_id=user.id,
    )
    other_repository = Repository(
        name="other-repo",
        github_url="https://github.com/example/other-repo",
        owner_id=other_user.id,
    )
    db.add_all([repository, other_repository])
    await db.flush()

    _, owned_run = await add_scan(
        db,
        user=user,
        repository=repository,
        status=ScanStatus.COMPLETED,
        scan_number=1,
    )
    await add_scan(
        db,
        user=user,
        repository=repository,
        status=ScanStatus.PARTIAL,
        scan_number=2,
    )
    await add_scan(
        db,
        user=other_user,
        repository=other_repository,
        status=ScanStatus.FAILED,
        scan_number=3,
    )
    db.add_all(
        [
            Finding(
                scanner_run_id=owned_run.id,
                category=FindingCategory.SECRET.value,
                rule_id="secret-1",
                title="Secret",
                description="Safe description",
                severity="CRITICAL",
                confidence="HIGH",
                recommendation="Rotate it",
                fingerprint="secret-1",
                review_status=FindingReviewStatus.OPEN.value,
            ),
            Finding(
                scanner_run_id=owned_run.id,
                category=FindingCategory.CODE.value,
                rule_id="code-1",
                title="Code",
                description="Safe description",
                severity="HIGH",
                confidence="HIGH",
                recommendation="Fix it",
                fingerprint="code-1",
                review_status=FindingReviewStatus.CONFIRMED.value,
            ),
        ]
    )
    await db.commit()

    statistics = await get_user_statistics(db, user_id=user.id)

    assert statistics == UserStatistics(
        total_repositories=1,
        total_scans=2,
        completed_scans=1,
        partial_scans=1,
        failed_scans=0,
        critical_findings=1,
        high_findings=1,
        open_findings=1,
    )


@pytest.mark.asyncio
async def test_statistics_for_user_without_data_are_zero(db: AsyncSession) -> None:
    user = User(name="Empty", email="empty@example.com", password_hash="hash")
    db.add(user)
    await db.commit()

    statistics = await get_user_statistics(db, user_id=user.id)

    assert statistics == UserStatistics(0, 0, 0, 0, 0, 0, 0, 0)
