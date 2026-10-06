"""PDF report assembly with ReportLab (SRS FR-08, ticket T-29).

``load_report_data`` gathers everything from the database in explicit async
queries; ``render_report_pdf`` is a pure function from that data to PDF bytes.
All repository-derived text is XML-escaped before it reaches ReportLab's
Paragraph markup parser.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Evidence,
    ExplanationStatus,
    Finding,
    FindingExplanation,
    Report,
    Repository,
    Scan,
    ScannerRun,
)

MAX_DETAILED_FINDINGS = 150
_SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
_SEVERITY_COLORS = {
    "CRITICAL": colors.HexColor("#8B1A1A"),
    "HIGH": colors.HexColor("#C0392B"),
    "MEDIUM": colors.HexColor("#B9770E"),
    "LOW": colors.HexColor("#2E6B9E"),
}


@dataclass(frozen=True)
class ReportFinding:
    severity: str
    title: str
    scanner: str
    category: str
    location: str
    description: str
    recommendation: str
    review_status: str
    snippet: str | None = None
    ai_explanation: str | None = None
    ai_remediation: str | None = None


@dataclass(frozen=True)
class ReportData:
    repository_name: str
    repository_url: str
    branch: str
    commit_sha: str | None
    scan_status: str
    queued_at: datetime | None
    completed_at: datetime | None
    scanner_runs: list[tuple[str, str, int, str | None]]
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    risk_score: int | None
    policy_status: str
    report_version: str
    executive_summary: str
    findings: list[ReportFinding] = field(default_factory=list)
    generated_at: datetime | None = None


def _location(file_path: str | None, line_start: int | None) -> str:
    if not file_path:
        return "-"
    return f"{file_path}:{line_start}" if line_start else file_path


async def load_report_data(db: AsyncSession, *, report: Report) -> ReportData:
    scan = (await db.execute(select(Scan).where(Scan.id == report.scan_id))).scalar_one()
    repository = (
        await db.execute(select(Repository).where(Repository.id == scan.repository_id))
    ).scalar_one()
    runs = list(
        (
            await db.execute(
                select(ScannerRun).where(ScannerRun.scan_id == scan.id).order_by(ScannerRun.scanner_name)
            )
        ).scalars()
    )
    run_names = {run.id: run.scanner_name for run in runs}
    findings = list(
        (
            await db.execute(
                select(Finding).where(Finding.scanner_run_id.in_(list(run_names) or [-1]))
            )
        ).scalars()
    )
    findings.sort(key=lambda item: (_SEVERITY_RANK.get(item.severity, 9), item.id))
    finding_ids = [finding.id for finding in findings[:MAX_DETAILED_FINDINGS]] or [-1]

    snippets: dict[int, str] = {}
    for evidence in (
        await db.execute(
            select(Evidence).where(Evidence.finding_id.in_(finding_ids)).order_by(Evidence.id)
        )
    ).scalars():
        if evidence.code_snippet and evidence.finding_id not in snippets:
            snippets[evidence.finding_id] = evidence.code_snippet

    explanations: dict[int, FindingExplanation] = {}
    for explanation in (
        await db.execute(
            select(FindingExplanation)
            .where(
                FindingExplanation.finding_id.in_(finding_ids),
                FindingExplanation.status == ExplanationStatus.READY.value,
            )
            .order_by(FindingExplanation.id)
        )
    ).scalars():
        explanations[explanation.finding_id] = explanation  # latest READY wins

    return ReportData(
        repository_name=repository.name,
        repository_url=repository.github_url,
        branch=scan.target_branch,
        commit_sha=scan.commit_sha,
        scan_status=scan.status,
        queued_at=scan.queued_at,
        completed_at=scan.completed_at,
        scanner_runs=[
            (run.scanner_name, run.status, run.finding_count, run.error_summary) for run in runs
        ],
        total_findings=report.total_findings,
        critical_count=report.critical_count,
        high_count=report.high_count,
        medium_count=report.medium_count,
        low_count=report.low_count,
        risk_score=report.risk_score,
        policy_status=report.policy_status,
        report_version=report.report_version,
        executive_summary=report.summary,
        generated_at=report.generated_at,
        findings=[
            ReportFinding(
                severity=finding.severity,
                title=finding.title,
                scanner=run_names.get(finding.scanner_run_id, "-"),
                category=finding.category,
                location=_location(finding.file_path, finding.line_start),
                description=finding.description,
                recommendation=finding.recommendation,
                review_status=finding.review_status,
                snippet=snippets.get(finding.id),
                ai_explanation=(
                    explanations[finding.id].explanation if finding.id in explanations else None
                ),
                ai_remediation=(
                    explanations[finding.id].remediation_guidance
                    if finding.id in explanations
                    else None
                ),
            )
            for finding in findings[:MAX_DETAILED_FINDINGS]
        ],
    )


def _text(value: object) -> str:
    """Escape for ReportLab Paragraph markup and keep line breaks."""
    return escape(str(value)).replace("\n", "<br/>")


def _format_time(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M UTC") if value else "-"


def render_report_pdf(data: ReportData) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Security report - {data.repository_name}",
        author="Repo Security Auditor",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12, alignment=TA_LEFT)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10)
    code = ParagraphStyle(
        "code", parent=small, fontName="Courier", backColor=colors.HexColor("#F4F4F4"), borderPadding=3
    )
    heading = styles["Heading2"]
    story: list = [
        Paragraph(f"Security Scan Report: {_text(data.repository_name)}", styles["Title"]),
        Paragraph(_text(data.repository_url), small),
        Spacer(1, 6 * mm),
    ]

    metadata = [
        ["Branch", data.branch, "Scan status", data.scan_status],
        ["Commit", data.commit_sha or "latest", "Policy", data.policy_status],
        ["Queued", _format_time(data.queued_at), "Completed", _format_time(data.completed_at)],
        ["Risk score", "-" if data.risk_score is None else f"{data.risk_score} / 100", "Report version", data.report_version],
    ]
    story.append(_grid([[Paragraph(_text(cell), small) for cell in row] for row in metadata], header=False))
    story += [Spacer(1, 5 * mm), Paragraph("Executive summary", heading)]
    story.append(Paragraph(_text(data.executive_summary or "No summary available."), body))

    story += [Spacer(1, 4 * mm), Paragraph("Findings by severity", heading)]
    severity_rows = [
        ["Critical", "High", "Medium", "Low", "Total"],
        [data.critical_count, data.high_count, data.medium_count, data.low_count, data.total_findings],
    ]
    story.append(_grid([[Paragraph(_text(cell), body) for cell in row] for row in severity_rows]))

    story += [Spacer(1, 4 * mm), Paragraph("Scanner coverage", heading)]
    coverage = [["Scanner", "Status", "Findings", "Notes"]] + [
        [name, status, count, error or ""] for name, status, count, error in data.scanner_runs
    ]
    story.append(_grid([[Paragraph(_text(cell), small) for cell in row] for row in coverage]))

    story += [Spacer(1, 4 * mm), Paragraph("Issue summary", heading)]
    if data.findings:
        rows = [["Severity", "Title", "Location", "Scanner"]] + [
            [finding.severity, finding.title, finding.location, finding.scanner]
            for finding in data.findings
        ]
        table = _grid(
            [[Paragraph(_text(cell), small) for cell in row] for row in rows],
            column_widths=[20 * mm, 80 * mm, 55 * mm, 20 * mm],
        )
        for index, finding in enumerate(data.findings, start=1):
            color = _SEVERITY_COLORS.get(finding.severity)
            if color is not None:
                table.setStyle(TableStyle([("TEXTCOLOR", (0, index), (0, index), color)]))
        story.append(table)
        if data.total_findings > len(data.findings):
            story.append(
                Paragraph(
                    f"Showing the {len(data.findings)} most severe of {data.total_findings} findings.",
                    small,
                )
            )
    else:
        story.append(Paragraph("No findings were reported.", body))

    if data.findings:
        story += [Spacer(1, 4 * mm), Paragraph("Issue details", heading)]
    for index, finding in enumerate(data.findings, start=1):
        block = [
            Paragraph(
                f"{index}. [{_text(finding.severity)}] {_text(finding.title)}", styles["Heading4"]
            ),
            Paragraph(
                f"<b>Location:</b> {_text(finding.location)} &nbsp; <b>Scanner:</b> "
                f"{_text(finding.scanner)} &nbsp; <b>Review:</b> {_text(finding.review_status)}",
                small,
            ),
            Paragraph(_text(finding.description), body),
        ]
        if finding.snippet:
            block.append(Paragraph(_text(finding.snippet), code))
        block.append(Paragraph(f"<b>Recommendation:</b> {_text(finding.recommendation)}", body))
        if finding.ai_explanation:
            block.append(Paragraph(f"<b>AI analysis:</b> {_text(finding.ai_explanation)}", body))
        if finding.ai_remediation:
            block.append(Paragraph(f"<b>AI remediation:</b> {_text(finding.ai_remediation)}", body))
        block.append(Spacer(1, 3 * mm))
        story.append(KeepTogether(block))

    def footer(canvas, doc) -> None:  # noqa: ANN001 - ReportLab callback signature
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawString(18 * mm, 10 * mm, f"Generated {_format_time(data.generated_at)}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def _grid(rows: list[list], *, header: bool = True, column_widths: list[float] | None = None) -> Table:
    table = Table(rows, colWidths=column_widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BBBBBB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")))
    table.setStyle(TableStyle(style))
    return table
