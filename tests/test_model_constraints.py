from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import (
    Base,
    Finding,
    FindingCategory,
    FindingReviewStatus,
    Repository,
    Scan,
    ScannerName,
    ScannerRun,
    Severity,
    User,
)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def create_user_and_repository(
    db: AsyncSession,
    *,
    email: str = "owner@example.com",
    github_url: str = "https://github.com/example/repository",
) -> tuple[User, Repository]:
    user = User(name="Repository Owner", email=email, password_hash="test-hash")
    db.add(user)
    await db.flush()

    repository = Repository(
        name="repository",
        github_url=github_url,
        owner_id=user.id,
        default_branch="main",
    )
    db.add(repository)
    await db.flush()
    return user, repository


@pytest.mark.asyncio
async def test_duplicate_repository_url_is_allowed_for_different_users(
    db: AsyncSession,
) -> None:
    _, first_repository = await create_user_and_repository(db)
    second_user = User(
        name="Second Owner",
        email="second@example.com",
        password_hash="test-hash",
    )
    db.add(second_user)
    await db.flush()

    second_repository = Repository(
        name="repository",
        github_url=first_repository.github_url,
        owner_id=second_user.id,
    )
    db.add(second_repository)
    await db.commit()


@pytest.mark.asyncio
async def test_duplicate_repository_url_is_rejected_for_same_user(
    db: AsyncSession,
) -> None:
    _, repository = await create_user_and_repository(db)
    duplicate = Repository(
        name="duplicate",
        github_url=repository.github_url,
        owner_id=repository.owner_id,
    )
    db.add(duplicate)

    with pytest.raises(IntegrityError):
        await db.commit()


@pytest.mark.asyncio
async def test_invalid_scan_status_is_rejected(db: AsyncSession) -> None:
    user, repository = await create_user_and_repository(db)
    db.add(
        Scan(
            repository_id=repository.id,
            requested_by=user.id,
            status="INVALID",
            target_branch="main",
        )
    )

    with pytest.raises(IntegrityError):
        await db.commit()


@pytest.mark.asyncio
async def test_scanner_run_is_unique_per_scan_and_scanner(db: AsyncSession) -> None:
    user, repository = await create_user_and_repository(db)
    scan = Scan(repository_id=repository.id, requested_by=user.id, target_branch="main")
    db.add(scan)
    await db.flush()

    db.add_all(
        [
            ScannerRun(
                scan_id=scan.id,
                scanner_name=ScannerName.SEMGREP,
            ),
            ScannerRun(
                scan_id=scan.id,
                scanner_name=ScannerName.SEMGREP,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db.commit()


@pytest.mark.asyncio
async def test_finding_line_range_must_be_valid(db: AsyncSession) -> None:
    user, repository = await create_user_and_repository(db)
    scan = Scan(repository_id=repository.id, requested_by=user.id, target_branch="main")
    db.add(scan)
    await db.flush()
    scanner_run = ScannerRun(scan_id=scan.id, scanner_name=ScannerName.SEMGREP)
    db.add(scanner_run)
    await db.flush()

    db.add(
        Finding(
            scanner_run_id=scanner_run.id,
            category=FindingCategory.CODE,
            rule_id="rule-1",
            title="Invalid range",
            description="Test finding",
            severity=Severity.HIGH,
            confidence="HIGH",
            recommendation="Fix it",
            file_path="src/example.py",
            line_start=20,
            line_end=10,
            fingerprint="fingerprint-1",
            review_status=FindingReviewStatus.OPEN,
        )
    )

    with pytest.raises(IntegrityError):
        await db.commit()
