import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Response, Query, status
from app.schemas.generated import (
    Report,
    ReportResponse,
    ReportListResponse,
    GenerateReportRequest,
    ReportStatus,
    Pagination,
)

router = APIRouter(prefix="/reports", tags=["Reports"])

SAMPLE_REPORT_ID = uuid.uuid4()
SAMPLE_REPORT = Report(
    id=SAMPLE_REPORT_ID,
    scanId=uuid.uuid4(),
    status=ReportStatus.ready,
    format="pdf",
    fileUrl=f"/api/reports/{SAMPLE_REPORT_ID}/pdf",
    fileSize=1048576,
    createdAt=datetime.now(timezone.utc),
    completedAt=datetime.now(timezone.utc),
)

@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    scanId: uuid.UUID | None = None,
):
    return ReportListResponse(
        status="success",
        data=[SAMPLE_REPORT],
        pagination=Pagination(page=page, pageSize=pageSize, totalItems=1, totalPages=1),
    )

@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(body: GenerateReportRequest):
    new_report = Report(
        id=uuid.uuid4(),
        scanId=body.scanId,
        status=ReportStatus.generating,
        format="pdf",
        fileUrl=None,
        fileSize=None,
        createdAt=datetime.now(timezone.utc),
        completedAt=None,
    )
    return ReportResponse(status="success", data=new_report)

@router.get("/{id}", response_model=ReportResponse)
async def get_report(id: uuid.UUID):
    return ReportResponse(status="success", data=SAMPLE_REPORT)

@router.get("/{id}/pdf")
async def download_pdf(id: uuid.UUID, download: bool = False):
    # Minimal valid empty PDF byte buffer for testing preview and download
    mock_pdf_bytes = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
        b"0000000052 00000 n\n0000000101 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n162\n%%EOF\n"
    )
    disposition = "attachment" if download else "inline"
    return Response(
        content=mock_pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="report-{id}.pdf"'},
    )