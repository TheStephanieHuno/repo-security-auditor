import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend_app_test.db.session import get_db
from backend_app_test.core.dependencies import get_current_user
from backend_app_test.core.audit import AuditEvent, AuditOutcome, audit_event
from backend_app_test.db.models import Finding as DBFinding, Repository as DBRepository, User as DBUser
from backend_app_test.schemas.generated import (
    Finding, FindingResponse, FindingListResponse, ReviewFindingRequest,
    Severity, Confidence, ReviewStatus, Pagination,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/findings", tags=["Findings"])

def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

def _finding_to_response(f: DBFinding) -> Finding:
    return Finding(
        id=f.id, scanId=f.scan_id, repositoryId=f.repository_id,
        severity=Severity(f.severity) if f.severity in [s.value for s in Severity] else Severity.medium,
        confidence=Confidence(f.confidence) if f.confidence in [c.value for c in Confidence] else Confidence.high,
        category=f.category, title=f.title, description=f.description, filePath=f.file_path,
        lineStart=f.line_start, lineEnd=f.line_end, codeSnippet=f.code_snippet, recommendation=f.recommendation,
        aiExplanation=f.ai_explanation, reviewStatus=ReviewStatus(f.review_status) if f.review_status in [r.value for r in ReviewStatus] else ReviewStatus.open,
        reviewNote=f.review_note, reviewedBy=f.reviewed_by, reviewedAt=ensure_utc(f.reviewed_at), createdAt=ensure_utc(f.created_at)
    )

@router.get("", response_model=FindingListResponse)
async def list_findings(
    page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100),
    repositoryId: Optional[uuid.UUID] = Query(None), scanId: Optional[uuid.UUID] = Query(None),
    severity: Optional[str] = Query(None), confidence: Optional[str] = Query(None),
    category: Optional[str] = Query(None), reviewStatus: Optional[str] = Query(None),
    current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    query = select(DBFinding).join(DBRepository, DBFinding.repository_id == DBRepository.id).where(DBRepository.added_by == current_user.id)
    if repositoryId:
        query = query.where(DBFinding.repository_id == repositoryId)
    if scanId:
        query = query.where(DBFinding.scan_id == scanId)
    if severity:
        query = query.where(DBFinding.severity.in_([s.strip().lower() for s in severity.split(",")]))
    if confidence:
        query = query.where(DBFinding.confidence.in_([c.strip().lower() for c in confidence.split(",")]))
    if category:
        query = query.where(DBFinding.category.ilike(f"%{category}%"))
    if reviewStatus:
        query = query.where(DBFinding.review_status.in_([r.strip().lower() for r in reviewStatus.split(",")]))

    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * pageSize
    query = query.order_by(DBFinding.created_at.desc()).offset(offset).limit(pageSize)
    findings = (await db.execute(query)).scalars().all()
    total_pages = max(1, (total_items + pageSize - 1) // pageSize)

    return FindingListResponse(
        status="success",
        data=[_finding_to_response(f) for f in findings],
        pagination=Pagination(page=page, pageSize=pageSize, totalItems=total_items, totalPages=total_pages)
    )

@router.get("/{id}", response_model=FindingResponse)
async def get_finding(id: uuid.UUID, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(DBFinding).join(DBRepository, DBFinding.repository_id == DBRepository.id).where(DBFinding.id == id, DBRepository.added_by == current_user.id)
    finding = (await db.execute(query)).scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found or access denied.")
    return FindingResponse(status="success", data=_finding_to_response(finding))

@router.patch("/{id}", response_model=FindingResponse)
async def review_finding(id: uuid.UUID, body: ReviewFindingRequest, request: Request, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(DBFinding).join(DBRepository, DBFinding.repository_id == DBRepository.id).where(DBFinding.id == id, DBRepository.added_by == current_user.id)
    finding = (await db.execute(query)).scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found or access denied.")
    previous_status = finding.review_status
    finding.review_status = body.reviewStatus.value if hasattr(body.reviewStatus, "value") else body.reviewStatus
    finding.review_note = body.reviewNote
    finding.reviewed_by = current_user.id
    finding.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    audit_event(
        AuditEvent.FINDING_REVIEW_UPDATED, outcome=AuditOutcome.SUCCESS, request=request,
        actor_id=current_user.id, finding_id=id, previous_status=previous_status,
        new_status=finding.review_status,
        # Note text may be sensitive; record only that one exists.
        note_provided=bool(finding.review_note), note_length=len(finding.review_note or ""),
    )
    await db.refresh(finding)
    return FindingResponse(status="success", data=_finding_to_response(finding))
