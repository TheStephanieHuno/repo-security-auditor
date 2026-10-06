import uuid

from fastapi import APIRouter, Query
from sqlalchemy import Select

from app.api.serializers import CATEGORY_LABELS, findings_to_api, pagination
from app.core.dependencies import CurrentUser, DBSession
from app.core.errors import APIError
from app.db.models import (
    Confidence,
    Finding,
    FindingCategory,
    FindingReviewStatus,
    Repository,
    Scan,
    Severity,
    utcnow,
)
from app.db.queries import get_owned_finding_by_public_id, owned_findings, paginate
from app.schemas.generated import FindingListResponse, FindingResponse, ReviewFindingRequest

router = APIRouter(prefix="/findings", tags=["Findings"])

MAX_REVIEW_NOTE_LENGTH = 2000
_CATEGORY_BY_LABEL = {label.lower(): value for value, label in CATEGORY_LABELS.items()}


def _parse_filter(value: str | None, allowed: type, name: str) -> list[str] | None:
    """Accept a comma-separated list of lowercase API values; reject unknown ones."""
    if value is None or not value.strip():
        return None
    parsed = []
    for item in value.split(","):
        candidate = item.strip().upper()
        if candidate not in allowed.__members__:
            raise APIError(422, "VALIDATION_ERROR", f"Unsupported {name} filter value.")
        parsed.append(allowed[candidate].value)
    return parsed


def apply_finding_filters(
    query: Select,
    *,
    severity: str | None = None,
    review_status: str | None = None,
    confidence: str | None = None,
    category: str | None = None,
) -> Select:
    if (severities := _parse_filter(severity, Severity, "severity")) is not None:
        query = query.where(Finding.severity.in_(severities))
    if (statuses := _parse_filter(review_status, FindingReviewStatus, "reviewStatus")) is not None:
        query = query.where(Finding.review_status.in_(statuses))
    if (confidences := _parse_filter(confidence, Confidence, "confidence")) is not None:
        query = query.where(Finding.confidence.in_(confidences))
    if category is not None and category.strip():
        values = []
        for item in category.split(","):
            key = item.strip()
            value = _CATEGORY_BY_LABEL.get(key.lower()) or (
                key.upper() if key.upper() in FindingCategory.__members__ else None
            )
            if value is None:
                raise APIError(422, "VALIDATION_ERROR", "Unsupported category filter value.")
            values.append(value)
        query = query.where(Finding.category.in_(values))
    return query


async def _owned(db, user, finding_id: uuid.UUID) -> Finding:
    finding = await get_owned_finding_by_public_id(db, user_id=user.id, public_id=finding_id)
    if finding is None:
        raise APIError(404, "NOT_FOUND", "Finding not found.")
    return finding


@router.get("", response_model=FindingListResponse)
async def list_findings(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    repositoryId: uuid.UUID | None = None,
    scanId: uuid.UUID | None = None,
    severity: str | None = None,
    reviewStatus: str | None = None,
    confidence: str | None = None,
    category: str | None = None,
):
    query = owned_findings(user.id)
    if repositoryId is not None:
        query = query.where(Repository.public_id == repositoryId)
    if scanId is not None:
        query = query.where(Scan.public_id == scanId)
    query = apply_finding_filters(
        query, severity=severity, review_status=reviewStatus, confidence=confidence, category=category
    )
    result = await paginate(db, query, page=page, page_size=pageSize)
    return FindingListResponse(
        status="success", data=await findings_to_api(db, result.items), pagination=pagination(result)
    )


@router.get("/{id}", response_model=FindingResponse)
async def get_finding(id: uuid.UUID, user: CurrentUser, db: DBSession):
    finding = await _owned(db, user, id)
    return FindingResponse(status="success", data=(await findings_to_api(db, [finding]))[0])


@router.patch("/{id}", response_model=FindingResponse)
async def review_finding(id: uuid.UUID, body: ReviewFindingRequest, user: CurrentUser, db: DBSession):
    finding = await _owned(db, user, id)
    note = body.reviewNote.strip() if body.reviewNote is not None else None
    if note is not None and len(note) > MAX_REVIEW_NOTE_LENGTH:
        raise APIError(
            422, "VALIDATION_ERROR", f"Review note must be at most {MAX_REVIEW_NOTE_LENGTH} characters."
        )
    finding.review_status = FindingReviewStatus[body.reviewStatus.value.upper()].value
    finding.review_note = note or None
    finding.reviewed_by = user.id
    finding.reviewed_at = utcnow()
    await db.flush()
    await db.refresh(finding)
    return FindingResponse(status="success", data=(await findings_to_api(db, [finding]))[0])
