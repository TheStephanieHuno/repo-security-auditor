"""Convert raw scanner output into ``NormalizedFinding`` objects (SRS NFR-05).

Each ``normalize_*`` function accepts one scanner's native output and returns
findings ready for ``persist_normalized_findings``. Paths are made
repository-relative, secrets are masked before they reach evidence, and
malformed entries raise ``ValueError`` so the scanner run fails visibly
instead of storing partial or unsafe data.
"""

from __future__ import annotations

import math
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

from app.db.models import Confidence, EvidenceType, FindingCategory, Severity
from app.db.normalization import (
    MAX_TEXT_LENGTH,
    NormalizedEvidence,
    NormalizedFinding,
    build_fingerprint,
    map_severity,
    normalize_repository_path,
    redact_sensitive_text,
)

_SEVERITY_TAG = re.compile(r"^severity:(low|medium|high|critical)$", re.IGNORECASE)
_SEMGREP_LOGIN_PLACEHOLDER = "requires login"


def relative_repository_path(raw_path: str | None, workspace: Path) -> str | None:
    """Turn a scanner-reported path into a safe repository-relative path."""
    if raw_path is None or not str(raw_path).strip():
        return None
    candidate = PurePath(str(raw_path))
    if candidate.is_absolute():
        # abspath does not follow symlinks, unlike Path.resolve.
        root = os.path.abspath(workspace)
        target = os.path.abspath(str(candidate))
        try:
            contained = os.path.commonpath(
                [os.path.normcase(root), os.path.normcase(target)]
            ) == os.path.normcase(root)
        except ValueError:  # different drives on Windows
            contained = False
        if not contained:
            raise ValueError("scanner reported a path outside the workspace")
        return normalize_repository_path(os.path.relpath(target, root))
    return normalize_repository_path(str(raw_path))


def _text(value: Any, *, default: str = "", limit: int = MAX_TEXT_LENGTH) -> str:
    text = str(value).strip() if value is not None else ""
    return (text or default)[:limit]


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _line_range(start: Any, end: Any) -> tuple[int | None, int | None]:
    line_start = _positive_int(start)
    line_end = _positive_int(end)
    if line_start is not None and line_end is not None and line_end < line_start:
        line_end = line_start
    if line_start is None:
        line_end = None
    return line_start, line_end


def mask_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    if secret.upper() == "REDACTED":
        return "REDACTED"
    visible = secret[:4] if len(secret) >= 12 else ""
    return f"{visible}{'*' * 8}"


# ---------------------------------------------------------------- Gitleaks


GITLEAKS_RECOMMENDATION = (
    "Revoke and rotate the exposed credential immediately, remove it from the "
    "repository and its history, and load it at runtime from a secret manager "
    "or environment variable."
)


def normalize_gitleaks(entries: Any, workspace: Path) -> list[NormalizedFinding]:
    if not isinstance(entries, list):
        raise ValueError("gitleaks report must be a JSON array")
    findings: list[NormalizedFinding] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("gitleaks report entries must be objects")
        rule_id = _text(entry.get("RuleID"), limit=255)
        if not rule_id:
            raise ValueError("gitleaks entry is missing RuleID")
        file_path = relative_repository_path(entry.get("File"), workspace)
        line_start, line_end = _line_range(entry.get("StartLine"), entry.get("EndLine"))
        raw_severity = next(
            (
                match.group(1)
                for tag in entry.get("Tags") or []
                if isinstance(tag, str) and (match := _SEVERITY_TAG.match(tag))
            ),
            "HIGH",
        )
        severity, _ = map_severity("GITLEAKS", raw_severity)

        secret = entry.get("Secret") if isinstance(entry.get("Secret"), str) else None
        match_text = entry.get("Match") if isinstance(entry.get("Match"), str) else None
        if match_text and secret and secret.upper() != "REDACTED":
            match_text = match_text.replace(secret, mask_secret(secret) or "********")
        description_name = _text(entry.get("Description"), default=rule_id, limit=200)
        location = f"{file_path or 'an unknown file'}" + (
            f" at line {line_start}" if line_start else ""
        )
        findings.append(
            NormalizedFinding(
                category=FindingCategory.SECRET,
                source_scanner="GITLEAKS",
                rule_id=rule_id,
                title=f"Hardcoded secret detected ({description_name})"[:500],
                description=(
                    f"A credential matching the '{description_name}' rule was found in "
                    f"{location}. Anyone with read access to the repository can use it."
                ),
                severity=severity,
                confidence=Confidence.HIGH,
                recommendation=GITLEAKS_RECOMMENDATION,
                fingerprint=build_fingerprint(
                    source_scanner="GITLEAKS",
                    rule_id=rule_id,
                    category=FindingCategory.SECRET,
                    file_path=file_path,
                    line_start=line_start,
                    stable_resource=None,
                    title=description_name,
                ),
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                evidence=(
                    NormalizedEvidence(
                        evidence_type=EvidenceType.SECRET,
                        file_path=file_path,
                        line_start=line_start,
                        line_end=line_end,
                        code_snippet=redact_sensitive_text(match_text),
                        matched_value_redacted=mask_secret(secret),
                        raw_reference=f"gitleaks:{rule_id}",
                    ),
                ),
            )
        )
    return findings


