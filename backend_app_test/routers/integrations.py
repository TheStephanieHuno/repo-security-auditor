from datetime import datetime, timezone
from fastapi import APIRouter, status
from backend_app_test.schemas.generated import (
    GitHubResponse,
    GitHubIntegration,
)

router = APIRouter(prefix="/integrations", tags=["Integrations"])

@router.get("/github", response_model=GitHubResponse)
async def get_github_status():
    return GitHubResponse(
        status="success",
        data=GitHubIntegration(connected=True, username="octocat", connectedAt=datetime.now(timezone.utc)),
    )

@router.post("/github", response_model=GitHubResponse)
async def connect_github():
    return GitHubResponse(
        status="success",
        data=GitHubIntegration(connected=True, username="octocat", connectedAt=datetime.now(timezone.utc)),
    )

@router.delete("/github", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_github():
    return None