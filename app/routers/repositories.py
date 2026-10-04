import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status, Query
from app.schemas.generated import (
    Repository,
    RepositoryResponse,
    RepositoryListResponse,
    ValidateRepositoryRequest,
    ValidateRepositoryResponse,
    ValidateRepositoryData,
    AddRepositoryRequest,
    Branch,
    BranchListResponse,
    PaginationMeta,
)

router = APIRouter(prefix="/repositories", tags=["Repositories"])

SAMPLE_REPO_ID = uuid.uuid4()

@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    mock_repo = Repository(
        id=SAMPLE_REPO_ID,
        url="https://github.com/organization/core-repo",
        name="core-repo",
        owner="organization",
        provider="github",
        defaultBranch="main",
        isValid=True,
        addedBy=uuid.uuid4(),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return RepositoryListResponse(
        status="success",
        data=[mock_repo],
        pagination=PaginationMeta(page=page, pageSize=pageSize, totalItems=1, totalPages=1),
    )

@router.post("/validate", response_model=ValidateRepositoryResponse)
async def validate_repository(body: ValidateRepositoryRequest):
    return ValidateRepositoryResponse(
        status="success",
        data=ValidateRepositoryData(
            valid=True,
            name="core-repo",
            owner="organization",
            defaultBranch="main",
        ),
    )

@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def add_repository(body: AddRepositoryRequest):
    mock_repo = Repository(
        id=uuid.uuid4(),
        url=body.url,
        name="new-repository",
        owner="organization",
        provider="github",
        defaultBranch="main",
        isValid=True,
        addedBy=uuid.uuid4(),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return RepositoryResponse(status="success", data=mock_repo)

@router.get("/{id}/branches", response_model=BranchListResponse)
async def list_branches(id: uuid.UUID):
    return BranchListResponse(
        status="success",
        data=[
            Branch(name="main", isDefault=True, lastCommit="7f3b4c1"),
            Branch(name="develop", isDefault=False, lastCommit="a1b2c3d"),
            Branch(name="feature/login", isDefault=False, lastCommit="9e8d7c6"),
        ],
    )