import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.serializers import pagination, repository_to_api
from app.core.audit import AuditEvent, AuditOutcome, audit_event
from app.core.dependencies import CurrentUser, DBSession
from app.core.errors import APIError
from app.db.queries import get_owned_repository_by_public_id, owned_repositories, paginate
from app.db.repositories import (
    DuplicateRepositoryError,
    RepositoryBusyError,
    create_repository,
    delete_repository,
    parse_github_url,
)
from app.schemas.generated import (
    AddRepoRequest,
    Branch,
    BranchListResponse,
    RepositoryListResponse,
    RepositoryResponse,
    ValidateRepoRequest,
    ValidateRepoResponse,
)
from app.services.github import GitHubClient, GitHubUnavailableError, get_github_client

router = APIRouter(prefix="/repositories", tags=["Repositories"])
GitHub = Annotated[GitHubClient, Depends(get_github_client)]


def _parse(url: str):
    if len(url) > 1024:
        raise APIError(422, "INVALID_REPOSITORY_URL", "Repository URL is too long.")
    try:
        return parse_github_url(url)
    except ValueError as error:
        raise APIError(422, "INVALID_REPOSITORY_URL", str(error)) from None


async def _lookup(github: GitHubClient, owner: str, name: str):
    try:
        return await github.get_repository(owner, name)
    except GitHubUnavailableError as error:
        raise APIError(502, "GITHUB_UNAVAILABLE", str(error)) from None


async def _owned(db, user, repository_id: uuid.UUID):
    repository = await get_owned_repository_by_public_id(db, user_id=user.id, public_id=repository_id)
    if repository is None:
        raise APIError(404, "NOT_FOUND", "Repository not found.")
    return repository


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    result = await paginate(db, owned_repositories(user.id), page=page, page_size=pageSize)
    return RepositoryListResponse(
        status="success",
        data=[repository_to_api(repository, user) for repository in result.items],
        pagination=pagination(result),
    )


@router.post("/validate", response_model=ValidateRepoResponse)
async def validate_repository(body: ValidateRepoRequest, user: CurrentUser, github: GitHub):
    coordinates = _parse(body.url)
    found = await _lookup(github, coordinates.owner, coordinates.name)
    if found is None or found.private:
        return ValidateRepoResponse(status="success", data={"valid": False})
    return ValidateRepoResponse(
        status="success",
        data={
            "valid": True,
            "name": found.name,
            "owner": found.owner,
            "defaultBranch": found.default_branch,
        },
    )


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def add_repository(body: AddRepoRequest, user: CurrentUser, db: DBSession, github: GitHub):
    coordinates = _parse(body.url)
    found = await _lookup(github, coordinates.owner, coordinates.name)
    if found is None or found.private:
        # Private repositories need credentials the MVP does not manage yet.
        raise APIError(422, "REPOSITORY_NOT_FOUND", "Repository was not found or is not public.")
    try:
        repository = await create_repository(
            db,
            owner_id=user.id,
            url=body.url,
            name=found.name,
            default_branch=found.default_branch,
            language=found.language,
            validated=True,
        )
    except DuplicateRepositoryError:
        raise APIError(409, "REPOSITORY_EXISTS", "This repository has already been added.") from None
    await db.refresh(repository)
    return RepositoryResponse(status="success", data=repository_to_api(repository, user))


@router.get("/{id}", response_model=RepositoryResponse)
async def get_repository(id: uuid.UUID, user: CurrentUser, db: DBSession):
    repository = await _owned(db, user, id)
    return RepositoryResponse(status="success", data=repository_to_api(repository, user))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_repository(id: uuid.UUID, request: Request, user: CurrentUser, db: DBSession):
    repository = await _owned(db, user, id)
    target = {"repository_id": repository.public_id, "repository_url": repository.github_url}
    try:
        await delete_repository(db, repository=repository)
    except RepositoryBusyError:
        audit_event(
            AuditEvent.REPOSITORY_DELETE_BLOCKED,
            outcome=AuditOutcome.DENIED,
            request=request,
            actor_id=user.public_id,
            reason="scan_in_progress",
            **target,
        )
        raise APIError(
            409, "SCAN_IN_PROGRESS", "Cancel or wait for running scans before removing this repository."
        ) from None
    await db.commit()
    audit_event(
        AuditEvent.REPOSITORY_DELETED,
        outcome=AuditOutcome.SUCCESS,
        request=request,
        actor_id=user.public_id,
        **target,
    )
    return None


@router.get("/{id}/branches", response_model=BranchListResponse)
async def list_branches(id: uuid.UUID, user: CurrentUser, db: DBSession, github: GitHub):
    repository = await _owned(db, user, id)
    coordinates = parse_github_url(repository.github_url)
    try:
        branches = await github.list_branches(coordinates.owner, coordinates.name)
    except GitHubUnavailableError as error:
        raise APIError(502, "GITHUB_UNAVAILABLE", str(error)) from None
    return BranchListResponse(
        status="success",
        data=[
            Branch(
                name=branch.name,
                isDefault=branch.name == repository.default_branch,
                lastCommit=branch.sha[:7] if branch.sha else None,
            )
            for branch in branches
        ],
    )
