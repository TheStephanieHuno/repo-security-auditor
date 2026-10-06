import math
import uuid
from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Finding, Report, Repository, Scan, ScannerRun, ScanStatus


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


def _owned_scans(user_id: int) -> Select[tuple[Scan]]:
    return (
        select(Scan)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(
            Repository.owner_id == user_id,
            Scan.requested_by == user_id,
        )
    )


async def get_owned_scan(
    db: AsyncSession, *, user_id: int, scan_id: int
) -> Scan | None:
    result = await db.execute(_owned_scans(user_id).where(Scan.id == scan_id))
    return result.scalar_one_or_none()


async def get_owned_scan_progress(
    db: AsyncSession, *, user_id: int, scan_id: int
) -> Scan | None:
    """Load an owned scan with its scanner runs eagerly, for progress reads."""
    result = await db.execute(
        _owned_scans(user_id)
        .where(Scan.id == scan_id)
        .options(selectinload(Scan.scanner_runs))
    )
    return result.scalar_one_or_none()


async def list_scan_scanner_runs(
    db: AsyncSession, *, user_id: int, scan_id: int
) -> list[ScannerRun]:
    result = await db.execute(
        select(ScannerRun)
        .join(Scan, ScannerRun.scan_id == Scan.id)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(
            Scan.id == scan_id,
            Repository.owner_id == user_id,
            Scan.requested_by == user_id,
        )
        .order_by(ScannerRun.scanner_name)
    )
    return list(result.scalars().all())


async def list_repository_scans(
    db: AsyncSession,
    *,
    user_id: int,
    repository_id: int,
    status: ScanStatus | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Scan]:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    if offset < 0:
        raise ValueError("offset must be non-negative")
    query = _owned_scans(user_id).where(Scan.repository_id == repository_id)
    if status is not None:
        query = query.where(Scan.status == status.value)
    # id breaks ties between scans created within the same timestamp.
    query = query.order_by(Scan.created_at.desc(), Scan.id.desc()).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_latest_repository_scan(
    db: AsyncSession, *, user_id: int, repository_id: int
) -> Scan | None:
    scans = await list_repository_scans(
        db, user_id=user_id, repository_id=repository_id, limit=1
    )
    return scans[0] if scans else None


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


# ------------------------------------------------------------------ pagination

T = TypeVar("T")
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(self.total / self.page_size)) if self.total else 0


async def paginate(
    db: AsyncSession, query: Select[tuple[T]], *, page: int = 1, page_size: int = 20
) -> Page[T]:
    """Run ``query`` for one page and count all matching rows in the same filter."""
    if page < 1:
        raise ValueError("page must be at least 1")
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")
    total = await db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    )
    result = await db.execute(query.limit(page_size).offset((page - 1) * page_size))
    return Page(items=list(result.scalars().all()), total=total or 0, page=page, page_size=page_size)


# --------------------------------------------- ownership-scoped base queries


def owned_repositories(user_id: int) -> Select[tuple[Repository]]:
    return (
        select(Repository)
        .where(Repository.owner_id == user_id)
        .order_by(Repository.created_at.desc(), Repository.id.desc())
    )


def owned_scans(user_id: int) -> Select[tuple[Scan]]:
    return _owned_scans(user_id).order_by(Scan.created_at.desc(), Scan.id.desc())


def owned_findings(user_id: int) -> Select[tuple[Finding]]:
    return (
        select(Finding)
        .join(ScannerRun, Finding.scanner_run_id == ScannerRun.id)
        .join(Scan, ScannerRun.scan_id == Scan.id)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(Repository.owner_id == user_id, Scan.requested_by == user_id)
        .order_by(Finding.created_at.desc(), Finding.id.desc())
    )


def owned_reports(user_id: int) -> Select[tuple[Report]]:
    return (
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(Repository.owner_id == user_id, Scan.requested_by == user_id)
        .order_by(Report.created_at.desc(), Report.id.desc())
    )


async def get_owned_repository_by_public_id(
    db: AsyncSession, *, user_id: int, public_id: uuid.UUID
) -> Repository | None:
    result = await db.execute(owned_repositories(user_id).where(Repository.public_id == public_id))
    return result.scalar_one_or_none()


async def get_owned_scan_by_public_id(
    db: AsyncSession, *, user_id: int, public_id: uuid.UUID
) -> Scan | None:
    result = await db.execute(_owned_scans(user_id).where(Scan.public_id == public_id))
    return result.scalar_one_or_none()


async def get_owned_finding_by_public_id(
    db: AsyncSession, *, user_id: int, public_id: uuid.UUID
) -> Finding | None:
    result = await db.execute(owned_findings(user_id).where(Finding.public_id == public_id))
    return result.scalar_one_or_none()


async def get_owned_report_by_public_id(
    db: AsyncSession, *, user_id: int, public_id: uuid.UUID
) -> Report | None:
    result = await db.execute(owned_reports(user_id).where(Report.public_id == public_id))
    return result.scalar_one_or_none()
