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


async def refresh_scan_status(db: AsyncSession, *, scan: Scan) -> ScanStatus:
    result = await db.execute(
        select(ScannerRun).where(ScannerRun.scan_id == scan.id)
    )
    status = derive_scan_status(list(result.scalars().all()))
    scan.status = status.value
    if status in {
        ScanStatus.COMPLETED,
        ScanStatus.PARTIAL,
        ScanStatus.FAILED,
    }:
        scan.completed_at = scan.completed_at or utcnow()
    await db.flush()
    return status


async def mark_scanner_run_running(
    db: AsyncSession, *, scanner_run: ScannerRun, started_at: datetime | None = None
) -> None:
    if scanner_run.status in {
        ScannerRunStatus.COMPLETED.value,
        ScannerRunStatus.FAILED.value,
        ScannerRunStatus.TIMEOUT.value,
    }:
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
    if scanner_run.status in {
        ScannerRunStatus.COMPLETED.value,
        ScannerRunStatus.FAILED.value,
        ScannerRunStatus.TIMEOUT.value,
    }:
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
    if scanner_run.status in {
        ScannerRunStatus.COMPLETED.value,
        ScannerRunStatus.FAILED.value,
        ScannerRunStatus.TIMEOUT.value,
    }:
        return
    scanner_run.status = (
        ScannerRunStatus.TIMEOUT.value
        if timed_out
        else ScannerRunStatus.FAILED.value
    )
    scanner_run.error_summary = error_summary
    scanner_run.completed_at = completed_at or utcnow()
    await db.flush()
