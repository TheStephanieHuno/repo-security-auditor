import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.serializers import findings_to_api, pagination, scans_to_api
from app.core.dependencies import CurrentUser, DBSession
from app.core.errors import APIError
from app.db.lifecycle import cancel_scan, create_scan_with_scanner_runs
from app.db.models import Repository, Scan, ScannerName
from app.db.queries import (
    get_owned_repository_by_public_id,
    get_owned_scan_by_public_id,
    owned_findings,
    owned_scans,
    paginate,
)
from app.routers.findings import apply_finding_filters
from app.scanners import default_checks
from app.schemas.generated import (
    FindingListResponse,
    ScanListResponse,
    ScanProgressResponse,
    ScanResponse,
    StartScanRequest,
)
from app.services.scan_runner import ScanDispatcher, get_scan_dispatcher
from app.services.workspace import validate_branch

router = APIRouter(prefix="/scans", tags=["Scans"])
Dispatcher = Annotated[ScanDispatcher, Depends(get_scan_dispatcher)]


async def _owned(db, user, scan_id: uuid.UUID) -> Scan:
    scan = await get_owned_scan_by_public_id(db, user_id=user.id, public_id=scan_id)
    if scan is None:
        raise APIError(404, "NOT_FOUND", "Scan not found.")
    return scan


@router.get("", response_model=ScanListResponse)
async def list_scans(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    repositoryId: uuid.UUID | None = None,
):
    query = owned_scans(user.id)
    if repositoryId is not None:
        query = query.where(Repository.public_id == repositoryId)
    result = await paginate(db, query, page=page, page_size=pageSize)
    return ScanListResponse(
        status="success", data=await scans_to_api(db, result.items), pagination=pagination(result)
    )


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def start_scan(body: StartScanRequest, user: CurrentUser, db: DBSession, dispatcher: Dispatcher):
    try:
        branch = validate_branch(body.branch.strip())
    except ValueError as error:
        raise APIError(422, "INVALID_BRANCH", str(error)) from None
    repository = await get_owned_repository_by_public_id(
        db, user_id=user.id, public_id=body.repositoryId
    )
    if repository is None:
        raise APIError(404, "NOT_FOUND", "Repository not found.")
    scan = await create_scan_with_scanner_runs(
        db,
        user_id=user.id,
        repository_id=repository.id,
        target_branch=branch,
        scanner_names=[ScannerName(check.name) for check in default_checks()],
    )
    assert scan is not None  # ownership was verified above
    # The durable QUEUED rows must exist before a worker can pick up the job.
    await db.commit()
    dispatcher.dispatch(scan.id)
    await db.refresh(scan)
    return ScanResponse(status="success", data=(await scans_to_api(db, [scan]))[0])


@router.get("/{id}", response_model=ScanResponse)
async def get_scan(id: uuid.UUID, user: CurrentUser, db: DBSession):
    scan = await _owned(db, user, id)
    return ScanResponse(status="success", data=(await scans_to_api(db, [scan]))[0])


@router.get("/{id}/status", response_model=ScanProgressResponse)
async def get_scan_status(id: uuid.UUID, user: CurrentUser, db: DBSession):
    scan = await _owned(db, user, id)
    view = (await scans_to_api(db, [scan]))[0]
    return ScanProgressResponse(
        status="success", data={"id": view.id, "status": view.status, "progress": view.progress}
    )


@router.post("/{id}/cancel", response_model=ScanResponse)
async def cancel(id: uuid.UUID, user: CurrentUser, db: DBSession):
    scan = await _owned(db, user, id)
    if not await cancel_scan(db, scan=scan):
        raise APIError(409, "SCAN_FINISHED", "Only queued or running scans can be cancelled.")
    await db.refresh(scan)
    return ScanResponse(status="success", data=(await scans_to_api(db, [scan]))[0])


@router.get("/{id}/findings", response_model=FindingListResponse)
async def get_scan_findings(
    id: uuid.UUID,
    user: CurrentUser,
    db: DBSession,
    severity: str | None = None,
    reviewStatus: str | None = None,
    confidence: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    scan = await _owned(db, user, id)
    query = apply_finding_filters(
        owned_findings(user.id).where(Scan.id == scan.id),
        severity=severity,
        review_status=reviewStatus,
        confidence=confidence,
        category=category,
    )
    result = await paginate(db, query, page=page, page_size=pageSize)
    return FindingListResponse(
        status="success",
        data=await findings_to_api(db, result.items),
        pagination=pagination(result),
    )
