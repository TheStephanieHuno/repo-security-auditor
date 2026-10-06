import re
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Scan,
    ScanStatus,
    ScannerName,
    ScannerRun,
    ScannerRunStatus,
    utcnow,
)
from app.db.normalization import (
    NormalizedFinding,
    persist_normalized_findings,
    redact_sensitive_text,
)
from app.db.queries import get_owned_repository

TERMINAL_SCAN_STATUSES = frozenset(
    {
        ScanStatus.COMPLETED.value,
        ScanStatus.PARTIAL.value,
        ScanStatus.FAILED.value,
        ScanStatus.CANCELLED.value,
    }
)
TERMINAL_SCANNER_RUN_STATUSES = frozenset(
    {
        ScannerRunStatus.COMPLETED.value,
        ScannerRunStatus.FAILED.value,
        ScannerRunStatus.TIMEOUT.value,
        ScannerRunStatus.CANCELLED.value,
    }
)
MAX_ERROR_SUMMARY_LENGTH = 1000

_COMMIT_SHA_PATTERN = re.compile(r"[0-9a-f]{7,40}")


def derive_scan_status(scanner_runs: list[ScannerRun]) -> ScanStatus:
    if not scanner_runs or all(
        run.status == ScannerRunStatus.QUEUED.value for run in scanner_runs
    ):
        return ScanStatus.QUEUED

    statuses = {run.status for run in scanner_runs}
    if ScannerRunStatus.RUNNING.value in statuses:
        return ScanStatus.RUNNING

    completed = sum(
        run.status == ScannerRunStatus.COMPLETED.value for run in scanner_runs
    )
    terminal_failures = any(
        status in {
            ScannerRunStatus.FAILED.value,
            ScannerRunStatus.TIMEOUT.value,
            ScannerRunStatus.CANCELLED.value,
        }
        for status in statuses
    )

    if completed and terminal_failures:
        return ScanStatus.PARTIAL
    if completed == len(scanner_runs):
        return ScanStatus.COMPLETED
    if terminal_failures and completed == 0:
        return ScanStatus.FAILED
    return ScanStatus.RUNNING


async def create_scan_with_scanner_runs(
    db: AsyncSession,
    *,
    user_id: int,
    repository_id: int,
    target_branch: str,
    scanner_names: Sequence[ScannerName],
    commit_sha: str | None = None,
) -> Scan | None:
    """Create a QUEUED Scan with one QUEUED ScannerRun per scanner.

    Returns None when the repository is not owned by the user, so callers
    cannot distinguish a missing repository from another user's repository.
    """
    if not target_branch.strip():
        raise ValueError("target_branch must not be empty")
    unique_scanners = list(dict.fromkeys(scanner_names))
    if not unique_scanners:
        raise ValueError("at least one scanner is required")
    if commit_sha is not None and not _COMMIT_SHA_PATTERN.fullmatch(commit_sha):
        raise ValueError("commit_sha must be a lowercase hexadecimal git revision")

    repository = await get_owned_repository(
        db, user_id=user_id, repository_id=repository_id
    )
    if repository is None:
        return None

    scan = Scan(
        repository_id=repository.id,
        requested_by=user_id,
        status=ScanStatus.QUEUED.value,
        target_branch=target_branch.strip(),
        commit_sha=commit_sha,
    )
    scan.scanner_runs = [
        ScannerRun(scanner_name=name.value, status=ScannerRunStatus.QUEUED.value)
        for name in unique_scanners
    ]
    db.add(scan)
    await db.flush()
    return scan


async def get_or_create_scanner_run(
    db: AsyncSession,
    *,
    scan_id: int,
    scanner_name: ScannerName,
) -> ScannerRun:
    result = await db.execute(
        select(ScannerRun).where(
            ScannerRun.scan_id == scan_id,
            ScannerRun.scanner_name == scanner_name.value,
        )
    )
    scanner_run = result.scalar_one_or_none()
    if scanner_run is None:
        scanner_run = ScannerRun(
            scan_id=scan_id,
            scanner_name=scanner_name.value,
            status=ScannerRunStatus.QUEUED.value,
        )
        db.add(scanner_run)
        await db.flush()
    return scanner_run


async def mark_scan_running(
    db: AsyncSession, *, scan: Scan, started_at: datetime | None = None
) -> bool:
    """Claim a scan for processing.

    Returns False for a terminal scan so a duplicate or late delivery does not
    reprocess it. An already RUNNING scan stays claimable for worker retries.
    """
    if scan.status in TERMINAL_SCAN_STATUSES:
        return False
    if scan.status == ScanStatus.QUEUED.value:
        scan.status = ScanStatus.RUNNING.value
        scan.started_at = scan.started_at or started_at or utcnow()
        await db.flush()
    return True


async def refresh_scan_status(db: AsyncSession, *, scan: Scan) -> ScanStatus:
    if scan.status == ScanStatus.CANCELLED.value:
        # Cancellation is a user decision; late scanner results never override it.
        return ScanStatus.CANCELLED
    result = await db.execute(
        select(ScannerRun).where(ScannerRun.scan_id == scan.id)
    )
    status = derive_scan_status(list(result.scalars().all()))
    if (
        scan.status in TERMINAL_SCAN_STATUSES
        and status.value not in TERMINAL_SCAN_STATUSES
    ):
        # A terminal scan never regresses to QUEUED or RUNNING.
        return ScanStatus(scan.status)
    scan.status = status.value
    if status == ScanStatus.RUNNING:
        scan.started_at = scan.started_at or utcnow()
    if status.value in TERMINAL_SCAN_STATUSES:
        scan.completed_at = scan.completed_at or utcnow()
    await db.flush()
    return status


