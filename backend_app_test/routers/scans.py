import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend_app_test.db.session import get_db
from backend_app_test.core.dependencies import get_current_user
from backend_app_test.db.models import Scan as DBScan, Repository as DBRepository, Finding as DBFinding, User as DBUser
from backend_app_test.core.access import verify_user_owns_repository, verify_user_owns_scan
from backend_app_test.workers.queue import get_redis_pool
from backend_app_test.workers.scan_worker import process_scan_job
from backend_app_test.schemas.generated import (
    Scan, ScanResponse, ScanListResponse, ScanProgressResponse, StartScanRequest,
    ScanStatus, FindingsCount, Finding, FindingListResponse, Severity, Confidence, ReviewStatus, Pagination,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scans", tags=["Scans"])

def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

async def run_in_process_fallback(scan_id_str: str, repo_url: str, branch: str, repo_id_str: str):
    await process_scan_job({}, scan_id_str, repo_url, branch, repo_id_str)

@router.get("", response_model=ScanListResponse)
async def list_scans(page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), repositoryId: uuid.UUID | None = None, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    offset = (page - 1) * pageSize
    query = select(DBScan).join(DBRepository, DBScan.repository_id == DBRepository.id).where(DBRepository.added_by == current_user.id)
    if repositoryId:
        query = query.where(DBScan.repository_id == repositoryId)
    result = await db.execute(query.offset(offset).limit(pageSize).order_by(DBScan.created_at.desc()))
    scans = result.scalars().all()
    scan_items = []
    for s in scans:
        findings_query = select(DBFinding.severity, func.count()).where(DBFinding.scan_id == s.id).group_by(DBFinding.severity)
        counts_res = (await db.execute(findings_query)).all()
        counts_dict = {row[0]: row[1] for row in counts_res}
        scan_items.append(Scan(
            id=s.id, repositoryId=s.repository_id, branch=s.branch, status=ScanStatus(s.status), progress=s.progress,
            findingsCount=FindingsCount(critical=counts_dict.get("critical", 0), high=counts_dict.get("high", 0), medium=counts_dict.get("medium", 0), low=counts_dict.get("low", 0), info=counts_dict.get("info", 0)),
            startedAt=ensure_utc(s.started_at), completedAt=ensure_utc(s.completed_at), cancelledAt=ensure_utc(s.cancelled_at), createdAt=ensure_utc(s.created_at), updatedAt=ensure_utc(s.updated_at)
        ))
    count_query = select(func.count()).select_from(DBScan).join(DBRepository, DBScan.repository_id == DBRepository.id).where(DBRepository.added_by == current_user.id)
    total_items = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total_items + pageSize - 1) // pageSize)
    return ScanListResponse(status="success", data=scan_items, pagination=Pagination(page=page, pageSize=pageSize, totalItems=total_items, totalPages=total_pages))

