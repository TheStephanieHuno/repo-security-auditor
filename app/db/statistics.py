from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Finding, Repository, Scan, ScannerRun


@dataclass(frozen=True)
class UserStatistics:
    total_repositories: int
    total_scans: int
    completed_scans: int
    partial_scans: int
    failed_scans: int
    critical_findings: int
    high_findings: int
    open_findings: int


async def get_user_statistics(
    db: AsyncSession, *, user_id: int
) -> UserStatistics:
    repository_counts = await db.execute(
        select(func.count(Repository.id)).where(Repository.owner_id == user_id)
    )
    total_repositories = repository_counts.scalar_one()

    scan_counts = await db.execute(
        select(
            func.count(Scan.id),
            func.sum(case((Scan.status == "COMPLETED", 1), else_=0)),
            func.sum(case((Scan.status == "PARTIAL", 1), else_=0)),
            func.sum(case((Scan.status == "FAILED", 1), else_=0)),
        )
        .join(Repository, Scan.repository_id == Repository.id)
        .where(
            Repository.owner_id == user_id,
            Scan.requested_by == user_id,
        )
    )
    total_scans, completed_scans, partial_scans, failed_scans = scan_counts.one()

    finding_counts = await db.execute(
        select(
            func.sum(case((Finding.severity == "CRITICAL", 1), else_=0)),
            func.sum(case((Finding.severity == "HIGH", 1), else_=0)),
            func.sum(case((Finding.review_status == "OPEN", 1), else_=0)),
        )
        .join(ScannerRun, Finding.scanner_run_id == ScannerRun.id)
        .join(Scan, ScannerRun.scan_id == Scan.id)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(
            Repository.owner_id == user_id,
            Scan.requested_by == user_id,
        )
    )
    critical_findings, high_findings, open_findings = finding_counts.one()

    return UserStatistics(
        total_repositories=total_repositories or 0,
        total_scans=total_scans or 0,
        completed_scans=completed_scans or 0,
        partial_scans=partial_scans or 0,
        failed_scans=failed_scans or 0,
        critical_findings=critical_findings or 0,
        high_findings=high_findings or 0,
        open_findings=open_findings or 0,
    )