async def cancel_scan(
    db: AsyncSession, *, scan: Scan, cancelled_at: datetime | None = None
) -> bool:
    """Cancel a QUEUED or RUNNING scan and its unfinished scanner runs.

    Returns False when the scan is already terminal. Results from runs that
    already finished are kept.
    """
    if scan.status in TERMINAL_SCAN_STATUSES:
        return False
    timestamp = cancelled_at or utcnow()
    result = await db.execute(select(ScannerRun).where(ScannerRun.scan_id == scan.id))
    for run in result.scalars().all():
        if run.status not in TERMINAL_SCANNER_RUN_STATUSES:
            run.status = ScannerRunStatus.CANCELLED.value
            run.completed_at = timestamp
    scan.status = ScanStatus.CANCELLED.value
    scan.cancelled_at = timestamp
    await db.flush()
    return True


async def mark_scanner_run_running(
    db: AsyncSession, *, scanner_run: ScannerRun, started_at: datetime | None = None
) -> None:
    if scanner_run.status in TERMINAL_SCANNER_RUN_STATUSES:
        return
    scanner_run.status = ScannerRunStatus.RUNNING.value
    scanner_run.attempt_count += 1
    scanner_run.started_at = started_at or utcnow()
    await db.flush()


async def mark_scanner_run_completed(
    db: AsyncSession,
    *,
    scanner_run: ScannerRun,
    finding_count: int,
    completed_at: datetime | None = None,
) -> None:
    if finding_count < 0:
        raise ValueError("finding_count must be non-negative")
    if scanner_run.status in TERMINAL_SCANNER_RUN_STATUSES:
        return
    scanner_run.status = ScannerRunStatus.COMPLETED.value
    scanner_run.finding_count = finding_count
    scanner_run.completed_at = completed_at or utcnow()
    scanner_run.error_summary = None
    await db.flush()


async def mark_scanner_run_failed(
    db: AsyncSession,
    *,
    scanner_run: ScannerRun,
    error_summary: str,
    timed_out: bool = False,
    completed_at: datetime | None = None,
) -> None:
    if not error_summary.strip():
        raise ValueError("error_summary must not be empty")
    if scanner_run.status in TERMINAL_SCANNER_RUN_STATUSES:
        return
    scanner_run.status = (
        ScannerRunStatus.TIMEOUT.value
        if timed_out
        else ScannerRunStatus.FAILED.value
    )
    scanner_run.error_summary = error_summary
    scanner_run.completed_at = completed_at or utcnow()
    await db.flush()


async def _refresh_parent_scan(db: AsyncSession, scanner_run: ScannerRun) -> ScanStatus:
    scan = await db.get(Scan, scanner_run.scan_id)
    if scan is None:
        raise LookupError("scanner run has no parent scan")
    return await refresh_scan_status(db, scan=scan)


async def record_scanner_run_success(
    db: AsyncSession,
    *,
    scanner_run: ScannerRun,
    findings: list[NormalizedFinding],
    completed_at: datetime | None = None,
) -> ScanStatus:
    """Durably store a successful scanner result and return the derived scan status.

    Findings, Evidence, and the COMPLETED transition are written in one
    savepoint, so a failure leaves the run RUNNING with no partial rows.
    Repeating the call for a terminal run changes nothing.
    """
    if scanner_run.status in TERMINAL_SCANNER_RUN_STATUSES:
        return await _refresh_parent_scan(db, scanner_run)
    if scanner_run.status != ScannerRunStatus.RUNNING.value:
        raise ValueError("only a RUNNING scanner run can record a result")

    try:
        async with db.begin_nested():
            await persist_normalized_findings(
                db, scanner_run=scanner_run, findings=findings
            )
            await mark_scanner_run_completed(
                db,
                scanner_run=scanner_run,
                finding_count=scanner_run.finding_count,
                completed_at=completed_at,
            )
    except Exception:
        # The savepoint rollback expires the run; reload it here so the caller
        # can record the failure without an implicit lazy load.
        await db.refresh(scanner_run)
        raise
    return await _refresh_parent_scan(db, scanner_run)


async def record_scanner_run_failure(
    db: AsyncSession,
    *,
    scanner_run: ScannerRun,
    error_summary: str,
    timed_out: bool = False,
    completed_at: datetime | None = None,
) -> ScanStatus:
    """Durably store a FAILED or TIMEOUT result and return the derived scan status.

    The error summary is redacted and truncated before persistence, because
    scanner diagnostics can echo repository content.
    """
    safe_summary = redact_sensitive_text(
        error_summary, max_length=MAX_ERROR_SUMMARY_LENGTH
    )
    await mark_scanner_run_failed(
        db,
        scanner_run=scanner_run,
        error_summary=safe_summary or "",
        timed_out=timed_out,
        completed_at=completed_at,
    )
    return await _refresh_parent_scan(db, scanner_run)
