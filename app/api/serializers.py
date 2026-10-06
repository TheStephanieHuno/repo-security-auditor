"""Convert persistence rows into the openapi.yaml response schemas.

Persistence uses integer keys and uppercase enums; the public API uses
``public_id`` UUIDs and the lowercase vocabulary of ``app/schemas/generated.py``.
List endpoints load related data in batches instead of per row.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.lifecycle import TERMINAL_SCAN_STATUSES, TERMINAL_SCANNER_RUN_STATUSES
from app.db.models import (
    Evidence,
    ExplanationStatus,
    Finding,
    FindingCategory,
    FindingExplanation,
    Report,
    Repository,
    Scan,
    ScannerRun,
    ScanStatus,
    User,
)
from app.db.queries import Page
from app.db.repositories import parse_github_url
from app.schemas import generated as schemas

SCAN_STATUS_TO_API = {
    ScanStatus.QUEUED.value: schemas.ScanStatus.queued,
    ScanStatus.RUNNING.value: schemas.ScanStatus.running,
    ScanStatus.COMPLETED.value: schemas.ScanStatus.completed,
    # The public contract has no "partial"; results are available, so it is
    # reported as completed and the per-scanner detail lives in the report.
    ScanStatus.PARTIAL.value: schemas.ScanStatus.completed,
    ScanStatus.FAILED.value: schemas.ScanStatus.failed,
    ScanStatus.CANCELLED.value: schemas.ScanStatus.cancelled,
}
CATEGORY_LABELS = {
    FindingCategory.CODE.value: "Code Vulnerability",
    FindingCategory.SECRET.value: "Secret Exposure",
    FindingCategory.DEPENDENCY.value: "Dependency Vulnerability",
    FindingCategory.CONFIGURATION.value: "Insecure Configuration",
}
REPORT_STATUS_TO_API = {
    "QUEUED": schemas.ReportStatus.generating,
    "GENERATING": schemas.ReportStatus.generating,
    "READY": schemas.ReportStatus.ready,
    "FAILED": schemas.ReportStatus.failed,
}


def aware(value: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; every stored timestamp is UTC."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def pagination(page: Page) -> schemas.Pagination:
    return schemas.Pagination(
        page=page.page, pageSize=page.page_size, totalItems=page.total, totalPages=page.total_pages
    )


def user_to_api(user: User) -> schemas.User:
    return schemas.User(
        id=user.public_id,
        name=user.name,
        email=user.email,
        role=schemas.UserRole(user.role.lower()),
        createdAt=aware(user.created_at),
        updatedAt=aware(user.updated_at),
    )


def repository_to_api(repository: Repository, owner: User) -> schemas.Repository:
    coordinates = parse_github_url(repository.github_url)
    return schemas.Repository(
        id=repository.public_id,
        url=repository.github_url,
        name=repository.name,
        owner=coordinates.owner,
        provider="github",
        defaultBranch=repository.default_branch or "main",
        isValid=repository.last_validated_at is not None,
        addedBy=owner.public_id,
        createdAt=aware(repository.created_at),
        updatedAt=aware(repository.updated_at),
    )


def scan_progress(scan_status: str, run_statuses: Sequence[str]) -> int:
    if scan_status in TERMINAL_SCAN_STATUSES:
        return 100
    if not run_statuses:
        return 0
    finished = sum(status in TERMINAL_SCANNER_RUN_STATUSES for status in run_statuses)
    if scan_status == ScanStatus.QUEUED.value:
        return 0
    # Claimed but nothing finished yet still shows movement.
    return min(99, max(5, round(100 * finished / len(run_statuses))))


async def scans_to_api(db: AsyncSession, scans: Sequence[Scan]) -> list[schemas.Scan]:
    if not scans:
        return []
    scan_ids = [scan.id for scan in scans]
    run_statuses: dict[int, list[str]] = defaultdict(list)
    for scan_id, status in await db.execute(
        select(ScannerRun.scan_id, ScannerRun.status).where(ScannerRun.scan_id.in_(scan_ids))
    ):
        run_statuses[scan_id].append(status)
    counts: dict[int, dict[str, int]] = defaultdict(dict)
    for scan_id, severity, count in await db.execute(
        select(ScannerRun.scan_id, Finding.severity, func.count(Finding.id))
        .join(Finding, Finding.scanner_run_id == ScannerRun.id)
        .where(ScannerRun.scan_id.in_(scan_ids))
        .group_by(ScannerRun.scan_id, Finding.severity)
    ):
        counts[scan_id][severity] = count
    repository_ids = dict(
        (
            await db.execute(
                select(Repository.id, Repository.public_id).where(
                    Repository.id.in_({scan.repository_id for scan in scans})
                )
            )
        ).all()
    )
    return [
        schemas.Scan(
            id=scan.public_id,
            repositoryId=repository_ids[scan.repository_id],
            branch=scan.target_branch,
            status=SCAN_STATUS_TO_API[scan.status],
            progress=scan_progress(scan.status, run_statuses[scan.id]),
            findingsCount=schemas.FindingsCount(
                critical=counts[scan.id].get("CRITICAL", 0),
                high=counts[scan.id].get("HIGH", 0),
                medium=counts[scan.id].get("MEDIUM", 0),
                low=counts[scan.id].get("LOW", 0),
                info=0,
            ),
            startedAt=aware(scan.started_at),
            completedAt=aware(scan.completed_at),
            cancelledAt=aware(scan.cancelled_at),
            createdAt=aware(scan.created_at),
            updatedAt=aware(scan.updated_at),
        )
        for scan in scans
    ]


async def findings_to_api(db: AsyncSession, findings: Sequence[Finding]) -> list[schemas.Finding]:
    if not findings:
        return []
    finding_ids = [finding.id for finding in findings]
    owners = {
        run_id: (scan_public_id, repository_public_id)
        for run_id, scan_public_id, repository_public_id in await db.execute(
            select(ScannerRun.id, Scan.public_id, Repository.public_id)
            .join(Scan, ScannerRun.scan_id == Scan.id)
            .join(Repository, Scan.repository_id == Repository.id)
            .where(ScannerRun.id.in_({finding.scanner_run_id for finding in findings}))
        )
    }
    snippets: dict[int, str] = {}
    for finding_id, snippet in await db.execute(
        select(Evidence.finding_id, Evidence.code_snippet)
        .where(Evidence.finding_id.in_(finding_ids), Evidence.code_snippet.is_not(None))
        .order_by(Evidence.id)
    ):
        snippets.setdefault(finding_id, snippet)
    explanations: dict[int, str] = {}
    for finding_id, text in await db.execute(
        select(FindingExplanation.finding_id, FindingExplanation.explanation)
        .where(
            FindingExplanation.finding_id.in_(finding_ids),
            FindingExplanation.status == ExplanationStatus.READY.value,
        )
        .order_by(FindingExplanation.id)
    ):
        explanations[finding_id] = text  # latest READY explanation wins
    reviewer_ids = {finding.reviewed_by for finding in findings if finding.reviewed_by}
    reviewers = (
        dict((await db.execute(select(User.id, User.public_id).where(User.id.in_(reviewer_ids)))).all())
        if reviewer_ids
        else {}
    )
    return [
        schemas.Finding(
            id=finding.public_id,
            scanId=owners[finding.scanner_run_id][0],
            repositoryId=owners[finding.scanner_run_id][1],
            severity=schemas.Severity(finding.severity.lower()),
            confidence=schemas.Confidence(finding.confidence.lower()),
            category=CATEGORY_LABELS.get(finding.category, finding.category),
            title=finding.title,
            description=finding.description,
            filePath=finding.file_path or "",
            lineStart=finding.line_start,
            lineEnd=finding.line_end,
            codeSnippet=snippets.get(finding.id),
            recommendation=finding.recommendation,
            aiExplanation=explanations.get(finding.id),
            reviewStatus=schemas.ReviewStatus(finding.review_status.lower()),
            reviewNote=finding.review_note,
            reviewedBy=reviewers.get(finding.reviewed_by) if finding.reviewed_by else None,
            reviewedAt=aware(finding.reviewed_at),
            createdAt=aware(finding.created_at),
        )
        for finding in findings
    ]


async def reports_to_api(db: AsyncSession, reports: Sequence[Report]) -> list[schemas.Report]:
    if not reports:
        return []
    scan_ids = dict(
        (
            await db.execute(
                select(Scan.id, Scan.public_id).where(Scan.id.in_({r.scan_id for r in reports}))
            )
        ).all()
    )
    return [
        schemas.Report(
            id=report.public_id,
            scanId=scan_ids[report.scan_id],
            status=REPORT_STATUS_TO_API[report.status],
            format="pdf",
            fileUrl=f"/api/reports/{report.public_id}/pdf" if report.status == "READY" else None,
            fileSize=None,
            createdAt=aware(report.created_at),
            completedAt=aware(report.generated_at) if report.status == "READY" else None,
        )
        for report in reports
    ]
