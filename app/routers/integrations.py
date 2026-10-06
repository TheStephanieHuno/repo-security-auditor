from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser
from app.core.errors import APIError
from app.schemas.generated import GitHubIntegration, GitHubResponse

router = APIRouter(prefix="/integrations", tags=["Integrations"])

# GitHub OAuth is post-MVP (US-26). These endpoints now require authentication
# and report the integration honestly as not connected instead of returning
# a fake "octocat" account.


@router.get("/github", response_model=GitHubResponse)
async def get_github_status(user: CurrentUser):
    return GitHubResponse(status="success", data=GitHubIntegration(connected=False))


@router.post("/github", response_model=GitHubResponse)
async def connect_github(user: CurrentUser):
    raise APIError(501, "NOT_IMPLEMENTED", "GitHub account connection is not available yet.")


@router.delete("/github", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_github(user: CurrentUser):
    return None