# ----------------------------------------------------------------- Semgrep


SEMGREP_DEFAULT_RECOMMENDATION = (
    "Review the flagged code path and replace the unsafe construct with the "
    "safe alternative described in the rule message."
)


MAX_SNIPPET_LINES = 20


def read_workspace_snippet(
    workspace: Path, relative_path: str | None, line_start: int | None, line_end: int | None
) -> str | None:
    """Read the flagged lines from the workspace (Semgrep returns "requires login" instead).

    Only regular files that resolve inside the workspace are read.
    """
    if not relative_path or line_start is None:
        return None
    root = workspace.resolve()
    candidate = root / relative_path
    try:
        if candidate.is_symlink() or not candidate.is_file():
            return None
        resolved = candidate.resolve()
        if os.path.commonpath([str(root), str(resolved)]) != str(root):
            return None
        last = min(line_end or line_start, line_start + MAX_SNIPPET_LINES - 1)
        with resolved.open(encoding="utf-8", errors="replace") as handle:
            lines = [
                line.rstrip("\r\n")
                for number, line in enumerate(handle, start=1)
                if line_start <= number <= last
            ]
    except (OSError, ValueError):
        return None
    return "\n".join(lines) or None


def _semgrep_rule_id(check_id: str) -> str:
    # Semgrep prefixes local rule IDs with their config path, e.g.
    # "app.scanners.rules.semgrep.rsa-python-eval"; keep the rule's own ID.
    return check_id.rsplit(".", 1)[-1] if "." in check_id else check_id


def normalize_semgrep(report: Any, workspace: Path) -> list[NormalizedFinding]:
    if not isinstance(report, Mapping) or not isinstance(report.get("results"), list):
        raise ValueError("semgrep report must contain a results array")
    findings: list[NormalizedFinding] = []
    for result in report["results"]:
        if not isinstance(result, Mapping):
            raise ValueError("semgrep results must be objects")
        check_id = _text(result.get("check_id"), limit=255)
        if not check_id:
            raise ValueError("semgrep result is missing check_id")
        rule_id = _semgrep_rule_id(check_id)
        extra = result.get("extra") if isinstance(result.get("extra"), Mapping) else {}
        metadata = extra.get("metadata") if isinstance(extra.get("metadata"), Mapping) else {}
        start = result.get("start") if isinstance(result.get("start"), Mapping) else {}
        end = result.get("end") if isinstance(result.get("end"), Mapping) else {}

        file_path = relative_repository_path(result.get("path"), workspace)
        line_start, line_end = _line_range(start.get("line"), end.get("line"))
        severity, _ = map_severity("SEMGREP", extra.get("severity"))
        confidence_value = str(metadata.get("confidence", "MEDIUM")).upper()
        confidence = (
            Confidence(confidence_value)
            if confidence_value in Confidence.__members__
            else Confidence.MEDIUM
        )
        title = _text(
            metadata.get("title"), default=rule_id.replace("-", " ").capitalize(), limit=500
        )
        cwe = metadata.get("cwe")
        cwe_text = ", ".join(cwe) if isinstance(cwe, list) else _text(cwe)
        description = _text(extra.get("message"), default=title)
        if cwe_text:
            description = f"{description} ({cwe_text})"[:MAX_TEXT_LENGTH]
        snippet = extra.get("lines") if isinstance(extra.get("lines"), str) else None
        if not snippet or snippet.strip().lower() == _SEMGREP_LOGIN_PLACEHOLDER:
            snippet = read_workspace_snippet(workspace, file_path, line_start, line_end)

        findings.append(
            NormalizedFinding(
                category=FindingCategory.CODE,
                source_scanner="SEMGREP",
                rule_id=rule_id,
                title=title,
                description=description,
                severity=severity,
                confidence=confidence,
                recommendation=_text(
                    metadata.get("recommendation"), default=SEMGREP_DEFAULT_RECOMMENDATION
                ),
                fingerprint=build_fingerprint(
                    source_scanner="SEMGREP",
                    rule_id=rule_id,
                    category=FindingCategory.CODE,
                    file_path=file_path,
                    line_start=line_start,
                    stable_resource=None,
                    title=title,
                ),
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                evidence=(
                    NormalizedEvidence(
                        evidence_type=EvidenceType.CODE,
                        file_path=file_path,
                        line_start=line_start,
                        line_end=line_end,
                        code_snippet=redact_sensitive_text(snippet),
                        raw_reference=f"semgrep:{rule_id}",
                    ),
                ),
            )
        )
    return findings


