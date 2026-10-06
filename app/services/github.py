"""GitHub REST API client used to validate repositories (SRS FR-03)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote

import httpx

GITHUB_API_URL = "https://api.github.com"


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    name: str
    default_branch: str
    private: bool
    language: str | None


@dataclass(frozen=True)
class GitHubBranch:
    name: str
    sha: str | None


class GitHubUnavailableError(Exception):
    pass


class GitHubClient:
    def __init__(
        self,
        *,
        token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN")
        self.transport = transport
        self.timeout_seconds = timeout_seconds

    def _client(self) -> httpx.AsyncClient:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "repo-security-auditor",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return httpx.AsyncClient(
            base_url=GITHUB_API_URL,
            headers=headers,
            timeout=self.timeout_seconds,
            transport=self.transport,
        )

    async def _get(self, path: str, **params: object) -> httpx.Response:
        try:
            async with self._client() as client:
                response = await client.get(path, params=params or None)
        except httpx.HTTPError:
            raise GitHubUnavailableError("GitHub could not be reached") from None
        if response.status_code in {403, 429} and response.headers.get("x-ratelimit-remaining") == "0":
            raise GitHubUnavailableError("GitHub API rate limit reached")
        if response.status_code >= 500:
            raise GitHubUnavailableError(f"GitHub returned HTTP {response.status_code}")
        return response

    async def get_repository(self, owner: str, name: str) -> GitHubRepository | None:
        response = await self._get(f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}")
        if response.status_code != 200:
            return None  # 404 for missing repositories and private repositories alike
        data = response.json()
        return GitHubRepository(
            owner=data["owner"]["login"],
            name=data["name"],
            default_branch=data.get("default_branch") or "main",
            private=bool(data.get("private")),
            language=data.get("language"),
        )

    async def list_branches(self, owner: str, name: str, *, limit: int = 100) -> list[GitHubBranch]:
        response = await self._get(
            f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}/branches", per_page=min(limit, 100)
        )
        if response.status_code != 200:
            return []
        return [
            GitHubBranch(name=item["name"], sha=(item.get("commit") or {}).get("sha"))
            for item in response.json()
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]


def get_github_client() -> GitHubClient:
    """FastAPI dependency; tests override it with a fake."""
    return GitHubClient()
