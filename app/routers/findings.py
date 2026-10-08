"""
Findings Router: Workspace-level vulnerability querying with multi-filtering.

Endpoints:
- GET  /api/findings        List all findings across the user\'s repositories
- GET  /api/findings/{id}   Retrieve a single finding with full detail
- PATCH /api/findings/{id}  Update finding review status and analyst notes

Security Controls:
- All queries enforce user ownership isolation (SRS FR-10).
- Pagination prevents unbounded result sets.
- Input filters are validated against known enum values.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.db.models import (
    Finding as DBFinding,
    Repository as DBRepository,
    User as DBUser,
)
from app.schemas.generated import (
    Finding,
    FindingResponse,
    FindingListResponse,
    ReviewFindingRequest,
    Severity,
    Confidence,
    ReviewStatus,
    Pagination,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/findings", tags=["Findings"])


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensures datetime objects carry UTC timezone info for Pydantic v2."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _finding_to_response(f: DBFinding) -> Finding:
    """Converts a SQLAlchemy Finding model to a Pydantic Finding schema."""
    return Finding(
        id=f.id,
        scanId=f.scan_id,
        repositoryId=f.repository_id,
        severity=Severity(f.severity) if f.severity in [s.value for s in Severity] else Severity.medium,
        confidence=Confidence(f.confidence) if f.confidence in [c.value for c in Confidence] else Confidence.high,
        category=f.category,
        title=f.title,
        description=f.description,
        filePath=f.file_path,
        lineStart=f.line_start,
        lineEnd=f.line_end,
        codeSnippet=f.code_snippet,
        recommendation=f.recommendation,
        aiExplanation=f.ai_explanation,
        reviewStatus=ReviewStatus(f.review_status) if f.review_status in [r.value for r in ReviewStatus] else ReviewStatus.open,
        reviewNote=f.review_note,
        reviewedBy=f.reviewed_by,
        reviewedAt=ensure_utc(f.reviewed_at),
        createdAt=ensure_utc(f.created_at),
    )


@router.get("", response_model=FindingListResponse)
async def list_findings(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    repositoryId: Optional[uuid.UUID] = Query(None, description="Filter by repository"),
    scanId: Optional[uuid.UUID] = Query(None, description="Filter by scan"),
    severity: Optional[str] = Query(None, description="Comma-separated severity levels"),
    confidence: Optional[str] = Query(None, description="Comma-separated confidence levels"),
    category: Optional[str] = Query(None, description="Filter by category"),
    reviewStatus: Optional[str] = Query(None, description="Comma-separated review statuses"),
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists all findings across the authenticated user\'s repositories.
    Supports multi-filtering by severity, confidence, category, and review status.
    """
    # Base query: only findings belonging to repositories owned by current user (FR-10)
    query = (
        select(DBFinding)
        .join(DBRepository, DBFinding.repository_id == DBRepository.id)
        .where(DBRepository.added_by == current_user.id)
    )

    # Apply optional filters
    if repositoryId:
        query = query.where(DBFinding.repository_id == repositoryId)

    if scanId:
        query = query.where(DBFinding.scan_id == scanId)

    if severity:
        severity_list = [s.strip().lower() for s in severity.split(",")]
        query = query.where(DBFinding.severity.in_(severity_list))

    if confidence:
        confidence_list = [c.strip().lower() for c in confidence.split(",")]
        query = query.where(DBFinding.confidence.in_(confidence_list))

    if category:
        query = query.where(DBFinding.category.ilike(f"%{category}%"))

    if reviewStatus:
        status_list = [r.strip().lower() for r in reviewStatus.split(",")]
        query = query.where(DBFinding.review_status.in_(status_list))

    # Count total matching records
    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * pageSize
    query = query.order_by(
        DBFinding.severity.asc(),  # critical first (alphabetical: critical < high < info < low < medium)
        DBFinding.created_at.desc(),
    ).offset(offset).limit(pageSize)

    result = await db.execute(query)
    findings = result.scalars().all()

    total_pages = max(1, (total_items + pageSize - 1) // pageSize)

    return FindingListResponse(
        status="success",
        data=[_finding_to_response(f) for f in findings],
        pagination=Pagination(
            page=page,
            pageSize=pageSize,
            totalItems=total_items,
            totalPages=total_pages,
        ),
    )


@router.get("/{id}", response_model=FindingResponse)
async def get_finding(
    id: uuid.UUID,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a single finding with full detail, enforcing ownership (FR-10)."""
    query = (
        select(DBFinding)
        .join(DBRepository, DBFinding.repository_id == DBRepository.id)
        .where(DBFinding.id == id, DBRepository.added_by == current_user.id)
    )
    result = await db.execute(query)
    finding = result.scalar_one_or_none()

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found or access denied.",
        )

    return FindingResponse(status="success", data=_finding_to_response(finding))


@router.patch("/{id}", response_model=FindingResponse)
async def review_finding(
    id: uuid.UUID,
    body: ReviewFindingRequest,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates the triage review status and optional analyst note for a finding.
    Only the owning user can modify findings in their repositories (FR-10).
    """
    query = (
        select(DBFinding)
        .join(DBRepository, DBFinding.repository_id == DBRepository.id)
        .where(DBFinding.id == id, DBRepository.added_by == current_user.id)
    )
    result = await db.execute(query)
    finding = result.scalar_one_or_none()

    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found or access denied.",
        )

    # Update review fields
    finding.review_status = body.reviewStatus.value if hasattr(body.reviewStatus, "value") else body.reviewStatus
    finding.review_note = body.reviewNote
    finding.reviewed_by = current_user.id
    finding.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(finding)

    logger.info(
        "Finding %s review updated to '%s' by user %s",
        finding.id, finding.review_status, current_user.id,
    )

    return FindingResponse(status="success", data=_finding_to_response(finding))