# --------------------------------------------------------------------- OSV


@dataclass(frozen=True)
class Dependency:
    ecosystem: str  # OSV ecosystem name, e.g. "PyPI" or "npm"
    name: str
    version: str
    manifest_path: str
    line: int | None = None
    # False when the manifest only gives a range (e.g. "^1.2.3"), so the
    # installed version may differ from the queried lower bound.
    exact: bool = True


_CVSS3_WEIGHTS: dict[str, dict[str, float]] = {
    "AV": {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2},
    "AC": {"L": 0.77, "H": 0.44},
    "UI": {"N": 0.85, "R": 0.62},
    "C": {"H": 0.56, "L": 0.22, "N": 0.0},
    "I": {"H": 0.56, "L": 0.22, "N": 0.0},
    "A": {"H": 0.56, "L": 0.22, "N": 0.0},
}


def _roundup(value: float) -> float:
    integer = round(value * 100000)
    if integer % 10000 == 0:
        return integer / 100000.0
    return (math.floor(integer / 10000) + 1) / 10.0


def cvss3_base_score(vector: str) -> float | None:
    """Compute a CVSS v3.x base score from its vector string."""
    if not vector.startswith(("CVSS:3.0/", "CVSS:3.1/")):
        return None
    metrics = dict(
        part.split(":", 1) for part in vector.split("/")[1:] if ":" in part
    )
    try:
        scope_changed = metrics["S"] == "C"
        privileges = {"N": 0.85, "L": 0.68 if scope_changed else 0.62, "H": 0.5 if scope_changed else 0.27}[
            metrics["PR"]
        ]
        av, ac, ui = (_CVSS3_WEIGHTS[key][metrics[key]] for key in ("AV", "AC", "UI"))
        c, i, a = (_CVSS3_WEIGHTS[key][metrics[key]] for key in ("C", "I", "A"))
    except KeyError:
        return None
    iss = 1 - ((1 - c) * (1 - i) * (1 - a))
    impact = (
        7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if scope_changed else 6.42 * iss
    )
    if impact <= 0:
        return 0.0
    exploitability = 8.22 * av * ac * privileges * ui
    total = impact + exploitability
    return _roundup(min(1.08 * total, 10) if scope_changed else min(total, 10))


def osv_severity(vulnerability: Mapping[str, Any]) -> tuple[Severity, Confidence]:
    database_specific = vulnerability.get("database_specific")
    if isinstance(database_specific, Mapping) and isinstance(
        database_specific.get("severity"), str
    ):
        severity, note = map_severity("OSV", database_specific["severity"])
        return severity, Confidence.HIGH if note is None else Confidence.MEDIUM
    scores = [
        score
        for entry in vulnerability.get("severity") or []
        if isinstance(entry, Mapping) and isinstance(entry.get("score"), str)
        and (score := cvss3_base_score(entry["score"])) is not None
    ]
    if scores:
        score = max(scores)
        if score >= 9.0:
            return Severity.CRITICAL, Confidence.HIGH
        if score >= 7.0:
            return Severity.HIGH, Confidence.HIGH
        if score >= 4.0:
            return Severity.MEDIUM, Confidence.HIGH
        return Severity.LOW, Confidence.HIGH
    return Severity.MEDIUM, Confidence.MEDIUM


def _fixed_versions(vulnerability: Mapping[str, Any], dependency: Dependency) -> list[str]:
    fixed: list[str] = []
    for affected in vulnerability.get("affected") or []:
        if not isinstance(affected, Mapping):
            continue
        package = affected.get("package") if isinstance(affected.get("package"), Mapping) else {}
        if str(package.get("name", "")).lower() != dependency.name.lower():
            continue
        for version_range in affected.get("ranges") or []:
            for event in (version_range or {}).get("events") or []:
                if isinstance(event, Mapping) and isinstance(event.get("fixed"), str):
                    fixed.append(event["fixed"])
    return list(dict.fromkeys(fixed))


def _osv_preference(vulnerability: Mapping[str, Any]) -> int:
    # GHSA advisories carry a severity label; prefer them over PYSEC/OSV aliases.
    return 0 if str(vulnerability.get("id", "")).startswith("GHSA-") else 1


