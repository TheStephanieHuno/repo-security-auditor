import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status, Query
from backend_app_test.schemas.generated import (
    Scan,
    ScanResponse,
    ScanListResponse,
    ScanProgressResponse,
    StartScanRequest,
    ScanStatus,
    FindingsCount,
    Finding,
    FindingListResponse,
    Severity,
    Confidence,
    ReviewStatus,
    Pagination,
)

router = APIRouter(prefix="/scans", tags=["Scans"])

SAMPLE_SCAN_ID = uuid.uuid4()
SAMPLE_SCAN = Scan(
    id=SAMPLE_SCAN_ID,
    repositoryId=uuid.uuid4(),
    branch="main",
    status=ScanStatus.completed,
    progress=100,
    findingsCount=FindingsCount(critical=1, high=3, medium=5, low=2, info=0),
    startedAt=datetime.now(timezone.utc),
    completedAt=datetime.now(timezone.utc),
    cancelledAt=None,
    createdAt=datetime.now(timezone.utc),
    updatedAt=datetime.now(timezone.utc),
)

@router.get("", response_model=ScanListResponse)
async def list_scans(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    repositoryId: uuid.UUID | None = None,
):
    return ScanListResponse(
        status="success",
        data=[SAMPLE_SCAN],
        pagination=Pagination(page=page, pageSize=pageSize, totalItems=1, totalPages=1),
    )

@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def start_scan(body: StartScanRequest):
    new_scan = Scan(
        id=uuid.uuid4(),
        repositoryId=body.repositoryId,
        branch=body.branch,
        status=ScanStatus.queued,
        progress=0,
        findingsCount=FindingsCount(critical=0, high=0, medium=0, low=0, info=0),
        startedAt=None,
        completedAt=None,
        cancelledAt=None,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return ScanResponse(status="success", data=new_scan)

@router.get("/{id}", response_model=ScanResponse)
async def get_scan(id: uuid.UUID):
    return ScanResponse(status="success", data=SAMPLE_SCAN)

@router.get("/{id}/status", response_model=ScanProgressResponse)
async def get_scan_status(id: uuid.UUID):
    return ScanProgressResponse(
        status="success",
        data={"id": id, "status": ScanStatus.running, "progress": 65},
    )

@router.post("/{id}/cancel", response_model=ScanResponse)
async def cancel_scan(id: uuid.UUID):
    cancelled = Scan(
        id=id,
        repositoryId=uuid.uuid4(),
        branch="main",
        status=ScanStatus.cancelled,
        progress=40,
        findingsCount=FindingsCount(critical=0, high=0, medium=0, low=0, info=0),
        startedAt=datetime.now(timezone.utc),
        completedAt=None,
        cancelledAt=datetime.now(timezone.utc),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return ScanResponse(status="success", data=cancelled)

@router.get("/{id}/findings", response_model=FindingListResponse)
async def get_scan_findings(
    id: uuid.UUID,
    severity: str | None = None,
    confidence: str | None = None,
    reviewStatus: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    mock_finding = Finding(
        id=uuid.uuid4(),
        scanId=id,
        repositoryId=uuid.uuid4(),
        severity=Severity.high,
        confidence=Confidence.high,
        category="Secret Exposure",
        title="Hardcoded AWS Key",
        description="An AWS access key was detected in code configuration.",
        filePath="src/config.ts",
        lineStart=14,
        lineEnd=14,
        codeSnippet="const AWS_KEY = 'AKIAIOSFODNN7EXAMPLE';",
        recommendation="Rotate credentials and use environment variables.",
        aiExplanation="Exposed in commit 7f3b4c1 in public config.",
        reviewStatus=ReviewStatus.open,
        reviewNote=None,
        reviewedBy=None,
        reviewedAt=None,
        createdAt=datetime.now(timezone.utc),
    )
    return FindingListResponse(
        status="success",
        data=[mock_finding],
        pagination=Pagination(page=page, pageSize=pageSize, totalItems=1, totalPages=1),
    )