@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def start_scan(
    body: StartScanRequest,
    background_tasks: BackgroundTasks,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = await verify_user_owns_repository(db, body.repositoryId, current_user)

    now = datetime.now(timezone.utc)
    new_scan = DBScan(
        id=uuid.uuid4(),
        repository_id=repo.id,
        initiated_by=current_user.id,
        branch=body.branch,
        status="queued",
        progress=0,
        started_at=None,
        completed_at=None,
        cancelled_at=None,
        created_at=now,
        updated_at=now
    )
    db.add(new_scan)
    await db.commit()
    await db.refresh(new_scan)

    # Dispatch to the arq scan worker (resource-limited container). If Redis is
    # unreachable, run in this process so scans still complete.
    job_args = (str(new_scan.id), repo.url, body.branch, str(repo.id))
    enqueued = False
    pool = await get_redis_pool()
    if pool is not None:
        try:
            enqueued = await pool.enqueue_job("process_scan_job", *job_args) is not None
        except Exception as exc:
            logger.warning("Scan queue unavailable, running in-process: %s", exc)
    if not enqueued:
        background_tasks.add_task(run_in_process_fallback, *job_args)

    return ScanResponse(
        status="success",
        data=Scan(
            id=new_scan.id,
            repositoryId=new_scan.repository_id,
            branch=new_scan.branch,
            status=ScanStatus.queued,
            progress=0,
            findingsCount=FindingsCount(),
            startedAt=None,
            completedAt=None,
            cancelledAt=None,
            createdAt=ensure_utc(new_scan.created_at),
            updatedAt=ensure_utc(new_scan.updated_at)
        )
    )

@router.get("/{id}", response_model=ScanResponse)
async def get_scan(id: uuid.UUID, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    scan = await verify_user_owns_scan(db, id, current_user)
    findings_query = select(DBFinding.severity, func.count()).where(DBFinding.scan_id == scan.id).group_by(DBFinding.severity)
    counts_res = (await db.execute(findings_query)).all()
    counts_dict = {row[0]: row[1] for row in counts_res}
    return ScanResponse(status="success", data=Scan(
        id=scan.id, repositoryId=scan.repository_id, branch=scan.branch, status=ScanStatus(scan.status), progress=scan.progress,
        findingsCount=FindingsCount(critical=counts_dict.get("critical", 0), high=counts_dict.get("high", 0), medium=counts_dict.get("medium", 0), low=counts_dict.get("low", 0), info=counts_dict.get("info", 0)),
        startedAt=ensure_utc(scan.started_at), completedAt=ensure_utc(scan.completed_at), cancelledAt=ensure_utc(scan.cancelled_at), createdAt=ensure_utc(scan.created_at), updatedAt=ensure_utc(scan.updated_at)
    ))

@router.get("/{id}/status", response_model=ScanProgressResponse)
async def get_scan_status(id: uuid.UUID, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    scan = await verify_user_owns_scan(db, id, current_user)
    return ScanProgressResponse(status="success", data={"id": scan.id, "status": ScanStatus(scan.status), "progress": scan.progress})

@router.post("/{id}/cancel", response_model=ScanResponse)
async def cancel_scan(id: uuid.UUID, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    scan = await verify_user_owns_scan(db, id, current_user)
    if scan.status not in ("queued", "running"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Scan cannot be cancelled in its current state.")
    scan.status = "cancelled"
    scan.cancelled_at = datetime.now(timezone.utc)
    scan.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ScanResponse(status="success", data=Scan(id=scan.id, repositoryId=scan.repository_id, branch=scan.branch, status=ScanStatus.cancelled, progress=scan.progress, findingsCount=FindingsCount(), startedAt=ensure_utc(scan.started_at), completedAt=None, cancelledAt=ensure_utc(scan.cancelled_at), createdAt=ensure_utc(scan.created_at), updatedAt=ensure_utc(scan.updated_at)))

@router.get("/{id}/findings", response_model=FindingListResponse)
async def get_scan_findings(id: uuid.UUID, severity: str | None = None, confidence: str | None = None, reviewStatus: str | None = None, page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await verify_user_owns_scan(db, id, current_user)
    offset = (page - 1) * pageSize
    query = select(DBFinding).where(DBFinding.scan_id == id)
    if severity:
        query = query.where(DBFinding.severity == severity.lower())
    if confidence:
        query = query.where(DBFinding.confidence == confidence.lower())
    if reviewStatus:
        query = query.where(DBFinding.review_status == reviewStatus.lower())
    result = await db.execute(query.offset(offset).limit(pageSize))
    findings = result.scalars().all()
    data = [Finding(
        id=f.id, scanId=f.scan_id, repositoryId=f.repository_id, severity=Severity(f.severity), confidence=Confidence(f.confidence),
        category=f.category, title=f.title, description=f.description, filePath=f.file_path, lineStart=f.line_start, lineEnd=f.line_end,
        codeSnippet=f.code_snippet, recommendation=f.recommendation, aiExplanation=f.ai_explanation, reviewStatus=ReviewStatus(f.review_status),
        reviewNote=f.review_note, reviewedBy=f.reviewed_by, reviewedAt=ensure_utc(f.reviewed_at), createdAt=ensure_utc(f.created_at)
    ) for f in findings]
    count_query = select(func.count()).select_from(DBFinding).where(DBFinding.scan_id == id)
    total_items = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total_items + pageSize - 1) // pageSize)
    return FindingListResponse(status="success", data=data, pagination=Pagination(page=page, pageSize=pageSize, totalItems=total_items, totalPages=total_pages))
