from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import (
    Base,
    Confidence,
    Finding,
    FindingCategory,
    Repository,
    Scan,
    ScanStatus,
    ScannerName,
    ScannerRun,
    ScannerRunStatus,
    Severity,
    User,
)
from app.db.reports import aggregate_scan_findings, build_scan_report


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


async def create_scan(db: AsyncSession, *, name: str) -> Scan:
    user = User(name=f"{name} Owner", email=f"{name}@example.com", password_hash="hash")
    db.add(user)
    await db.flush()
    repository = Repository(
        name=name,
        github_url=f"https://github.com/example/{name}",
        owner_id=user.id,
    )
    db.add(repository)
    await db.flush()
    scan = Scan(
        repository_id=repository.id,
        requested_by=user.id,
        target_branch="main",
        status=ScanStatus.COMPLETED.value,
    )
    db.add(scan)
    await db.flush()
    return scan


def add_finding(db: AsyncSession, scanner_run_id: int, severity: Severity, index: int) -> None:
    db.add(
        Finding(
            scanner_run_id=scanner_run_id,
            category=FindingCategory.CODE.value,
            rule_id=f"rule-{index}",
            title=f"Finding {index}",
            description="Safe description",
            severity=severity.value,
            confidence=Confidence.HIGH.value,
            recommendation="Apply the documented remediation.",
            fingerprint=f"fingerprint-{index}",
        )
    )


@pytest.mark.asyncio
async def test_report_aggregates_only_one_scan(db: AsyncSession) -> None:
    first_scan = await create_scan(db, name="first")
    second_scan = await create_scan(db, name="second")
    first_run = ScannerRun(
        scan_id=first_scan.id,
        scanner_name=ScannerName.SEMGREP.value,
        status=ScannerRunStatus.COMPLETED.value,
    )
    second_run = ScannerRun(
        scan_id=second_scan.id,
        scanner_name=ScannerName.SEMGREP.value,
        status=ScannerRunStatus.COMPLETED.value,
    )
    db.add_all([first_run, second_run])
    await db.flush()
    add_finding(db, first_run.id, Severity.CRITICAL, 1)
    add_finding(db, first_run.id, Severity.MEDIUM, 2)
    add_finding(db, second_run.id, Severity.HIGH, 3)
    await db.commit()

    counts = await aggregate_scan_findings(db, scan_id=first_scan.id)

    assert counts == {
        "total_findings": 2,
        "critical_count": 1,
        "high_count": 0,
        "medium_count": 1,
        "low_count": 0,
    }


@pytest.mark.asyncio
async def test_report_persists_versioned_score_and_policy(db: AsyncSession) -> None:
    scan = await create_scan(db, name="report")
    scanner_run = ScannerRun(
        scan_id=scan.id,
        scanner_name=ScannerName.GITLEAKS.value,
        status=ScannerRunStatus.COMPLETED.value,
    )
    db.add(scanner_run)
    await db.flush()
    add_finding(db, scanner_run.id, Severity.CRITICAL, 1)
    add_finding(db, scanner_run.id, Severity.HIGH, 2)
    add_finding(db, scanner_run.id, Severity.LOW, 3)
    await db.commit()

    report = await build_scan_report(db, scan=scan)
    await db.commit()

    assert report.status == "READY"
    assert report.report_version == "risk-v1"
    assert report.total_findings == 3
    assert report.critical_count == 1
    assert report.high_count == 1
    assert report.low_count == 1
    assert report.risk_score == 61
    assert report.policy_status == "FAIL"


@pytest.mark.asyncio
async def test_report_generation_requires_terminal_scan(db: AsyncSession) -> None:
    scan = await create_scan(db, name="queued")
    scan.status = ScanStatus.RUNNING.value

    with pytest.raises(ValueError, match="terminal scans"):
        await build_scan_report(db, scan=scan)
