import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Repository
from app.db.session import Base

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def run_alembic(database_url: str, *arguments: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.integration
def test_migration_upgrade_downgrade_upgrade(tmp_path: Path) -> None:
    database_path = (tmp_path / "migration.db").resolve()
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"

    run_alembic(database_url, "upgrade", "head")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master "
                "where type = 'table' and name not like 'sqlite_%'"
            )
        }
    assert {
        "users",
        "repositories",
        "scans",
        "scanner_runs",
        "findings",
        "evidence",
        "reports",
        "finding_explanations",
        "alembic_version",
    } <= tables

    run_alembic(database_url, "downgrade", "base")
    with sqlite3.connect(database_path) as connection:
        assert not connection.execute(
            "select 1 from sqlite_master where type = 'table' and name = 'users'"
        ).fetchone()

    run_alembic(database_url, "upgrade", "head")
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("select version_num from alembic_version").fetchone()


@pytest.mark.asyncio
async def test_foreign_key_violation_rolls_back_transaction() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        session.add(
            Repository(
                name="orphan",
                github_url="https://github.com/example/orphan",
                owner_id=999999,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        assert await session.get(Repository, 1) is None

    await engine.dispose()
