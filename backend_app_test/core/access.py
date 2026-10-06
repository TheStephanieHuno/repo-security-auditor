import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend_app_test.db.models import Repository, Scan, Finding, Report, User  # <-- Updated import

async def verify_user_owns_repository(db: AsyncSession, repo_id: uuid.UUID, user: User) -> Repository:
    """Ensures the repository exists and belongs to the authenticated user (FR-10)."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id, Repository.added_by == user.id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
    return repo

async def verify_user_owns_scan(db: AsyncSession, scan_id: uuid.UUID, user: User) -> Scan:
    """Ensures the scan exists and belongs to a repository owned by the user (FR-10)."""
    result = await db.execute(
        select(Scan)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(Scan.id == scan_id, Repository.added_by == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found or access denied.",
        )
    return scan

async def verify_user_owns_finding(db: AsyncSession, finding_id: uuid.UUID, user: User) -> Finding:
    """Ensures the finding belongs to a scan owned by the user (FR-10)."""
    result = await db.execute(
        select(Finding)
        .join(Repository, Finding.repository_id == Repository.id)
        .where(Finding.id == finding_id, Repository.added_by == user.id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found or access denied.",
        )
    return finding

async def verify_user_owns_report(db: AsyncSession, report_id: uuid.UUID, user: User) -> Report:
    """Ensures the report belongs to a scan owned by the user (FR-10)."""
    result = await db.execute(
        select(Report)
        .join(Scan, Report.scan_id == Scan.id)
        .join(Repository, Scan.repository_id == Repository.id)
        .where(Report.id == report_id, Repository.added_by == user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or access denied.",
        )
    return report