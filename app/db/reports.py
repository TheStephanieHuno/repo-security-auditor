from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Finding,
    PolicyStatus,
    Report,
    ReportStatus,
    Scan,
    ScanStatus,
    ScannerRun,
)


@dataclass(frozen=True)
class RiskPolicy:
    version: str = "risk-v1"
    critical_weight: int = 40
    high_weight: int = 20
    medium_weight: int = 5
    low_weight: int = 1
    failing_severities: frozenset[str] = frozenset({"CRITICAL", "HIGH"})

    def score(self, counts: dict[str, int]) -> int:
        return min(
            100,
            counts.get("CRITICAL", 0) * self.critical_weight
            + counts.get("HIGH", 0) * self.high_weight
            + counts.get("MEDIUM", 0) * self.medium_weight
            + counts.get("LOW", 0) * self.low_weight,
        )

    def policy_status(self, counts: dict[str, int]) -> PolicyStatus:
        if any(counts.get(severity, 0) for severity in self.failing_severities):
            return PolicyStatus.FAIL
        return PolicyStatus.PASS


DEFAULT_RISK_POLICY = RiskPolicy()


async def aggregate_scan_findings(
    db: AsyncSession, *, scan_id: int
) -> dict[str, int]:
    severity_counts = await db.execute(
        select(
            Finding.severity,
            func.count(Finding.id),
        )
        .join(ScannerRun, Finding.scanner_run_id == ScannerRun.id)
        .where(ScannerRun.scan_id == scan_id)
        .group_by(Finding.severity)
    )
    counts = {severity: count for severity, count in severity_counts.all()}
    return {
        "total_findings": sum(counts.values()),
        "critical_count": counts.get("CRITICAL", 0),
        "high_count": counts.get("HIGH", 0),
        "medium_count": counts.get("MEDIUM", 0),
        "low_count": counts.get("LOW", 0),
    }


async def build_scan_report(
    db: AsyncSession,
    *,
    scan: Scan,
    policy: RiskPolicy = DEFAULT_RISK_POLICY,
) -> Report:
    if scan.status not in {
        ScanStatus.COMPLETED.value,
        ScanStatus.PARTIAL.value,
        ScanStatus.FAILED.value,
    }:
        raise ValueError("reports can only be generated for terminal scans")

    counts = await aggregate_scan_findings(db, scan_id=scan.id)
    severity_counts = {
        "CRITICAL": counts["critical_count"],
        "HIGH": counts["high_count"],
        "MEDIUM": counts["medium_count"],
        "LOW": counts["low_count"],
    }
    report = (
        await db.execute(select(Report).where(Report.scan_id == scan.id))
    ).scalar_one_or_none()
    if report is None:
        report = Report(
            scan_id=scan.id,
            status=ReportStatus.GENERATING.value,
            report_version=policy.version,
        )
        db.add(report)
    else:
        report.status = ReportStatus.GENERATING.value
        report.report_version = policy.version

    report.total_findings = counts["total_findings"]
    report.critical_count = counts["critical_count"]
    report.high_count = counts["high_count"]
    report.medium_count = counts["medium_count"]
    report.low_count = counts["low_count"]
    report.risk_score = policy.score(severity_counts)
    report.policy_status = policy.policy_status(severity_counts).value
    report.summary = (
        f"{report.total_findings} findings: "
        f"{report.critical_count} critical, "
        f"{report.high_count} high, "
        f"{report.medium_count} medium, "
        f"{report.low_count} low."
    )
    report.status = ReportStatus.READY.value
    report.generated_at = scan.completed_at
    await db.flush()
    return report
