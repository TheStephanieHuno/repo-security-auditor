"""
Reports Router — PDF security report generation, status polling, and binary streaming.

Endpoints:
- GET  /api/reports            List all reports for the user\'s scans
- POST /api/reports            Trigger async PDF report generation
- GET  /api/reports/{id}       Poll report generation status
- GET  /api/reports/{id}/pdf   Stream the finished PDF binary

Security Controls:
- All queries enforce user ownership isolation (SRS FR-10).
- PDF streaming uses Content-Disposition headers for preview vs. download.
- Report generation is asynchronous to prevent API thread blocking (SRS NFR-02).
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, AsyncSessionLocal
from app.core.dependencies import get_current_user
from app.db.models import (
    Report as DBReport,
    Scan as DBScan,
    Repository as DBRepository,
    Finding as DBFinding,
    User as DBUser,
)
from app.schemas.generated import (
    Report,
    ReportResponse,
    ReportListResponse,
    ReportStatus,
    GenerateReportRequest,
    Pagination,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _report_to_response(r: DBReport) -> Report:
    """Converts a SQLAlchemy Report model to a Pydantic Report schema."""
    return Report(
        id=r.id,
        scanId=r.scan_id,
        status=ReportStatus(r.status) if r.status in [s.value for s in ReportStatus] else ReportStatus.generating,
        format=r.format or "pdf",
        fileUrl=r.file_url,
        fileSize=r.file_size,
        createdAt=ensure_utc(r.created_at),
        completedAt=ensure_utc(r.completed_at),
    )


async def _generate_pdf_report(report_id: uuid.UUID, scan_id: uuid.UUID):
    """
    Background task: Assembles the PDF report and saves it to disk.
    This runs outside the API request thread (SRS NFR-02).
    """
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(DBReport).where(DBReport.id == report_id))
            report = result.scalar_one_or_none()
            if not report:
                return

            # Fetch scan and findings data
            scan_result = await db.execute(select(DBScan).where(DBScan.id == scan_id))
            scan = scan_result.scalar_one_or_none()
            if not scan:
                report.status = "failed"
                report.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            findings_result = await db.execute(
                select(DBFinding).where(DBFinding.scan_id == scan_id)
            )
            findings = findings_result.scalars().all()

            # Build PDF using ReportLab
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.platypus import (
                    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
                )
                from reportlab.lib import colors
                import tempfile
                import os

                pdf_path = os.path.join(
                    tempfile.gettempdir(), f"rsa_report_{report_id}.pdf"
                )

                doc = SimpleDocTemplate(pdf_path, pagesize=A4)
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    "CustomTitle", parent=styles["Title"], fontSize=22, spaceAfter=20,
                )
                heading_style = ParagraphStyle(
                    "CustomHeading", parent=styles["Heading2"], fontSize=14, spaceAfter=10,
                )

                story = []

                # Cover Page
                story.append(Paragraph("Security Audit Report", title_style))
                story.append(Spacer(1, 0.3 * inch))
                story.append(Paragraph(f"Scan ID: {scan_id}", styles["Normal"]))
                story.append(Paragraph(f"Branch: {scan.branch}", styles["Normal"]))
                story.append(Paragraph(
                    f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                    styles["Normal"],
                ))
                story.append(Spacer(1, 0.5 * inch))

                # Executive Summary
                story.append(Paragraph("Executive Summary", heading_style))
                total_findings = len(findings)
                critical = sum(1 for f in findings if f.severity == "critical")
                high = sum(1 for f in findings if f.severity == "high")
                medium = sum(1 for f in findings if f.severity == "medium")
                low = sum(1 for f in findings if f.severity == "low")
                info = sum(1 for f in findings if f.severity == "info")

                summary_text = (
                    f"This security audit identified {total_findings} findings: "
                    f"{critical} critical, {high} high, {medium} medium, "
                    f"{low} low, and {info} informational. "
                )
                if critical > 0 or high > 0:
                    summary_text += (
                        "Immediate remediation is strongly recommended for all "
                        "critical and high severity findings."
                    )
                else:
                    summary_text += (
                        "No critical or high severity issues were detected. "
                        "Continue monitoring and address medium/low findings at your earliest convenience."
                    )
                story.append(Paragraph(summary_text, styles["Normal"]))
                story.append(Spacer(1, 0.3 * inch))

                # Severity Summary Table
                story.append(Paragraph("Severity Breakdown", heading_style))
                table_data = [
                    ["Severity", "Count"],
                    ["Critical", str(critical)],
                    ["High", str(high)],
                    ["Medium", str(medium)],
                    ["Low", str(low)],
                    ["Info", str(info)],
                ]
                table = Table(table_data, colWidths=[3 * inch, 1.5 * inch])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ]))
                story.append(table)
                story.append(PageBreak())

                # Detailed Findings
                story.append(Paragraph("Detailed Findings", heading_style))
                for i, f in enumerate(findings[:50], 1):  # Cap at 50 for PDF size
                    story.append(Paragraph(
                        f"{i}. [{f.severity.upper()}] {f.title}",
                        styles["Heading3"],
                    ))
                    story.append(Paragraph(f"File: {f.file_path}", styles["Normal"]))
                    story.append(Paragraph(f"Description: {f.description[:300]}", styles["Normal"]))
                    if f.ai_explanation:
                        story.append(Paragraph(
                            f"AI Analysis: {f.ai_explanation[:300]}", styles["Normal"],
                        ))
                    story.append(Paragraph(
                        f"Recommendation: {f.recommendation[:200]}", styles["Normal"],
                    ))
                    story.append(Spacer(1, 0.15 * inch))

                doc.build(story)

                file_size = os.path.getsize(pdf_path)

                report.status = "ready"
                report.file_url = pdf_path
                report.file_size = file_size
                report.completed_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info("Report %s generated successfully (%d bytes)", report_id, file_size)

            except ImportError:
                logger.warning("ReportLab not installed. Generating minimal text report.")
                import tempfile
                import os

                pdf_path = os.path.join(
                    tempfile.gettempdir(), f"rsa_report_{report_id}.pdf"
                )
                # Minimal valid PDF
                pdf_content = (
                    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
                    b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
                    b"0000000052 00000 n\n0000000101 00000 n\n"
                    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n162\n%%EOF\n"
                )
                with open(pdf_path, "wb") as f:
                    f.write(pdf_content)

                report.status = "ready"
                report.file_url = pdf_path
                report.file_size = len(pdf_content)
                report.completed_at = datetime.now(timezone.utc)
                await db.commit()

        except Exception as e:
            logger.exception("Report %s generation failed: %s", report_id, e)
            try:
                result = await db.execute(select(DBReport).where(DBReport.id == report_id))
                report = result.scalar_one_or_none()
                if report:
                    report.status = "failed"
                    report.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    scanId: Optional[uuid.UUID] = Query(None),
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all reports for scans belonging to the authenticated user (FR-10)."""
    query = (
        select(DBReport)
        .join(DBScan, DBReport.scan_id == DBScan.id)
        .join(DBRepository, DBScan.repository_id == DBRepository.id)
        .where(DBRepository.added_by == current_user.id)
    )

    if scanId:
        query = query.where(DBReport.scan_id == scanId)

    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar() or 0

    offset = (page - 1) * pageSize
    result = await db.execute(
        query.order_by(DBReport.created_at.desc()).offset(offset).limit(pageSize)
    )
    reports = result.scalars().all()

    total_pages = max(1, (total_items + pageSize - 1) // pageSize)

    return ReportListResponse(
        status="success",
        data=[_report_to_response(r) for r in reports],
        pagination=Pagination(
            page=page,
            pageSize=pageSize,
            totalItems=total_items,
            totalPages=total_pages,
        ),
    )


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    body: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers asynchronous PDF report generation for a completed scan.
    Returns immediately with status 'generating'.
    """
    # Verify scan ownership (FR-10)
    scan_query = (
        select(DBScan)
        .join(DBRepository, DBScan.repository_id == DBRepository.id)
        .where(DBScan.id == body.scanId, DBRepository.added_by == current_user.id)
    )
    scan_result = await db.execute(scan_query)
    scan = scan_result.scalar_one_or_none()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found or access denied.",
        )

    if scan.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reports can only be generated for completed scans.",
        )

    # Create report record
    now = datetime.now(timezone.utc)
    new_report = DBReport(
        id=uuid.uuid4(),
        scan_id=scan.id,
        status="generating",
        format="pdf",
        file_url=None,
        file_size=None,
        created_at=now,
        completed_at=None,
    )
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    # Dispatch PDF generation to background
    background_tasks.add_task(_generate_pdf_report, new_report.id, scan.id)
    logger.info("Report %s queued for scan %s", new_report.id, scan.id)

    return ReportResponse(status="success", data=_report_to_response(new_report))


@router.get("/{id}", response_model=ReportResponse)
async def get_report(
    id: uuid.UUID,
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves report generation status and metadata (FR-10)."""
    query = (
        select(DBReport)
        .join(DBScan, DBReport.scan_id == DBScan.id)
        .join(DBRepository, DBScan.repository_id == DBRepository.id)
        .where(DBReport.id == id, DBRepository.added_by == current_user.id)
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or access denied.",
        )

    return ReportResponse(status="success", data=_report_to_response(report))


@router.get("/{id}/pdf")
async def download_report_pdf(
    id: uuid.UUID,
    download: bool = Query(False, description="Set true to force file download"),
    current_user: DBUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Streams the finished PDF report binary.
    - Default (download=false): Content-Disposition: inline (browser preview)
    - download=true: Content-Disposition: attachment (force download)
    """
    import os

    query = (
        select(DBReport)
        .join(DBScan, DBReport.scan_id == DBScan.id)
        .join(DBRepository, DBScan.repository_id == DBRepository.id)
        .where(DBReport.id == id, DBRepository.added_by == current_user.id)
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or access denied.",
        )

    if report.status != "ready" or not report.file_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Report is not ready. Current status: {report.status}",
        )

    if not os.path.exists(report.file_url):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found on disk.",
        )

    with open(report.file_url, "rb") as f:
        pdf_bytes = f.read()

    disposition = "attachment" if download else "inline"
    filename = f"security-report-{report.scan_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
            "Cache-Control": "private, max-age=3600",
        },
    )
