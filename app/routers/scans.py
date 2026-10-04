import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status, Query
from app.schemas.generated import (
    Scan,
    ScanResponse,
    ScanListResponse,
    ScanProgressResponse,
    ScanProgressData,
    StartScanRequest,
    ScanStatus,
    FindingsCount,
    PaginationMeta,
)

router = APIRouter(prefix="/scans", tags=["Scans"])

@router.get("", response_model=ScanListResponse)
async def list_scans(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    mock_scan = Scan(
        id=uuid.uuid4(),
        repositoryId=uuid.uuid4(),
        branch="main",
        status=ScanStatus.completed,
        progress=100,
        findingsCount=FindingsCount(critical=1, high=2, medium=4, low=3, info=0),
        startedAt=datetime.now(timezone.utc),
        completedAt=datetime.now(timezone.utc),
        cancelledAt=None,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return ScanListResponse(
        status="success",
        data=[mock_scan],
        pagination=PaginationMeta(page=page, pageSize=pageSize, totalItems=1, totalPages=1),
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

@router.get("/{id}/status", response_model=ScanProgressResponse)
async def get_scan_status(id: uuid.UUID):
    return ScanProgressResponse(
        status="success",
        data=ScanProgressData(
            id=id,
            status=ScanStatus.running,
            progress=65,
        ),
    )

@router.post("/{id}/cancel", response_model=ScanResponse)
async def cancel_scan(id: uuid.UUID):
    cancelled_scan = Scan(
        id=id,
        repositoryId=uuid.uuid4(),
        branch="main",
        status=ScanStatus.cancelled,
        progress=30,
        findingsCount=FindingsCount(critical=0, high=0, medium=0, low=0, info=0),
        startedAt=datetime.now(timezone.utc),
        completedAt=None,
        cancelledAt=datetime.now(timezone.utc),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return ScanResponse(status="success", data=cancelled_scan)