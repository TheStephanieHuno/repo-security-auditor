"""Dependency vulnerability checks against the OSV database (backlog US-11, FR-04).

Parses every requirements*.txt and package.json in the repository (outside
vendor folders), queries https://api.osv.dev/v1/query for each pinned package,
and reports each advisory once per dependency with its real severity, CVE
identifiers, and the fixed version to upgrade to. Only package names and
versions are sent to OSV - never source code.
"""

import asyncio
import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from backend_app_test.services.scanner.base import SecurityCheck

OSV_QUERY_URL = "https://api.osv.dev/v1/query"
MAX_DEPENDENCIES = 500
MAX_CONCURRENT_QUERIES = 8
SKIPPED_DIRECTORIES = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}

_REQUIREMENTS_FILE = re.compile(r"^requirements[\w.-]*\.txt$", re.IGNORECASE)
_PINNED_REQUIREMENT = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*===?\s*([A-Za-z0-9][A-Za-z0-9.+!_-]*)\s*$"
)
_NPM_VERSION = re.compile(r"^[\^~=v]?\s*(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$")
_OSV_SEVERITY = {"LOW": "low", "MODERATE": "medium", "MEDIUM": "medium", "HIGH": "high", "CRITICAL": "critical"}

# (ecosystem, name, version, manifest path, line, exact version?)
Dependency = Tuple[str, str, str, str, Optional[int], bool]


def _requirements(text: str, path: str) -> List[Dependency]:
    deps: List[Dependency] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split(" #", 1)[0].split(";", 1)[0].strip()
        if not line or line.startswith(("#", "-", "git+", "http:", "https:")):
            continue
        match = _PINNED_REQUIREMENT.match(line)
        if match:
            name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
            deps.append(("PyPI", name, match.group(2), path, line_number, True))
    return deps


def _package_json(text: str, path: str) -> List[Dependency]:
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(manifest, dict):
        return []
    lines = text.splitlines()
    deps: List[Dependency] = []
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        for name, spec in (manifest.get(section) or {}).items():
            if not isinstance(spec, str):
                continue
            match = _NPM_VERSION.match(spec.strip())
            if not match:
                continue  # ranges, tags, git/file specs cannot be queried precisely
            line = next((i for i, text_line in enumerate(lines, start=1) if f'"{name}"' in text_line), None)
            exact = spec.strip()[0].isdigit() or spec.strip().startswith("=")
            deps.append(("npm", name, match.group(1), path, line, exact))
    return deps


def discover_dependencies(repo_path: str) -> List[Dependency]:
    deps: List[Dependency] = []
    for root, dirs, files in os.walk(repo_path, followlinks=False):
        dirs[:] = [d for d in dirs if d not in SKIPPED_DIRECTORIES]
        for file in files:
            if file == "package.json":
                parser = _package_json
            elif _REQUIREMENTS_FILE.match(file):
                parser = _requirements
            else:
                continue
            full = os.path.join(root, file)
            if os.path.islink(full):
                continue
            rel = os.path.relpath(full, repo_path).replace("\\", "/")
            with open(full, "r", encoding="utf-8", errors="ignore") as handle:
                deps.extend(parser(handle.read(), rel))
            if len(deps) >= MAX_DEPENDENCIES:
                return deps[:MAX_DEPENDENCIES]
    return deps


def _roundup(value: float) -> float:
    integer = round(value * 100000)
    return integer / 100000.0 if integer % 10000 == 0 else (math.floor(integer / 10000) + 1) / 10.0


