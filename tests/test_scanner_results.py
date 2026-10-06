from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import lifecycle
from app.db.lifecycle import (
    create_scan_with_scanner_runs,
    mark_scan_running,
    mark_scanner_run_running,
    record_scanner_run_failure,
    record_scanner_run_success,
)
from app.db.models import (
    Base,
    Confidence,
    Evidence,
    EvidenceType,
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
from app.db.normalization import NormalizedEvidence, NormalizedFinding


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


def make_finding(
    *, fingerprint: str = "fingerprint-1", file_path: str = "src/app.py"
) -> NormalizedFinding:
    return NormalizedFinding(
        category=FindingCategory.CODE,
        source_scanner=ScannerName.SEMGREP.value,
        rule_id="python.lang.security.eval",
        title="Use of eval",
        description="Untrusted input reaches eval.",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        recommendation="Avoid eval on untrusted input.",
        fingerprint=fingerprint,
        file_path=file_path,
        line_start=10,
        line_end=10,
        evidence=(
            NormalizedEvidence(
                evidence_type=EvidenceType.CODE,
                file_path=file_path,
                line_start=10,
                line_end=10,
                code_snippet="eval(user_input)",
            ),
        ),
    )


async def create_running_scan(
    db: AsyncSession, scanner_names: list[ScannerName]
) -> tuple[Scan, dict[str, ScannerRun]]:
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
    scan = await create_scan_with_scanner_runs(
        db,
        user_id=user.id,
        repository_id=repository.id,
        target_branch="main",
        scanner_names=scanner_names,
    )
    assert scan is not None
    assert await mark_scan_running(db, scan=scan) is True
    runs = {run.scanner_name: run for run in scan.scanner_runs}
    for run in runs.values():
        await mark_scanner_run_running(db, scanner_run=run)
    return scan, runs


async def count(db: AsyncSession, model: type) -> int:
    return await db.scalar(select(func.count()).select_from(model)) or 0


@pytest.mark.asyncio
async def test_all_successful_runs_complete_the_scan(db: AsyncSession) -> None:
    """T-021: all ScannerRuns succeed -> Scan COMPLETED."""
    scan, runs = await create_running_scan(db, [ScannerName.SEMGREP, ScannerName.TRIVY])

    status = await record_scanner_run_success(
        db, scanner_run=runs["SEMGREP"], findings=[make_finding()]
    )
    assert status == ScanStatus.RUNNING
    status = await record_scanner_run_success(db, scanner_run=runs["TRIVY"], findings=[])

    assert status == ScanStatus.COMPLETED
    assert scan.status == ScanStatus.COMPLETED.value
    assert scan.completed_at is not None
    assert runs["SEMGREP"].finding_count == 1
    assert runs["TRIVY"].status == ScannerRunStatus.COMPLETED.value
    assert runs["TRIVY"].finding_count == 0
    assert await count(db, Evidence) == 1


@pytest.mark.asyncio
async def test_timeout_with_success_is_partial_and_keeps_findings(db: AsyncSession) -> None:
    """T-022: one timeout plus one success -> PARTIAL; successful findings preserved."""
    scan, runs = await create_running_scan(db, [ScannerName.SEMGREP, ScannerName.TRIVY])

    await record_scanner_run_success(
        db, scanner_run=runs["SEMGREP"], findings=[make_finding()]
    )
    status = await record_scanner_run_failure(
        db,
        scanner_run=runs["TRIVY"],
        error_summary="scanner exceeded the time limit",
        timed_out=True,
    )

    assert status == ScanStatus.PARTIAL
    assert runs["TRIVY"].status == ScannerRunStatus.TIMEOUT.value
    assert await count(db, Finding) == 1


@pytest.mark.asyncio
async def test_all_failed_runs_fail_the_scan(db: AsyncSession) -> None:
    """T-023: all ScannerRuns fail -> Scan FAILED."""
    scan, runs = await create_running_scan(db, [ScannerName.SEMGREP, ScannerName.GITLEAKS])

    await record_scanner_run_failure(
        db, scanner_run=runs["SEMGREP"], error_summary="malformed scanner output"
    )
    status = await record_scanner_run_failure(
        db, scanner_run=runs["GITLEAKS"], error_summary="scanner exited with code 2"
    )

    assert status == ScanStatus.FAILED
    assert scan.completed_at is not None


@pytest.mark.asyncio
async def test_duplicate_result_delivery_creates_no_duplicates(db: AsyncSession) -> None:
    """T-024: repeating a result write does not duplicate rows or findings."""
    scan, runs = await create_running_scan(db, [ScannerName.SEMGREP])
    run = runs["SEMGREP"]
    findings = [make_finding(), make_finding(fingerprint="fingerprint-2")]

    await record_scanner_run_success(db, scanner_run=run, findings=findings)
    status = await record_scanner_run_success(db, scanner_run=run, findings=findings)

    assert status == ScanStatus.COMPLETED
    assert await count(db, Finding) == 2
    assert await count(db, Evidence) == 2
    assert run.finding_count == 2


@pytest.mark.asyncio
async def test_retry_increments_attempt_count(db: AsyncSession) -> None:
    """T-025 persistence side: each RUNNING claim of a retried run counts an attempt."""
    _, runs = await create_running_scan(db, [ScannerName.CHECKOV])
    run = runs["CHECKOV"]
    assert run.attempt_count == 1

    await mark_scanner_run_running(db, scanner_run=run)
    assert run.attempt_count == 2


@pytest.mark.asyncio
async def test_terminal_scan_does_not_regress(db: AsyncSession) -> None:
    """T-026: a terminal scan or run never moves back to QUEUED or RUNNING."""
    scan, runs = await create_running_scan(db, [ScannerName.SEMGREP])
    run = runs["SEMGREP"]
    await record_scanner_run_success(db, scanner_run=run, findings=[])
    completed_at = scan.completed_at

    assert await mark_scan_running(db, scan=scan) is False
    await mark_scanner_run_running(db, scanner_run=run)
    status = await record_scanner_run_failure(
        db, scanner_run=run, error_summary="late duplicate failure"
    )

    assert status == ScanStatus.COMPLETED
    assert scan.status == ScanStatus.COMPLETED.value
    assert scan.completed_at == completed_at
    assert run.status == ScannerRunStatus.COMPLETED.value
    assert run.attempt_count == 1
    assert run.error_summary is None

    # A late extra run added to a terminal scan cannot drag it back to RUNNING.
    late_run = ScannerRun(
        scan_id=scan.id,
        scanner_name=ScannerName.TRIVY.value,
        status=ScannerRunStatus.RUNNING.value,
    )
    db.add(late_run)
    await db.flush()
    assert await record_scanner_run_failure(
        db, scanner_run=late_run, error_summary="late run failed"
    ) == ScanStatus.PARTIAL
    assert scan.status == ScanStatus.PARTIAL.value


@pytest.mark.asyncio
async def test_invalid_result_leaves_no_partial_rows(db: AsyncSession) -> None:
    """A traversal path in one finding rolls back the whole result write."""
    scan, runs = await create_running_scan(db, [ScannerName.SEMGREP])
    run = runs["SEMGREP"]

    with pytest.raises(ValueError):
        await record_scanner_run_success(
            db,
            scanner_run=run,
            findings=[
                make_finding(),
                make_finding(fingerprint="bad", file_path="../../etc/passwd"),
            ],
        )

    assert await count(db, Finding) == 0
    assert await count(db, Evidence) == 0
    assert run.status == ScannerRunStatus.RUNNING.value
    assert scan.status == ScanStatus.RUNNING.value


@pytest.mark.asyncio
async def test_database_error_rolls_back_result_and_allows_failure(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A database error mid-write keeps successful-scanner data out and the run usable."""
    scan, runs = await create_running_scan(db, [ScannerName.SEMGREP])
    run = runs["SEMGREP"]

    async def fail_completion(db: AsyncSession, **_: object) -> None:
        raise RuntimeError("database connection lost")

    monkeypatch.setattr(lifecycle, "mark_scanner_run_completed", fail_completion)
    with pytest.raises(RuntimeError):
        await record_scanner_run_success(db, scanner_run=run, findings=[make_finding()])
    monkeypatch.undo()

    assert await count(db, Finding) == 0
    assert run.status == ScannerRunStatus.RUNNING.value
    assert run.finding_count == 0

    status = await record_scanner_run_failure(
        db, scanner_run=run, error_summary="result persistence failed"
    )
    assert status == ScanStatus.FAILED
    assert scan.status == ScanStatus.FAILED.value


@pytest.mark.asyncio
async def test_result_requires_running_run(db: AsyncSession) -> None:
    user = User(name="Owner", email="owner@example.com", password_hash="hash")
    db.add(user)
    await db.flush()
    repository = Repository(
        name="repo", github_url="https://github.com/example/repo", owner_id=user.id
    )
    db.add(repository)
    await db.flush()
    scan = await create_scan_with_scanner_runs(
        db,
        user_id=user.id,
        repository_id=repository.id,
        target_branch="main",
        scanner_names=[ScannerName.SEMGREP],
    )
    assert scan is not None

    with pytest.raises(ValueError):
        await record_scanner_run_success(
            db, scanner_run=scan.scanner_runs[0], findings=[]
        )


@pytest.mark.asyncio
async def test_failure_summary_is_redacted_and_bounded(db: AsyncSession) -> None:
    _, runs = await create_running_scan(db, [ScannerName.GITLEAKS])
    run = runs["GITLEAKS"]

    await record_scanner_run_failure(
        db,
        scanner_run=run,
        error_summary="parse error near token=ghp_supersecretvalue " + "x" * 5000,
    )

    assert run.error_summary is not None
    assert "ghp_supersecretvalue" not in run.error_summary
    assert len(run.error_summary) <= 1000
    with pytest.raises(ValueError):
        await record_scanner_run_failure(
            db, scanner_run=run, error_summary="   "
        )
