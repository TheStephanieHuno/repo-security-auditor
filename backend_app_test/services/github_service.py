import os
import httpx
from typing import Optional, List, Dict, Any

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

def _get_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Repo-Security-Auditor"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def parse_github_url(url: str) -> Optional[tuple[str, str]]:
    """
    Parses a GitHub URL to extract owner and repository name.
    Supports formats:
    - https://github.com/owner/repo
    - git@github.com:owner/repo.git
    """
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
        
    if "github.com/" in cleaned:
        parts = cleaned.split("github.com/")[-1].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    elif "github.com:" in cleaned:
        parts = cleaned.split("github.com:")[-1].split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    return None

async def validate_github_repository(url: str) -> Dict[str, Any]:
    """
    Calls the real GitHub API to verify that a repository exists and is accessible.
    """
    parsed = parse_github_url(url)
    if not parsed:
        return {"valid": False, "name": None, "owner": None, "defaultBranch": None}
    
    owner, repo = parsed
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, headers=_get_headers(), timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": True,
                    "name": data.get("name"),
                    "owner": data.get("owner", {}).get("login"),
                    "defaultBranch": data.get("default_branch", "main")
                }
        except httpx.RequestError:
            pass
            
    return {"valid": False, "name": None, "owner": None, "defaultBranch": None}

async def fetch_github_branches(url: str) -> List[Dict[str, Any]]:
    """
    Retrieves all branches for a given repository from the live GitHub API.
    """
    parsed = parse_github_url(url)
    if not parsed:
        return []
        
    owner, repo = parsed
    api_url = f"https://api.github.com/repos/{owner}/{repo}/branches"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, headers=_get_headers(), timeout=10.0)
            if response.status_code == 200:
                branches_data = response.json()
                
                # Fetch default branch to mark it
                repo_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}",
                    headers=_get_headers(),
                    timeout=10.0
                )
                default_branch = "main"
                if repo_response.status_code == 200:
                    default_branch = repo_response.json().get("default_branch", "main")

                return [
                    {
                        "name": branch["name"],
                        "isDefault": branch["name"] == default_branch,
                        "lastCommit": branch.get("commit", {}).get("sha", "")[:7]
                    }
                    for branch in branches_data
                ]
        except httpx.RequestError:
            pass
            
    return []