def cvss3_base_score(vector: str) -> Optional[float]:
    """CVSS v3.x base score from a vector string (used when no severity label exists)."""
    if not vector.startswith(("CVSS:3.0/", "CVSS:3.1/")):
        return None
    m = dict(part.split(":", 1) for part in vector.split("/")[1:] if ":" in part)
    weights = {
        "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
        "AC": {"L": 0.77, "H": 0.44},
        "UI": {"N": 0.85, "R": 0.62},
        "CIA": {"H": 0.56, "L": 0.22, "N": 0.0},
    }
    try:
        changed = m["S"] == "C"
        pr = {"N": 0.85, "L": 0.68 if changed else 0.62, "H": 0.5 if changed else 0.27}[m["PR"]]
        av, ac, ui = weights["AV"][m["AV"]], weights["AC"][m["AC"]], weights["UI"][m["UI"]]
        c, i, a = (weights["CIA"][m[k]] for k in ("C", "I", "A"))
    except KeyError:
        return None
    iss = 1 - ((1 - c) * (1 - i) * (1 - a))
    impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if changed else 6.42 * iss
    if impact <= 0:
        return 0.0
    total = impact + 8.22 * av * ac * pr * ui
    return _roundup(min(1.08 * total, 10) if changed else min(total, 10))


def osv_severity(vuln: Dict[str, Any]) -> str:
    label = (vuln.get("database_specific") or {}).get("severity")
    if isinstance(label, str) and label.upper() in _OSV_SEVERITY:
        return _OSV_SEVERITY[label.upper()]
    scores = [
        s for s in (cvss3_base_score(e.get("score", "")) for e in vuln.get("severity") or [] if isinstance(e, dict))
        if s is not None
    ]
    if not scores:
        return "medium"
    top = max(scores)
    return "critical" if top >= 9.0 else "high" if top >= 7.0 else "medium" if top >= 4.0 else "low"


def fixed_versions(vuln: Dict[str, Any], name: str) -> List[str]:
    fixed: List[str] = []
    for affected in vuln.get("affected") or []:
        if str((affected.get("package") or {}).get("name", "")).lower() != name.lower():
            continue
        for rng in affected.get("ranges") or []:
            for event in rng.get("events") or []:
                if isinstance(event.get("fixed"), str):
                    fixed.append(event["fixed"])
    return list(dict.fromkeys(fixed))


def to_findings(dep: Dependency, vulns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ecosystem, name, version, path, line, exact = dep
    findings: List[Dict[str, Any]] = []
    seen: set = set()
    # GitHub advisories carry severity labels; prefer them over PYSEC/OSV aliases.
    for vuln in sorted(vulns, key=lambda v: 0 if str(v.get("id", "")).startswith("GHSA-") else 1):
        vid = str(vuln.get("id", "")).strip()
        aliases = [a for a in vuln.get("aliases") or [] if isinstance(a, str)]
        if not vid or vid in seen or seen.intersection(aliases):
            continue
        seen.update([vid, *aliases])
        cves = [a for a in [vid, *aliases] if a.startswith("CVE-")]
        summary = (vuln.get("summary") or vuln.get("details") or vid).strip()
        fixed = fixed_versions(vuln, name)
        reference = vid + (f" ({', '.join(cves)})" if cves and cves[0] != vid else "")
        findings.append({
            "title": f"{name} {version}: {summary}"[:300],
            "category": "Dependency Vulnerability",
            "severity": osv_severity(vuln),
            "confidence": "high" if exact else "medium",
            "description": f"{reference}: {(vuln.get('details') or summary).strip()}"[:1000],
            "filePath": path,
            "lineStart": line,
            "lineEnd": line,
            "codeSnippet": f'"{name}": "{version}"' if ecosystem == "npm" else f"{name}=={version}",
            "recommendation": (
                f"Upgrade {name} to {fixed[0]} or later."
                if fixed
                else f"No fixed release of {name} is published; replace the package or apply the advisory's mitigations."
            ),
        })
    return findings


class DependencyScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "dependency_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        deps = discover_dependencies(repo_path)
        if not deps:
            return []
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_QUERIES)
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "repo-security-auditor"}) as client:

            async def query(dep: Dependency) -> List[Dict[str, Any]]:
                ecosystem, name, version = dep[0], dep[1], dep[2]
                async with semaphore:
                    try:
                        res = await client.post(
                            OSV_QUERY_URL,
                            json={"package": {"name": name, "ecosystem": ecosystem}, "version": version},
                        )
                    except httpx.HTTPError:
                        return []
                if res.status_code != 200:
                    return []
                return to_findings(dep, res.json().get("vulns") or [])

            results = await asyncio.gather(*(query(dep) for dep in deps))
        return [finding for group in results for finding in group]
