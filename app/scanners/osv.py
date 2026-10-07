"""Dependency vulnerability scanner backed by the OSV API (SRS FR-04, T-19, O-09).

Parses ``requirements*.txt`` and ``package.json`` manifests, queries
https://api.osv.dev for known vulnerabilities, and normalizes each match.
Only dependency names and versions leave the worker; no source code does.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping
from urllib.parse import quote
from pathlib import Path
from typing import Any, ClassVar

import httpx

from app.db.models import ScannerName
from app.db.normalization import NormalizedFinding
from app.scanners.base import CheckError, SecurityCheck, iter_workspace_files
from app.scanners.normalizer import Dependency, normalize_osv

OSV_API_URL = "https://api.osv.dev/v1"
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_DEPENDENCIES = 2_000
MAX_VULNERABILITY_DETAILS = 300
QUERY_BATCH_SIZE = 500

_REQUIREMENTS_FILE = re.compile(r"^requirements[\w.-]*\.txt$", re.IGNORECASE)
_PINNED_REQUIREMENT = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*===?\s*([A-Za-z0-9][A-Za-z0-9.+!_-]*)\s*$"
)
_VULNERABILITY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_NPM_VERSION = re.compile(r"^[\^~=v]?\s*(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)$")


def _normalize_pypi_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(text: str, manifest_path: str) -> list[Dependency]:
    """Extract exactly pinned (``==``) requirements; ranges cannot be queried precisely."""
    dependencies: list[Dependency] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split(" #", 1)[0].split(";", 1)[0].strip()
        if not line or line.startswith(("#", "-", "git+", "http:", "https:")):
            continue
        match = _PINNED_REQUIREMENT.match(line)
        if match:
            dependencies.append(
                Dependency(
                    ecosystem="PyPI",
                    name=_normalize_pypi_name(match.group(1)),
                    version=match.group(2),
                    manifest_path=manifest_path,
                    line=line_number,
                )
            )
    return dependencies


def parse_package_json(text: str, manifest_path: str) -> list[Dependency]:
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(manifest, Mapping):
        return []
    lines = text.splitlines()
    dependencies: list[Dependency] = []
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        entries = manifest.get(section)
        if not isinstance(entries, Mapping):
            continue
        for name, spec in entries.items():
            if not isinstance(name, str) or not isinstance(spec, str):
                continue
            match = _NPM_VERSION.match(spec.strip())
            if not match:
                continue  # ranges, tags, git/file/workspace specs
            quoted = f'"{name}"'
            line = next(
                (index for index, text_line in enumerate(lines, start=1) if quoted in text_line),
                None,
            )
            dependencies.append(
                Dependency(
                    ecosystem="npm",
                    name=name,
                    version=match.group(1),
                    manifest_path=manifest_path,
                    line=line,
                    exact=spec.strip()[0].isdigit() or spec.strip().startswith("="),
                )
            )
    return dependencies


def discover_dependencies(workspace: Path) -> list[Dependency]:
    root = workspace.resolve()
    dependencies: list[Dependency] = []
    for path in iter_workspace_files(root, max_file_bytes=MAX_MANIFEST_BYTES):
        if path.name == "package.json":
            parser = parse_package_json
        elif _REQUIREMENTS_FILE.match(path.name):
            parser = parse_requirements
        else:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        dependencies.extend(parser(text, path.relative_to(root).as_posix()))
        if len(dependencies) >= MAX_DEPENDENCIES:
            return dependencies[:MAX_DEPENDENCIES]
    return dependencies


class OsvCheck(SecurityCheck):
    name: ClassVar[ScannerName] = ScannerName.OSV
    timeout_seconds: ClassVar[float] = 120.0

    def __init__(
        self,
        *,
        api_url: str = OSV_API_URL,
        transport: httpx.AsyncBaseTransport | None = None,
        request_timeout_seconds: float = 20.0,
        max_concurrency: int = 8,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.transport = transport
        self.request_timeout_seconds = request_timeout_seconds
        self.max_concurrency = max_concurrency

    async def _post(self, client: httpx.AsyncClient, path: str, payload: dict[str, Any]) -> Any:
        return await self._request(client, "POST", path, json=payload)

    async def _request(
        self, client: httpx.AsyncClient, method: str, path: str, **kwargs: Any
    ) -> Any:
        last_error = "no response"
        for attempt in range(2):
            try:
                response = await client.request(method, f"{self.api_url}{path}", **kwargs)
            except httpx.HTTPError as error:
                last_error = type(error).__name__
            else:
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError:
                        raise CheckError("OSV API returned malformed JSON") from None
                if response.status_code < 500:
                    raise CheckError(f"OSV API rejected the request (HTTP {response.status_code})")
                last_error = f"HTTP {response.status_code}"
            if attempt == 0:
                await asyncio.sleep(0.5)
        raise CheckError(f"OSV API unavailable ({last_error})")

    async def _vulnerability_ids(
        self, client: httpx.AsyncClient, dependencies: list[Dependency]
    ) -> list[list[str]]:
        ids: list[list[str]] = []
        for start in range(0, len(dependencies), QUERY_BATCH_SIZE):
            batch = dependencies[start : start + QUERY_BATCH_SIZE]
            payload = {
                "queries": [
                    {
                        "package": {"name": dependency.name, "ecosystem": dependency.ecosystem},
                        "version": dependency.version,
                    }
                    for dependency in batch
                ]
            }
            response = await self._post(client, "/querybatch", payload)
            results = response.get("results") if isinstance(response, Mapping) else None
            if not isinstance(results, list) or len(results) != len(batch):
                raise CheckError("OSV API returned an unexpected batch response")
            for result in results:
                vulns = result.get("vulns") if isinstance(result, Mapping) else None
                ids.append(
                    [
                        vuln["id"]
                        for vuln in vulns or []
                        if isinstance(vuln, Mapping)
                        and isinstance(vuln.get("id"), str)
                        and _VULNERABILITY_ID.match(vuln["id"])
                    ]
                )
        return ids

    async def scan(self, workspace: Path) -> list[NormalizedFinding]:
        dependencies = discover_dependencies(workspace)
        if not dependencies:
            return []
        async with httpx.AsyncClient(
            transport=self.transport,
            timeout=self.request_timeout_seconds,
            headers={"User-Agent": "repo-security-auditor"},
        ) as client:
            ids_per_dependency = await self._vulnerability_ids(client, dependencies)
            unique_ids = list(dict.fromkeys(i for ids in ids_per_dependency for i in ids))
            if len(unique_ids) > MAX_VULNERABILITY_DETAILS:
                unique_ids = unique_ids[:MAX_VULNERABILITY_DETAILS]

            semaphore = asyncio.Semaphore(self.max_concurrency)

            async def fetch(vulnerability_id: str) -> tuple[str, Any]:
                async with semaphore:
                    detail = await self._request(
                        client, "GET", f"/vulns/{quote(vulnerability_id, safe='')}"
                    )
                    return vulnerability_id, detail

            details = dict(await asyncio.gather(*(fetch(i) for i in unique_ids)))

        matches = [
            (dependency, details[vulnerability_id])
            for dependency, ids in zip(dependencies, ids_per_dependency, strict=True)
            for vulnerability_id in ids
            if isinstance(details.get(vulnerability_id), Mapping)
        ]
        try:
            return normalize_osv(matches)
        except ValueError as error:
            raise CheckError(f"OSV response rejected: {error}") from None
