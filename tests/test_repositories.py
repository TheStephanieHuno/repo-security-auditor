"""RSA-44 (T-10a, T-10b): repository integration tests and query helpers (SRS FR-02)."""

import pytest
from sqlalchemy import func, select

from app.db.models import Repository, Scan, ScanStatus, User
from app.db.queries import owned_repositories, paginate
from app.db.repositories import (
    DuplicateRepositoryError,
    RepositoryBusyError,
    create_repository,
    delete_repository,
    parse_github_url,
)

# ------------------------------------------------------------ query helpers


def test_github_url_parsing_and_canonical_form() -> None:
    coordinates = parse_github_url("https://GitHub.com/Acme/Web-App.git/")
    assert (coordinates.owner, coordinates.name) == ("Acme", "Web-App")
    assert coordinates.canonical_url == "https://github.com/acme/web-app"
    assert parse_github_url("github.com/acme/web").canonical_url == "https://github.com/acme/web"
    for bad in (
        "https://gitlab.com/acme/web",
        "https://github.com/acme",
        "https://github.com/acme/web/tree/main",
        "https://github.com/../etc",
        "ftp://github.com/acme/web",
        "https://github.com.evil.com/acme/web",
        "https://github.com/-acme/web",
    ):
        with pytest.raises(ValueError):
            parse_github_url(bad)


@pytest.mark.asyncio
async def test_paginate_counts_and_slices(api) -> None:
    async with api.sessions() as db:
        user = User(name="Owner", email="owner@example.com", password_hash="hash")
        db.add(user)
        await db.flush()
        for index in range(7):
            await create_repository(db, owner_id=user.id, url=f"https://github.com/acme/repo{index}")

        first = await paginate(db, owned_repositories(user.id), page=1, page_size=3)
        last = await paginate(db, owned_repositories(user.id), page=3, page_size=3)
        beyond = await paginate(db, owned_repositories(user.id), page=9, page_size=3)

        assert (first.total, first.total_pages, len(first.items)) == (7, 3, 3)
        assert len(last.items) == 1
        assert beyond.items == [] and beyond.total == 7
        names = [r.name for r in first.items + (await paginate(db, owned_repositories(user.id), page=2, page_size=3)).items + last.items]
        assert len(set(names)) == 7  # pages do not overlap
        with pytest.raises(ValueError):
            await paginate(db, owned_repositories(user.id), page=0)
        with pytest.raises(ValueError):
            await paginate(db, owned_repositories(user.id), page_size=101)


@pytest.mark.asyncio
async def test_create_repository_rejects_canonical_duplicates_per_owner(api) -> None:
    async with api.sessions() as db:
        first = User(name="A", email="a@example.com", password_hash="hash")
        second = User(name="B", email="b@example.com", password_hash="hash")
        db.add_all([first, second])
        await db.flush()
        await create_repository(db, owner_id=first.id, url="https://github.com/acme/web")
        with pytest.raises(DuplicateRepositoryError):
            await create_repository(db, owner_id=first.id, url="https://github.com/ACME/web.git")
        # A different user may add the same repository.
        await create_repository(db, owner_id=second.id, url="https://github.com/acme/web")
        assert await db.scalar(select(func.count(Repository.id))) == 2


@pytest.mark.asyncio
async def test_delete_repository_cascades_and_refuses_while_scanning(api) -> None:
    async with api.sessions() as db:
        user = User(name="A", email="a@example.com", password_hash="hash")
        db.add(user)
        await db.flush()
        repository = await create_repository(db, owner_id=user.id, url="https://github.com/acme/web")
        scan = Scan(repository_id=repository.id, requested_by=user.id, target_branch="main",
                    status=ScanStatus.RUNNING.value)
        db.add(scan)
        await db.flush()
        with pytest.raises(RepositoryBusyError):
            await delete_repository(db, repository=repository)
        scan.status = ScanStatus.COMPLETED.value
        await db.flush()
        await delete_repository(db, repository=repository)
        await db.commit()
        assert await db.scalar(select(func.count(Scan.id))) == 0


