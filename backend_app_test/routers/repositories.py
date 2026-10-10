import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend_app_test.db.session import get_db
from backend_app_test.core.dependencies import get_current_user
from backend_app_test.db.models import Repository as DBRepository, User as DBUser
from backend_app_test.core.access import verify_user_owns_repository
from backend_app_test.core.audit import AuditEvent, AuditOutcome, audit_event
from backend_app_test.services.github_service import validate_github_repository, fetch_github_branches
from backend_app_test.schemas.generated import (
    Repository, RepositoryResponse, RepositoryListResponse, ValidateRepoRequest,
    ValidateRepoResponse, AddRepoRequest, Branch, BranchListResponse, Pagination,
)

router = APIRouter(prefix="/repositories", tags=["Repositories"])

def ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

@router.get("", response_model=RepositoryListResponse)
async def list_repositories(page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    offset = (page - 1) * pageSize
    query = select(DBRepository).where(DBRepository.added_by == current_user.id)
    result = await db.execute(query.offset(offset).limit(pageSize))
    repos = result.scalars().all()
    count_query = select(func.count()).select_from(DBRepository).where(DBRepository.added_by == current_user.id)
    total_items = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total_items + pageSize - 1) // pageSize)
    data = [Repository(id=r.id, url=r.url, name=r.name, owner=r.owner, provider=r.provider, defaultBranch=r.default_branch, isValid=r.is_valid, addedBy=r.added_by, createdAt=ensure_utc(r.created_at), updatedAt=ensure_utc(r.updated_at)) for r in repos]
    return RepositoryListResponse(status="success", data=data, pagination=Pagination(page=page, pageSize=pageSize, totalItems=total_items, totalPages=total_pages))

@router.post("/validate", response_model=ValidateRepoResponse)
async def validate_repository(body: ValidateRepoRequest, current_user: DBUser = Depends(get_current_user)):
    if "github.com" not in body.url.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only GitHub repository URLs are supported.")
    result = await validate_github_repository(body.url)
    if not result["valid"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The repository could not be found on GitHub.")
    return ValidateRepoResponse(status="success", data=result)

@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def add_repository(body: AddRepoRequest, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(DBRepository).where(DBRepository.url == body.url, DBRepository.added_by == current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Repository already added.")
    validation = await validate_github_repository(body.url)
    if not validation["valid"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Repository URL is invalid or unreachable.")
    now = datetime.now(timezone.utc)
    new_repo = DBRepository(id=uuid.uuid4(), url=body.url, name=validation["name"], owner=validation["owner"], provider="github", default_branch=validation["defaultBranch"], is_valid=True, added_by=current_user.id, created_at=now, updated_at=now)
    db.add(new_repo)
    await db.commit()
    await db.refresh(new_repo)
    return RepositoryResponse(status="success", data=Repository(id=new_repo.id, url=new_repo.url, name=new_repo.name, owner=new_repo.owner, provider=new_repo.provider, defaultBranch=new_repo.default_branch, isValid=new_repo.is_valid, addedBy=new_repo.added_by, createdAt=ensure_utc(new_repo.created_at), updatedAt=ensure_utc(new_repo.updated_at)))

@router.get("/{id}", response_model=RepositoryResponse)
async def get_repository(id: uuid.UUID, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = await verify_user_owns_repository(db, id, current_user)
    return RepositoryResponse(status="success", data=Repository(id=repo.id, url=repo.url, name=repo.name, owner=repo.owner, provider=repo.provider, defaultBranch=repo.default_branch, isValid=repo.is_valid, addedBy=repo.added_by, createdAt=ensure_utc(repo.created_at), updatedAt=ensure_utc(repo.updated_at)))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_repository(id: uuid.UUID, request: Request, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = await verify_user_owns_repository(db, id, current_user)
    repository_url = repo.url
    await db.execute(delete(DBRepository).where(DBRepository.id == id))
    await db.commit()
    audit_event(AuditEvent.REPOSITORY_DELETED, outcome=AuditOutcome.SUCCESS, request=request,
                actor_id=current_user.id, repository_id=id, repository_url=repository_url)
    return None

@router.get("/{id}/branches", response_model=BranchListResponse)
async def list_branches(id: uuid.UUID, current_user: DBUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = await verify_user_owns_repository(db, id, current_user)
    branches = await fetch_github_branches(repo.url)
    return BranchListResponse(status="success", data=[Branch(name=b["name"], isDefault=b["isDefault"], lastCommit=b["lastCommit"]) for b in branches])
