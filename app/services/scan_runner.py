"""Background scan execution (SRS FR-04, FR-05, NFR-02, NFR-03, NFR-04).

``run_scan_job`` is the unit of work a queue worker executes for one scan. It
is idempotent: a duplicate delivery for a terminal or cancelled scan does
nothing, and each scanner's result is recorded independently so one failure
never discards another scanner's findings.

``InProcessScanDispatcher`` runs jobs as asyncio tasks inside the API
process. A Celery-backed dispatcher can replace it without touching callers.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.lifecycle import (
    TERMINAL_SCANNER_RUN_STATUSES,
    mark_scan_running,
    mark_scanner_run_running,
    record_scanner_run_failure,
    record_scanner_run_success,
)
from app.db.models import Repository, Scan, ScannerRun, ScanStatus
from app.db.session import AsyncSessionLocal
from app.scanners import CheckResult, CheckStatus, SecurityCheck, default_checks, run_checks
from app.scanners.base import CheckError
from app.services.ai_service import AIService, ai_explanations_enabled
from app.services.reporting import generate_report
from app.services.workspace import repository_workspace

logger = logging.getLogger(__name__)

SCAN_TIMEOUT_SECONDS = float(os.getenv("SCAN_TIMEOUT_SECONDS", "300"))

WorkspaceFactory = Callable[[str, str, str | None], AbstractAsyncContextManager[Path]]


def _default_workspace(url: str, branch: str, commit_sha: str | None) -> AbstractAsyncContextManager[Path]:
    return repository_workspace(url, branch, commit_sha=commit_sha)


def _default_ai() -> AIService | None:
    return AIService() if ai_explanations_enabled() else None


def _failed_results(checks: list[SecurityCheck], status: CheckStatus, summary: str) -> list[CheckResult]:
    return [CheckResult(scanner=check.name, status=status, error_summary=summary) for check in checks]


async def _scan(
    url: str,
    branch: str,
    commit_sha: str | None,
    checks: list[SecurityCheck],
    workspace_factory: WorkspaceFactory,
) -> list[CheckResult]:
    async with workspace_factory(url, branch, commit_sha) as workspace:
        return await run_checks(checks, workspace)


async def run_scan_job(
    scan_id: int,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    checks_factory: Callable[[], list[SecurityCheck]] = default_checks,
    workspace_factory: WorkspaceFactory = _default_workspace,
    ai_factory: Callable[[], AIService | None] = _default_ai,
    timeout_seconds: float = SCAN_TIMEOUT_SECONDS,
) -> None:
    sessions = session_factory or AsyncSessionLocal

    # 1. Claim the scan and mark its runs RUNNING, committed so progress is visible.
    async with sessions() as db:
        scan = await db.get(Scan, scan_id)
        if scan is None or not await mark_scan_running(db, scan=scan):
            return
        repository = await db.get(Repository, scan.repository_id)
        runs = list(
            (await db.execute(select(ScannerRun).where(ScannerRun.scan_id == scan_id))).scalars()
        )
        pending = [run for run in runs if run.status not in TERMINAL_SCANNER_RUN_STATUSES]
        for run in pending:
            await mark_scanner_run_running(db, scanner_run=run)
        await db.commit()
        url, branch, commit_sha = repository.github_url, scan.target_branch, scan.commit_sha
        wanted = {run.scanner_name for run in pending}

    available = {check.name.value: check for check in checks_factory()}
    checks = [available[name] for name in sorted(wanted) if name in available]
    results: list[CheckResult] = []

    # 2. Run the checks in an isolated workspace under the wall-clock limit.
    if checks:
        try:
            results = await asyncio.wait_for(
                _scan(url, branch, commit_sha, checks, workspace_factory), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            results = _failed_results(
                checks, CheckStatus.TIMEOUT, f"scan exceeded the {timeout_seconds:.0f}s limit"
            )
        except CheckError as error:  # workspace preparation failed
            results = _failed_results(checks, CheckStatus.FAILED, str(error))
        except Exception:
            logger.exception("scan %s failed before scanners ran", scan_id)
            results = _failed_results(checks, CheckStatus.FAILED, "scan failed with an internal error")

    # 3. Record every result independently.
    async with sessions() as db:
        runs_by_name = {
            run.scanner_name: run
            for run in (
                await db.execute(select(ScannerRun).where(ScannerRun.scan_id == scan_id))
            ).scalars()
        }
        for result in results:
            run = runs_by_name.get(result.scanner.value)
            if run is None:
                continue
            if result.status == CheckStatus.COMPLETED:
                try:
                    await record_scanner_run_success(db, scanner_run=run, findings=list(result.findings))
                    continue
                except ValueError:
                    logger.warning("scanner %s returned findings that failed validation", run.scanner_name)
                    summary = "scanner output failed validation"
                    timed_out = False
            else:
                summary = result.error_summary or "scanner failed"
                timed_out = result.status == CheckStatus.TIMEOUT
            await record_scanner_run_failure(
                db, scanner_run=run, error_summary=summary, timed_out=timed_out
            )
        for name in wanted - set(available):
            await record_scanner_run_failure(
                db, scanner_run=runs_by_name[name], error_summary="scanner is not installed on this worker"
            )
        await db.commit()

        # 4. Report and AI explanations; failures here never change scan results.
        scan = await db.get(Scan, scan_id)
        if scan is None or scan.status not in {ScanStatus.COMPLETED.value, ScanStatus.PARTIAL.value}:
            return
        ai = ai_factory()
        try:
            await generate_report(db, scan=scan, ai=ai)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("report generation failed for scan %s", scan_id)
            return
        if ai is not None:
            try:
                await ai.explain_scan_findings(db, scan_id=scan_id)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("AI explanations failed for scan %s", scan_id)


class ScanDispatcher(Protocol):
    def dispatch(self, scan_id: int) -> None: ...


class InProcessScanDispatcher:
    """Runs scan jobs as asyncio tasks in the API process."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def dispatch(self, scan_id: int) -> None:
        task = asyncio.create_task(run_scan_job(scan_id), name=f"scan-{scan_id}")
        self._tasks.add(task)
        task.add_done_callback(self._finished)

    def _finished(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("scan task %s crashed", task.get_name(), exc_info=task.exception())


_dispatcher = InProcessScanDispatcher()


def get_scan_dispatcher() -> ScanDispatcher:
    """FastAPI dependency; override in tests or swap for a Celery dispatcher."""
    return _dispatcher
