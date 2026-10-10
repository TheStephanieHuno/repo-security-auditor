import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import select

from backend_app_test.db.session import AsyncSessionLocal
from backend_app_test.db.models import Scan as DBScan
from backend_app_test.services.scanner.runner import run_full_security_scan
from backend_app_test.services.scanner.normalizer import normalize_scanner_findings
from backend_app_test.workers.queue import redis_settings

logger = logging.getLogger(__name__)

async def process_scan_job(ctx: dict, scan_id_str: str, repo_url: str, branch: str, repository_id_str: str):
    scan_id = uuid.UUID(scan_id_str)
    repository_id = uuid.UUID(repository_id_str)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(DBScan).where(DBScan.id == scan_id))
            scan = result.scalar_one_or_none()
            if not scan or scan.status == "cancelled":
                return
            scan.status = "running"
            scan.started_at = datetime.now(timezone.utc)
            scan.progress = 10
            await db.commit()

            async def update_progress(pct: int):
                async with AsyncSessionLocal() as sub_db:
                    sub_scan = (await sub_db.execute(select(DBScan).where(DBScan.id == scan_id))).scalar_one_or_none()
                    if sub_scan and sub_scan.status != "cancelled":
                        sub_scan.progress = pct
                        await sub_db.commit()

            raw_findings = await run_full_security_scan(repo_url, branch, progress_callback=update_progress)
            await db.refresh(scan)
            if scan.status == "cancelled":
                return
            for f in normalize_scanner_findings(raw_findings, scan_id, repository_id):
                db.add(f)
            scan.status = "completed"
            scan.progress = 100
            scan.completed_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception as e:
            logger.exception(f"Scan failed: {e}")
            try:
                res = await db.execute(select(DBScan).where(DBScan.id == scan_id))
                s = res.scalar_one_or_none()
                if s and s.status != "cancelled":
                    s.status = "failed"
                    s.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass

class WorkerSettings:
    functions = [process_scan_job]
    redis_settings = redis_settings
    max_jobs = 10
    job_timeout = 360
