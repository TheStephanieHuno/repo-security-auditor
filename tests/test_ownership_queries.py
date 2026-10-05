from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Repository, User
from app.db.queries import get_owned_repository, list_owned_repositories


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_user_cannot_read_another_users_repository(db: AsyncSession) -> None:
    user_a = User(name="User A", email="a@example.com", password_hash="hash-a")
    user_b = User(name="User B", email="b@example.com", password_hash="hash-b")
    db.add_all([user_a, user_b])
    await db.flush()

    repository_a = Repository(
        name="repo-a",
        github_url="https://github.com/example/repo-a",
        owner_id=user_a.id,
    )
    repository_b = Repository(
        name="repo-b",
        github_url="https://github.com/example/repo-b",
        owner_id=user_b.id,
    )
    db.add_all([repository_a, repository_b])
    await db.commit()

    assert await get_owned_repository(
        db, user_id=user_a.id, repository_id=repository_a.id
    ) is not None
    assert await get_owned_repository(
        db, user_id=user_a.id, repository_id=repository_b.id
    ) is None


@pytest.mark.asyncio
async def test_list_owned_repositories_is_scoped_to_user(db: AsyncSession) -> None:
    user_a = User(name="User A", email="a@example.com", password_hash="hash-a")
    user_b = User(name="User B", email="b@example.com", password_hash="hash-b")
    db.add_all([user_a, user_b])
    await db.flush()
    db.add_all(
        [
            Repository(
                name="repo-a",
                github_url="https://github.com/example/repo-a",
                owner_id=user_a.id,
            ),
            Repository(
                name="repo-b",
                github_url="https://github.com/example/repo-b",
                owner_id=user_b.id,
            ),
        ]
    )
    await db.commit()

    repositories = await list_owned_repositories(db, user_id=user_a.id)

    assert [repository.name for repository in repositories] == ["repo-a"]
