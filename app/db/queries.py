from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Finding, Report, Repository, Scan, ScannerRun


async def get_owned_repository(
    db: AsyncSession, *, user_id: int, repository_id: int
) -> Repository | None:
    result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.owner_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_owned_repositories(
    db: AsyncSession, *, user_id: int
) -> list[Repository]:
    result = await db.execute(
        select(Repository)
        .where(Repository.owner_id == user_id)
        .order_by(Repository.created_at.desc())
    )
    return list(result.scalars().all())


async def get_owned_scan(
    db: AsyncSession, *, user_id: int, scan_id: int
) -> Scan | None:
    result = await db.execute(
        select(Scan)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(
            Scan.id == scan_id,
            Repository.owner_id == user_id,
            Scan.requested_by == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_repository_scans(
    db: AsyncSession, *, user_id: int, repository_id: int
) -> list[Scan]:
    result = await db.execute(
        select(Scan)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(
            Scan.repository_id == repository_id,
            Repository.owner_id == user_id,
            Scan.requested_by == user_id,
        )
        .order_by(Scan.created_at.desc())
    )
    return list(result.scalars().all())


async def list_scan_findings(
    db: AsyncSession, *, user_id: int, scan_id: int
) -> list[Finding]:
    result = await db.execute(
        select(Finding)
        .join(Finding.scanner_run)
        .join(Scan, ScannerRun.scan_id == Scan.id)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(
            Scan.id == scan_id,
            Repository.owner_id == user_id,
            Scan.requested_by == user_id,
        )
        .order_by(Finding.created_at.desc())
    )
    return list(result.scalars().all())


async def get_owned_finding(
    db: AsyncSession, *, user_id: int, finding_id: int
) -> Finding | None:
    result = await db.execute(
        select(Finding)
        .join(Finding.scanner_run)
        .join(Scan, ScannerRun.scan_id == Scan.id)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(
            Finding.id == finding_id,
            Repository.owner_id == user_id,
            Scan.requested_by == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_owned_report(
    db: AsyncSession, *, user_id: int, report_id: int
) -> Report | None:
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(
            Report.id == report_id,
            Repository.owner_id == user_id,
            Scan.requested_by == user_id,
        )
    )
    return result.scalar_one_or_none()
