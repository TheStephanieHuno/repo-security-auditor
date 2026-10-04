import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status, Query
from app.schemas.generated import (
    Repository,
    RepositoryResponse,
    RepositoryListResponse,
    ValidateRepoRequest,
    ValidateRepoResponse,
    AddRepoRequest,
    Branch,
    BranchListResponse,
    Pagination,
)

router = APIRouter(prefix="/repositories", tags=["Repositories"])

SAMPLE_REPO_ID = uuid.uuid4()
SAMPLE_REPO = Repository(
    id=SAMPLE_REPO_ID,
    url="https://github.com/org/repo",
    name="repo",
    owner="org",
    provider="github",
    defaultBranch="main",
    isValid=True,
    addedBy=uuid.uuid4(),
    createdAt=datetime.now(timezone.utc),
    updatedAt=datetime.now(timezone.utc),
)

@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    return RepositoryListResponse(
        status="success",
        data=[SAMPLE_REPO],
        pagination=Pagination(page=page, pageSize=pageSize, totalItems=1, totalPages=1),
    )

@router.post("/validate", response_model=ValidateRepoResponse)
async def validate_repository(body: ValidateRepoRequest):
    return ValidateRepoResponse(
        status="success",
        data={"valid": True, "name": "repo", "owner": "org", "defaultBranch": "main"},
    )

@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def add_repository(body: AddRepoRequest):
    new_repo = Repository(
        id=uuid.uuid4(),
        url=body.url,
        name=body.url.rstrip("/").split("/")[-1],
        owner="org",
        provider="github",
        defaultBranch="main",
        isValid=True,
        addedBy=uuid.uuid4(),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    return RepositoryResponse(status="success", data=new_repo)

@router.get("/{id}", response_model=RepositoryResponse)
async def get_repository(id: uuid.UUID):
    return RepositoryResponse(status="success", data=SAMPLE_REPO)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_repository(id: uuid.UUID):
    return None

@router.get("/{id}/branches", response_model=BranchListResponse)
async def list_branches(id: uuid.UUID):
    return BranchListResponse(
        status="success",
        data=[
            Branch(name="main", isDefault=True, lastCommit="7f3b4c1"),
            Branch(name="develop", isDefault=False, lastCommit="a1b2c3d"),
            Branch(name="feature/auth", isDefault=False, lastCommit="9e8d7c6"),
        ],
    )