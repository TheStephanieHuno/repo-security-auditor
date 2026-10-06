"""Report generation: aggregation plus an optional AI executive summary."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Finding, Report, Repository, Scan, ScannerRun
from app.db.reports import build_scan_report
from app.services.ai_service import AIService, AIServiceError

logger = logging.getLogger(__name__)
TOP_FINDINGS_FOR_SUMMARY = 15
_SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


async def generate_report(
    db: AsyncSession, *, scan: Scan, ai: AIService | None = None
) -> Report:
    """Aggregate a terminal scan into its Report and, if AI is available, summarize it.

    A failed AI summary keeps the deterministic summary; it never fails the report.
    """
    report = await build_scan_report(db, scan=scan)
    if ai is None:
        return report

    repository = (
        await db.execute(select(Repository).where(Repository.id == scan.repository_id))
    ).scalar_one()
    findings = list(
        (
            await db.execute(
                select(Finding, ScannerRun.scanner_name)
                .join(ScannerRun, Finding.scanner_run_id == ScannerRun.id)
                .where(ScannerRun.scan_id == scan.id)
            )
        ).all()
    )
    findings.sort(key=lambda row: (_SEVERITY_RANK.get(row[0].severity, 9), row[0].id))
    scan_data = {
        "repository": repository.name,
        "branch": scan.target_branch,
        "scan_status": scan.status,
        "risk_score": report.risk_score,
        "policy_status": report.policy_status,
        "counts": {
            "total": report.total_findings,
            "critical": report.critical_count,
            "high": report.high_count,
            "medium": report.medium_count,
            "low": report.low_count,
        },
        "top_findings": [
            {
                "severity": finding.severity,
                "category": finding.category,
                "scanner": scanner,
                "title": finding.title,
                "location": finding.file_path,
            }
            for finding, scanner in findings[:TOP_FINDINGS_FOR_SUMMARY]
        ],
    }
    try:
        summary = await ai.summarize_report(scan_data)
    except AIServiceError as error:
        logger.warning("AI report summary unavailable for scan %s: %s", scan.id, error)
        return report

    parts = [summary.executive_summary.strip()]
    if summary.key_risks:
        parts.append("Key risks:\n" + "\n".join(f"- {risk}" for risk in summary.key_risks))
    if summary.remediation_priorities:
        parts.append(
            "Remediation priorities:\n"
            + "\n".join(f"{i}. {step}" for i, step in enumerate(summary.remediation_priorities, 1))
        )
    report.summary = "\n\n".join(parts)
    await db.flush()
    return report
