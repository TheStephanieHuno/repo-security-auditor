import uuid
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select

from backend_app_test.db.session import AsyncSessionLocal
from backend_app_test.db.models import Scan as DBScan, Finding as DBFinding
from backend_app_test.services.scanner.runner import run_full_security_scan
from backend_app_test.services.scanner.normalizer import normalize_scanner_findings
from backend_app_test.workers.queue import redis_settings

logger = logging.getLogger(__name__)

async def process_scan_job(ctx: dict, scan_id_str: str, repo_url: str, branch: str, repository_id_str: str):
    """
    ARQ Background Task / Worker Job handler.
    Pulls job from Redis, executes orchestrator, and persists normalized findings to PostgreSQL/SQLite.
    """
    scan_id = uuid.UUID(scan_id_str)
    repository_id = uuid.UUID(repository_id_str)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Update status to 'running'
            result = await db.execute(select(DBScan).where(DBScan.id == scan_id))
            scan = result.scalar_one_or_none()
            if not scan or scan.status == "cancelled":
                logger.info(f"Scan {scan_id} was cancelled before starting.")
                return

            scan.status = "running"
            scan.started_at = datetime.now(timezone.utc)
            scan.progress = 10
            await db.commit()

            # 2. Progress callback to update live database progress
            async def update_progress(pct: int):
                async with AsyncSessionLocal() as sub_db:
                    sub_scan = (await sub_db.execute(select(DBScan).where(DBScan.id == scan_id))).scalar_one_or_none()
                    if sub_scan and sub_scan.status != "cancelled":
                        sub_scan.progress = pct
                        await sub_db.commit()

            # 3. Execute runner
            raw_findings = await run_full_security_scan(repo_url, branch, progress_callback=update_progress)

            # 4. Check if scan was cancelled mid-flight
            await db.refresh(scan)
            if scan.status == "cancelled":
                logger.info(f"Scan {scan_id} was cancelled during execution. Discarding partial findings.")
                return

            # 5. Normalize raw scanner outputs into DBFinding models
            normalized_findings = normalize_scanner_findings(raw_findings, scan_id, repository_id)
            for f in normalized_findings:
                db.add(f)

            # 6. Mark scan completed
            scan.status = "completed"
            scan.progress = 100
            scan.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Scan {scan_id} completed successfully with {len(normalized_findings)} findings.")

        except Exception as e:
            logger.exception(f"Scan {scan_id} execution failed: {e}")
            try:
                result = await db.execute(select(DBScan).where(DBScan.id == scan_id))
                scan = result.scalar_one_or_none()
                if scan and scan.status != "cancelled":
                    scan.status = "failed"
                    scan.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass


class WorkerSettings:
    """Configuration class for running ARQ worker process: arq backend_app_test.workers.scan_worker.WorkerSettings"""
    functions = [process_scan_job]
    redis_settings = redis_settings
    max_jobs = 10
    job_timeout = 360