# -------------------------------------------------------- API integration


@pytest.mark.asyncio
async def test_add_repository_validates_against_github(api) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers, "https://github.com/Acme/Web.git")
    assert repository["url"] == "https://github.com/acme/web"
    assert repository["owner"] == "acme"
    assert repository["isValid"] is True
    assert repository["defaultBranch"] == "main"

    api.github.missing.add("acme/ghost")
    missing = await api.client.post(
        "/api/repositories", json={"url": "https://github.com/acme/ghost"}, headers=headers
    )
    assert missing.status_code == 422
    api.github.private.add("acme/secret")
    private = await api.client.post(
        "/api/repositories", json={"url": "https://github.com/acme/secret"}, headers=headers
    )
    assert private.status_code == 422

    invalid = await api.client.post(
        "/api/repositories", json={"url": "https://evil.example.com/acme/web"}, headers=headers
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_REPOSITORY_URL"


@pytest.mark.asyncio
async def test_duplicate_repository_returns_conflict(api) -> None:
    headers = await api.register("ada@example.com")
    await api.add_repository(headers, "https://github.com/acme/web")
    duplicate = await api.client.post(
        "/api/repositories", json={"url": "https://GITHUB.com/acme/WEB/"}, headers=headers
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "REPOSITORY_EXISTS"


@pytest.mark.asyncio
async def test_list_get_and_delete_repository(api) -> None:
    headers = await api.register("ada@example.com")
    for name in ("one", "two", "three"):
        await api.add_repository(headers, f"https://github.com/acme/{name}")

    page = await api.client.get("/api/repositories?page=1&pageSize=2", headers=headers)
    body = page.json()
    assert len(body["data"]) == 2
    assert body["pagination"] == {"page": 1, "pageSize": 2, "totalItems": 3, "totalPages": 2}

    repository_id = body["data"][0]["id"]
    assert (await api.client.get(f"/api/repositories/{repository_id}", headers=headers)).status_code == 200
    assert (await api.client.delete(f"/api/repositories/{repository_id}", headers=headers)).status_code == 204
    assert (await api.client.get(f"/api/repositories/{repository_id}", headers=headers)).status_code == 404
    assert (await api.client.delete(f"/api/repositories/{repository_id}", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_repository_with_active_scan_cannot_be_deleted(api) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    await api.start_scan(headers, repository["id"])
    response = await api.client.delete(f"/api/repositories/{repository['id']}", headers=headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_repositories_are_isolated_between_users(api) -> None:
    owner = await api.register("owner@example.com")
    other = await api.register("other@example.com")
    repository = await api.add_repository(owner)

    assert (await api.client.get("/api/repositories", headers=other)).json()["data"] == []
    for method, path in (
        ("GET", f"/api/repositories/{repository['id']}"),
        ("DELETE", f"/api/repositories/{repository['id']}"),
        ("GET", f"/api/repositories/{repository['id']}/branches"),
    ):
        response = await api.client.request(method, path, headers=other)
        assert response.status_code == 404, path
    # Still present for its owner.
    assert (await api.client.get(f"/api/repositories/{repository['id']}", headers=owner)).status_code == 200


@pytest.mark.asyncio
async def test_branches_and_validate_endpoints(api) -> None:
    headers = await api.register("ada@example.com")
    repository = await api.add_repository(headers)
    branches = (await api.client.get(f"/api/repositories/{repository['id']}/branches", headers=headers)).json()
    assert [b["name"] for b in branches["data"]] == ["main", "develop"]
    assert branches["data"][0]["isDefault"] is True

    valid = await api.client.post("/api/repositories/validate", json={"url": "https://github.com/a/b"}, headers=headers)
    assert valid.json()["data"]["valid"] is True
    api.github.missing.add("a/missing")
    invalid = await api.client.post(
        "/api/repositories/validate", json={"url": "https://github.com/a/missing"}, headers=headers
    )
    assert invalid.json()["data"] == {"valid": False, "name": None, "owner": None, "defaultBranch": None}