def normalize_osv(
    matches: Iterable[tuple[Dependency, Mapping[str, Any]]],
) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    # The same advisory is often published under several IDs (GHSA, PYSEC, CVE);
    # report it once per dependency.
    seen: dict[Dependency, set[str]] = {}
    ordered = sorted(matches, key=lambda match: _osv_preference(match[1]))
    for dependency, vulnerability in ordered:
        vulnerability_id = _text(vulnerability.get("id"), limit=255)
        if not vulnerability_id:
            raise ValueError("OSV vulnerability is missing an id")
        aliases = [alias for alias in vulnerability.get("aliases") or [] if isinstance(alias, str)]
        known = seen.setdefault(dependency, set())
        if vulnerability_id in known or known.intersection(aliases):
            continue
        known.update([vulnerability_id, *aliases])
        cve = next((alias for alias in aliases if alias.startswith("CVE-")), None)
        summary = _text(vulnerability.get("summary"), default=vulnerability_id, limit=300)
        details = _text(vulnerability.get("details"), default=summary)
        severity, confidence = osv_severity(vulnerability)
        if not dependency.exact:
            confidence = Confidence.LOW if confidence == Confidence.MEDIUM else Confidence.MEDIUM
        fixed = _fixed_versions(vulnerability, dependency)
        recommendation = (
            f"Upgrade {dependency.name} to {fixed[0]} or later."
            if fixed
            else f"No fixed release of {dependency.name} is published; replace the "
            "package or apply the advisory's mitigations."
        )
        manifest = normalize_repository_path(dependency.manifest_path)
        reference = vulnerability_id + (f" ({cve})" if cve and cve != vulnerability_id else "")
        stable_resource = f"{dependency.ecosystem}:{dependency.name}@{dependency.version}"
        findings.append(
            NormalizedFinding(
                category=FindingCategory.DEPENDENCY,
                source_scanner="OSV",
                rule_id=vulnerability_id,
                title=f"{dependency.name} {dependency.version}: {summary}"[:500],
                description=f"{reference}: {details}"[:MAX_TEXT_LENGTH],
                severity=severity,
                confidence=confidence,
                recommendation=recommendation,
                fingerprint=build_fingerprint(
                    source_scanner="OSV",
                    rule_id=vulnerability_id,
                    category=FindingCategory.DEPENDENCY,
                    file_path=manifest,
                    line_start=None,
                    stable_resource=stable_resource,
                    title=vulnerability_id,
                ),
                file_path=manifest,
                line_start=dependency.line,
                line_end=dependency.line,
                evidence=(
                    NormalizedEvidence(
                        evidence_type=EvidenceType.DEPENDENCY,
                        file_path=manifest,
                        line_start=dependency.line,
                        line_end=dependency.line,
                        code_snippet=f"{dependency.name}=={dependency.version}",
                        raw_reference=f"https://osv.dev/vulnerability/{vulnerability_id}",
                    ),
                ),
            )
        )
    return findings


# ------------------------------------------------------------ Config checks


@dataclass(frozen=True)
class ConfigIssue:
    rule_id: str
    title: str
    description: str
    severity: Severity
    recommendation: str
    file_path: str
    line: int | None = None
    snippet: str | None = None
    category: FindingCategory = FindingCategory.CONFIGURATION
    confidence: Confidence = Confidence.MEDIUM


def normalize_config(issues: Iterable[ConfigIssue]) -> list[NormalizedFinding]:
    findings: list[NormalizedFinding] = []
    for issue in issues:
        file_path = normalize_repository_path(issue.file_path)
        evidence_type = (
            EvidenceType.SECRET
            if issue.category == FindingCategory.SECRET
            else EvidenceType.CONFIGURATION
        )
        findings.append(
            NormalizedFinding(
                category=issue.category,
                source_scanner="CONFIG",
                rule_id=issue.rule_id,
                title=issue.title,
                description=issue.description,
                severity=issue.severity,
                confidence=issue.confidence,
                recommendation=issue.recommendation,
                fingerprint=build_fingerprint(
                    source_scanner="CONFIG",
                    rule_id=issue.rule_id,
                    category=issue.category,
                    file_path=file_path,
                    line_start=issue.line,
                    stable_resource=None,
                    title=issue.title,
                ),
                file_path=file_path,
                line_start=issue.line,
                line_end=issue.line,
                evidence=(
                    NormalizedEvidence(
                        evidence_type=evidence_type,
                        file_path=file_path,
                        line_start=issue.line,
                        line_end=issue.line,
                        code_snippet=redact_sensitive_text(issue.snippet),
                        raw_reference=f"config:{issue.rule_id}",
                    ),
                ),
            )
        )
    return findings
