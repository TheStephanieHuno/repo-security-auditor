"""Static insecure-configuration checks (SRS FR-04, ticket T-20).

Detects committed environment files, enabled debug modes, and overly
permissive CORS policies. Pure Python: no subprocess and no network.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from app.db.models import Confidence, ScannerName, Severity
from app.db.normalization import NormalizedFinding
from app.scanners.base import SecurityCheck, iter_workspace_files
from app.scanners.normalizer import ConfigIssue, normalize_config

MAX_CONFIG_FILE_BYTES = 1024 * 1024
CREDENTIAL_WINDOW_LINES = 12

_ENV_FILE = re.compile(r"^\.env(?:\.[\w.-]+)?$", re.IGNORECASE)
_ENV_TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".dist", ".defaults", ".tpl")
_ENV_ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
_SENSITIVE_KEY = re.compile(r"(?i)(secret|token|passw|pwd|api_?key|private|credential|auth)")

SOURCE_SUFFIXES = frozenset({".py", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx"})
CONFIG_SUFFIXES = frozenset(
    {".ini", ".cfg", ".toml", ".yaml", ".yml", ".properties", ".conf", ".json"}
)

_CREDENTIALS_ENABLED = re.compile(
    r"(?i)(allow_credentials\s*=\s*True|supports_credentials\s*=\s*True|credentials\s*:\s*true)"
)


@dataclass(frozen=True)
class LineRule:
    rule_id: str
    title: str
    description: str
    severity: Severity
    recommendation: str
    pattern: re.Pattern[str]
    suffixes: frozenset[str]
    # Raise to HIGH when credentials are also allowed near the match.
    escalate_with_credentials: bool = False
    confidence: Confidence = Confidence.MEDIUM


_CORS_RECOMMENDATION = (
    "Replace the wildcard with an explicit allowlist of trusted origins, and "
    "never combine a wildcard or reflected origin with credentials."
)

LINE_RULES: tuple[LineRule, ...] = (
    LineRule(
        rule_id="rsa-config-flask-debug",
        title="Flask debug mode enabled",
        description=(
            "The application is started with debug=True. The Werkzeug debugger "
            "allows arbitrary code execution from the browser if it is reachable."
        ),
        severity=Severity.HIGH,
        recommendation="Remove debug=True and control debug mode from an environment variable that is off in production.",
        pattern=re.compile(r"\.run\s*\([^)]*\bdebug\s*=\s*True"),
        suffixes=frozenset({".py"}),
        confidence=Confidence.HIGH,
    ),
    LineRule(
        rule_id="rsa-config-django-debug",
        title="Django DEBUG setting enabled",
        description=(
            "DEBUG = True exposes stack traces, settings, and SQL queries to "
            "anyone who triggers an error."
        ),
        severity=Severity.MEDIUM,
        recommendation="Set DEBUG from the environment and default it to False.",
        pattern=re.compile(r"^\s*DEBUG\s*=\s*True\b"),
        suffixes=frozenset({".py"}),
    ),
    LineRule(
        rule_id="rsa-config-debug-flag",
        title="Debug flag enabled in configuration",
        description="A configuration file enables debug mode, which commonly leaks internals in error responses.",
        severity=Severity.MEDIUM,
        recommendation="Disable debug mode in committed configuration and enable it only in local overrides.",
        pattern=re.compile(
            r"(?i)^\s*\"?(?:flask_|app_|django_)?debug\"?\s*[:=]\s*[\"']?(?:true|1|yes|on)[\"']?\s*,?\s*$"
        ),
        suffixes=CONFIG_SUFFIXES,
    ),
    LineRule(
        rule_id="rsa-config-cors-wildcard",
        title="CORS allows any origin",
        description="The CORS policy accepts requests from any origin.",
        severity=Severity.MEDIUM,
        recommendation=_CORS_RECOMMENDATION,
        pattern=re.compile(
            r"""(?ix)
            allow_origins\s*=\s*\[\s*["']\*["']\s*\]        # FastAPI / Starlette
            | \borigins\s*=\s*["']\*["']                     # Flask-CORS
            | \borigin\s*:\s*(?:["']\*["']|true\b)            # Node cors({origin})
            | Access-Control-Allow-Origin["']?\s*[,:]\s*["']\*["']
            """
        ),
        suffixes=SOURCE_SUFFIXES | CONFIG_SUFFIXES,
        escalate_with_credentials=True,
    ),
    LineRule(
        rule_id="rsa-config-cors-allow-all",
        title="CORS allows any origin",
        description="Django CORS is configured to accept requests from any origin.",
        severity=Severity.MEDIUM,
        recommendation=_CORS_RECOMMENDATION,
        pattern=re.compile(r"^\s*CORS_(?:ALLOW_ALL_ORIGINS|ORIGIN_ALLOW_ALL)\s*=\s*True\b"),
        suffixes=frozenset({".py"}),
        escalate_with_credentials=True,
    ),
    LineRule(
        rule_id="rsa-config-cors-default",
        title="CORS middleware enabled with default (any-origin) policy",
        description="The CORS middleware is used without options, which allows every origin.",
        severity=Severity.LOW,
        recommendation=_CORS_RECOMMENDATION,
        pattern=re.compile(r"(?:\bcors\(\s*\)|\bCORS\(\s*app\s*\))"),
        suffixes=SOURCE_SUFFIXES,
    ),
)


def _check_env_file(path: Path, relative: str) -> ConfigIssue | None:
    lowered = path.name.lower()
    if lowered.endswith(_ENV_TEMPLATE_SUFFIXES):
        return None
    keys: list[str] = []
    sensitive_with_value = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _ENV_ASSIGNMENT.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip().strip("'\"")
        keys.append(key)
        if value and _SENSITIVE_KEY.search(key):
            sensitive_with_value = True
    if not keys:
        return None
    listed = ", ".join(keys[:15]) + (", ..." if len(keys) > 15 else "")
    return ConfigIssue(
        rule_id="rsa-config-committed-env-file",
        title=f"Environment file committed to the repository ({path.name})",
        description=(
            f"{relative} is tracked in the repository and defines {len(keys)} "
            "variable(s)"
            + (", including credential-like values." if sensitive_with_value else ".")
        ),
        severity=Severity.HIGH if sensitive_with_value else Severity.MEDIUM,
        recommendation=(
            "Remove the file from version control, add it to .gitignore, rotate any "
            "credentials it contained, and commit a .env.example with placeholder values instead."
        ),
        file_path=relative,
        line=None,
        # Only variable names are kept as evidence; values are never read into findings.
        snippet=f"Variables: {listed}",
        confidence=Confidence.HIGH,
    )


def scan_configuration(workspace: Path) -> list[ConfigIssue]:
    root = workspace.resolve()
    issues: list[ConfigIssue] = []
    for path in iter_workspace_files(root, max_file_bytes=MAX_CONFIG_FILE_BYTES):
        relative = path.relative_to(root).as_posix()
        if _ENV_FILE.match(path.name):
            issue = _check_env_file(path, relative)
            if issue:
                issues.append(issue)
            continue
        suffix = path.suffix.lower()
        rules = [rule for rule in LINE_RULES if suffix in rule.suffixes]
        if not rules:
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines):
            if len(line) > 2000:
                continue  # minified or generated content
            for rule in rules:
                if not rule.pattern.search(line):
                    continue
                severity = rule.severity
                description = rule.description
                if rule.escalate_with_credentials:
                    window = "\n".join(
                        lines[max(0, index - CREDENTIAL_WINDOW_LINES) : index + CREDENTIAL_WINDOW_LINES]
                    )
                    if _CREDENTIALS_ENABLED.search(window):
                        severity = Severity.HIGH
                        description += (
                            " Credentials are also allowed, so any website can make "
                            "authenticated requests on behalf of a signed-in user."
                        )
                issues.append(
                    ConfigIssue(
                        rule_id=rule.rule_id,
                        title=rule.title,
                        description=description,
                        severity=severity,
                        recommendation=rule.recommendation,
                        file_path=relative,
                        line=index + 1,
                        snippet=line.strip()[:300],
                        confidence=rule.confidence,
                    )
                )
    return issues


class ConfigCheck(SecurityCheck):
    name: ClassVar[ScannerName] = ScannerName.CONFIG
    timeout_seconds: ClassVar[float] = 60.0

    async def scan(self, workspace: Path) -> list[NormalizedFinding]:
        issues = await asyncio.to_thread(scan_configuration, workspace)
        return normalize_config(issues)
