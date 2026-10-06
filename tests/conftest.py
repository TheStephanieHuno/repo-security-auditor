import os

# Must be set before app modules are imported.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("AUTO_MIGRATE", "0")
os.environ.setdefault("AI_EXPLANATIONS_ENABLED", "0")

from collections.abc import AsyncGenerator  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.rate_limit import login_failures  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.db.session import enable_sqlite_foreign_keys, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.reports import get_ai_service  # noqa: E402
from app.services.github import (  # noqa: E402
    GitHubBranch,
    GitHubRepository,
    get_github_client,
)
from app.services.scan_runner import get_scan_dispatcher  # noqa: E402


class FakeGitHub:
    """Every github.com/<owner>/<name> exists and is public unless listed as missing/private."""

    def __init__(self) -> None:
        self.missing: set[str] = set()
        self.private: set[str] = set()

    async def get_repository(self, owner: str, name: str) -> GitHubRepository | None:
        key = f"{owner}/{name}".lower()
        if key in self.missing:
            return None
        return GitHubRepository(
            owner=owner, name=name, default_branch="main", private=key in self.private, language="Python"
        )

    async def list_branches(self, owner: str, name: str, *, limit: int = 100) -> list[GitHubBranch]:
        return [GitHubBranch("main", "7f3b4c1aa"), GitHubBranch("develop", "a1b2c3d44")]


@dataclass
class RecordingDispatcher:
    dispatched: list[int] = field(default_factory=list)

    def dispatch(self, scan_id: int) -> None:
        self.dispatched.append(scan_id)


@dataclass
class APIHarness:
    client: httpx.AsyncClient
    sessions: async_sessionmaker[AsyncSession]
    github: FakeGitHub
    dispatcher: RecordingDispatcher

    async def register(self, email: str, password: str = "correct-horse-battery", name: str = "User") -> dict:
        response = await self.client.post(
            "/api/auth/register", json={"name": name, "email": email, "password": password}
        )
        assert response.status_code == 201, response.text
        token = response.json()["data"]["token"]
        return {"Authorization": f"Bearer {token}"}

    async def add_repository(self, headers: dict, url: str = "https://github.com/acme/web") -> dict:
        response = await self.client.post("/api/repositories", json={"url": url}, headers=headers)
        assert response.status_code == 201, response.text
        return response.json()["data"]

    async def start_scan(self, headers: dict, repository_id: str, branch: str = "main") -> dict:
        response = await self.client.post(
            "/api/scans", json={"repositoryId": repository_id, "branch": branch}, headers=headers
        )
        assert response.status_code == 201, response.text
        return response.json()["data"]


@pytest_asyncio.fixture
async def api() -> AsyncGenerator[APIHarness, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    enable_sqlite_foreign_keys(engine.sync_engine)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    github = FakeGitHub()
    dispatcher = RecordingDispatcher()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_github_client] = lambda: github
    app.dependency_overrides[get_scan_dispatcher] = lambda: dispatcher
    app.dependency_overrides[get_ai_service] = lambda: None
    login_failures._attempts.clear()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        yield APIHarness(client=client, sessions=sessions, github=github, dispatcher=dispatcher)
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
