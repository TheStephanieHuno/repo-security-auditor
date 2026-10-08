from datetime import datetime, timezone
from fastapi import APIRouter, status, Depends
from backend_app_test.core.dependencies import get_current_user
from backend_app_test.db.models import User as DBUser
from backend_app_test.schemas.generated import GitHubResponse, GitHubIntegration

router = APIRouter(prefix="/integrations", tags=["Integrations"])

@router.get("/github", response_model=GitHubResponse)
async def get_github_status(current_user: DBUser = Depends(get_current_user)):
    return GitHubResponse(status="success", data=GitHubIntegration(connected=True, username="octocat", connectedAt=datetime.now(timezone.utc)))

@router.post("/github", response_model=GitHubResponse)
async def connect_github(current_user: DBUser = Depends(get_current_user)):
    return GitHubResponse(status="success", data=GitHubIntegration(connected=True, username="octocat", connectedAt=datetime.now(timezone.utc)))

@router.delete("/github", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_github(current_user: DBUser = Depends(get_current_user)):
    return None
