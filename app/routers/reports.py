import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.serializers import pagination, reports_to_api
from app.core.dependencies import CurrentUser, DBSession
from app.core.errors import APIError
from app.db.models import ReportStatus, Scan, ScanStatus
from app.db.queries import (
    get_owned_report_by_public_id,
    get_owned_scan_by_public_id,
    owned_reports,
    paginate,
)
from app.schemas.generated import (
    GenerateReportRequest,
    ReportListResponse,
    ReportResponse,
)
from app.services.ai_service import AIService, ai_explanations_enabled
from app.services.pdf_report import load_report_data, render_report_pdf
from app.services.reporting import generate_report

router = APIRouter(prefix="/reports", tags=["Reports"])


def get_ai_service() -> AIService | None:
    """FastAPI dependency; None when no AI provider is configured."""
    return AIService() if ai_explanations_enabled() else None


AI = Annotated[AIService | None, Depends(get_ai_service)]


@router.get("", response_model=ReportListResponse)
async def list_reports(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    scanId: uuid.UUID | None = None,
):
    query = owned_reports(user.id)
    if scanId is not None:
        query = query.where(Scan.public_id == scanId)
    result = await paginate(db, query, page=page, page_size=pageSize)
    return ReportListResponse(
        status="success", data=await reports_to_api(db, result.items), pagination=pagination(result)
    )


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(body: GenerateReportRequest, user: CurrentUser, db: DBSession, ai: AI):
    scan = await get_owned_scan_by_public_id(db, user_id=user.id, public_id=body.scanId)
    if scan is None:
        raise APIError(404, "NOT_FOUND", "Scan not found.")
    if scan.status not in {ScanStatus.COMPLETED.value, ScanStatus.PARTIAL.value}:
        raise APIError(409, "SCAN_NOT_REPORTABLE", "Reports are available for completed scans only.")
    report = await generate_report(db, scan=scan, ai=ai)
    await db.refresh(report)
    return ReportResponse(status="success", data=(await reports_to_api(db, [report]))[0])


@router.get("/{id}", response_model=ReportResponse)
async def get_report(id: uuid.UUID, user: CurrentUser, db: DBSession):
    report = await get_owned_report_by_public_id(db, user_id=user.id, public_id=id)
    if report is None:
        raise APIError(404, "NOT_FOUND", "Report not found.")
    return ReportResponse(status="success", data=(await reports_to_api(db, [report]))[0])


@router.get("/{id}/pdf")
async def download_pdf(id: uuid.UUID, user: CurrentUser, db: DBSession, download: bool = False):
    report = await get_owned_report_by_public_id(db, user_id=user.id, public_id=id)
    if report is None:
        raise APIError(404, "NOT_FOUND", "Report not found.")
    if report.status != ReportStatus.READY.value:
        raise APIError(409, "REPORT_NOT_READY", "The report is not ready yet.")
    data = await load_report_data(db, report=report)
    # ReportLab is CPU-bound; keep it off the event loop.
    pdf = await asyncio.to_thread(render_report_pdf, data)
    disposition = "attachment" if download else "inline"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="security-report-{report.public_id}.pdf"',
            "Cache-Control": "no-store",
        },
    )
