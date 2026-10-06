import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Query
from app.schemas.generated import (
    Finding,
    FindingResponse,
    FindingListResponse,
    ReviewFindingRequest,
    Severity,
    ReviewStatus,
    Pagination,
)

router = APIRouter(prefix="/findings", tags=["Findings"])

SAMPLE_FINDING = Finding(
    id=uuid.uuid4(),
    scanId=uuid.uuid4(),
    repositoryId=uuid.uuid4(),
    severity=Severity.critical,
    category="Dependency Vulnerability",
    title="SQL Injection in Auth Pipeline",
    description="Raw string concatenation in SQL execution.",
    filePath="src/auth.py",
    lineStart=42,
    lineEnd=45,
    codeSnippet="db.execute(f'SELECT * FROM users WHERE email={email}')",
    recommendation="Use parameterized queries or ORM abstractions.",
    aiExplanation="High severity issue with exploit potential.",
    reviewStatus=ReviewStatus.open,
    reviewNote=None,
    reviewedBy=None,
    reviewedAt=None,
    createdAt=datetime.now(timezone.utc),
)

@router.get("", response_model=FindingListResponse)
async def list_findings(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    repositoryId: uuid.UUID | None = None,
    scanId: uuid.UUID | None = None,
    severity: str | None = None,
    reviewStatus: str | None = None,
):
    return FindingListResponse(
        status="success",
        data=[SAMPLE_FINDING],
        pagination=Pagination(page=page, pageSize=pageSize, totalItems=1, totalPages=1),
    )

@router.get("/{id}", response_model=FindingResponse)
async def get_finding(id: uuid.UUID):
    return FindingResponse(status="success", data=SAMPLE_FINDING)

@router.patch("/{id}", response_model=FindingResponse)
async def review_finding(id: uuid.UUID, body: ReviewFindingRequest):
    SAMPLE_FINDING.reviewStatus = body.reviewStatus
    SAMPLE_FINDING.reviewNote = body.reviewNote
    SAMPLE_FINDING.reviewedAt = datetime.now(timezone.utc)
    return FindingResponse(status="success", data=SAMPLE_FINDING)