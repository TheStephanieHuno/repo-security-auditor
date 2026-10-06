"""Repository persistence: canonical URLs, duplicate handling, and deletion."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Repository, Scan, ScanStatus, utcnow

_GITHUB_URL = re.compile(
    r"^\s*(?:https?://)?(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<name>[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?\s*$",
    re.IGNORECASE,
)


class DuplicateRepositoryError(Exception):
    pass


class RepositoryBusyError(Exception):
    pass


@dataclass(frozen=True)
class GitHubCoordinates:
    owner: str
    name: str

    @property
    def canonical_url(self) -> str:
        # GitHub owner and repository names are case-insensitive.
        return f"https://github.com/{self.owner.lower()}/{self.name.lower()}"


def parse_github_url(url: str) -> GitHubCoordinates:
    match = _GITHUB_URL.fullmatch(url)
    if not match or match.group("name") in {".", ".."}:
        raise ValueError("URL must be a GitHub repository such as https://github.com/owner/name")
    return GitHubCoordinates(owner=match.group("owner"), name=match.group("name"))


async def create_repository(
    db: AsyncSession,
    *,
    owner_id: int,
    url: str,
    name: str | None = None,
    default_branch: str | None = None,
    language: str | None = None,
    is_private: bool = False,
    validated: bool = False,
) -> Repository:
    """Add a repository for a user, rejecting duplicates of the canonical URL."""
    coordinates = parse_github_url(url)
    canonical = coordinates.canonical_url
    duplicate = await db.scalar(
        select(exists().where(Repository.owner_id == owner_id, Repository.github_url == canonical))
    )
    if duplicate:
        raise DuplicateRepositoryError(canonical)
    repository = Repository(
        owner_id=owner_id,
        github_url=canonical,
        name=(name or coordinates.name)[:255],
        default_branch=default_branch,
        language=language,
        is_private=is_private,
        last_validated_at=utcnow() if validated else None,
    )
    try:
        # The unique constraint is the final guard against a concurrent insert.
        async with db.begin_nested():
            db.add(repository)
            await db.flush()
    except IntegrityError:
        raise DuplicateRepositoryError(canonical) from None
    return repository


async def delete_repository(db: AsyncSession, *, repository: Repository) -> None:
    """Delete a repository and, by cascade, its scans and results.

    Refused while a scan is queued or running, because the worker would lose
    the rows it is writing to.
    """
    active = await db.scalar(
        select(
            exists().where(
                Scan.repository_id == repository.id,
                Scan.status.in_([ScanStatus.QUEUED.value, ScanStatus.RUNNING.value]),
            )
        )
    )
    if active:
        raise RepositoryBusyError(repository.github_url)
    await db.delete(repository)
    await db.flush()
