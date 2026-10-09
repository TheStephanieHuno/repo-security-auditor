"""
Database Session Engine — PostgreSQL 16 (Async)
Uses asyncpg driver for high-performance non-blocking query execution.
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Strict PostgreSQL connection string (Reads from environment or defaults to local Docker PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://auditor:auditor123@localhost:5432/repo_auditor"
)

# SQLAlchemy 2.0 Async PostgreSQL Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Automatically detects and recovers stale connections
)

# Asynchronous Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all PostgreSQL ORM models."""
    pass


async def get_db():
    """FastAPI dependency for injecting transactional PostgreSQL sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise