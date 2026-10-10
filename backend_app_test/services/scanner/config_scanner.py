"""Insecure configuration checks (backlog US-12, FR-04).

Flags committed environment files (critical), enabled debug modes, and
wildcard CORS policies, with a recommendation for each. Evidence for .env
files lists variable names only - values are never read into findings.
"""

import os
import re
from typing import Any, Dict, List

from backend_app_test.services.scanner.base import SecurityCheck

MAX_FILE_BYTES = 1024 * 1024
SKIPPED_DIRECTORIES = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}
ENV_TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".dist", ".defaults", ".tpl")
SOURCE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx"}
CONFIG_SUFFIXES = {".ini", ".cfg", ".toml", ".yaml", ".yml", ".properties", ".conf", ".json"}

_ENV_FILE = re.compile(r"^\.env(?:\.[\w.-]+)?$", re.IGNORECASE)
_ENV_ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
_CREDENTIALS = re.compile(r"(?i)(allow_credentials\s*=\s*True|supports_credentials\s*=\s*True|credentials\s*:\s*true)")
CORS_RECOMMENDATION = (
    "Replace the wildcard with an explicit list of trusted origins, and never "
    "combine a wildcard origin with credentials."
)

# (title, severity, pattern, file suffixes, recommendation, escalate when credentials allowed)
LINE_RULES = [
    (
        "Flask Debug Mode Enabled", "high",
        re.compile(r"\.run\s*\([^)]*\bdebug\s*=\s*True"), {".py"},
        "Remove debug=True; the Werkzeug debugger allows code execution. Control debug mode from an environment variable that is off in production.",
        False,
    ),
    (
        "Debug Mode Enabled (DEBUG=True)", "medium",
        re.compile(r"^\s*DEBUG\s*=\s*True\b"), {".py"},
        "Set DEBUG from the environment and default it to False in production.",
        False,
    ),
    (
        "Debug Flag Enabled in Configuration", "medium",
        re.compile(r"(?i)^\s*\"?(?:flask_|app_|django_)?debug\"?\s*[:=]\s*[\"']?(?:true|1|yes|on)[\"']?\s*,?\s*$"),
        CONFIG_SUFFIXES,
        "Disable debug mode in committed configuration; enable it only in local overrides.",
        False,
    ),
    (
        "Permissive CORS Policy (Wildcard Origin)", "high",
        re.compile(
            r"""(?ix)
            allow_origins\s*=\s*\[\s*["']\*["']\s*\]
            | \borigins\s*=\s*["']\*["']
            | \borigin\s*:\s*(?:["']\*["']|true\b)
            | Access-Control-Allow-Origin["']?\s*[,:]\s*["']\*["']
            | ^\s*CORS_(?:ALLOW_ALL_ORIGINS|ORIGIN_ALLOW_ALL)\s*=\s*True\b
            """
        ),
        SOURCE_SUFFIXES | CONFIG_SUFFIXES,
        CORS_RECOMMENDATION,
        True,
    ),
]


def _finding(title, severity, rel_path, line, snippet, recommendation, description, confidence="high"):
    return {
        "title": title,
        "category": "Insecure Configuration",
        "severity": severity,
        "confidence": confidence,
        "description": description,
        "filePath": rel_path,
        "lineStart": line,
        "lineEnd": line,
        "codeSnippet": snippet[:300],
        "recommendation": recommendation,
    }


def _env_file_finding(path: str, rel_path: str) -> Dict[str, Any] | None:
    if os.path.basename(path).lower().endswith(ENV_TEMPLATE_SUFFIXES):
        return None
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        keys = [m.group(1) for m in map(_ENV_ASSIGNMENT.match, handle.read().splitlines()) if m]
    if not keys:
        return None
    listed = ", ".join(keys[:15]) + (", ..." if len(keys) > 15 else "")
    return _finding(
        "Committed Environment Secrets File",
        "critical",
        rel_path,
        1,
        f"Variables: {listed}",
        "Remove the file from version control, add it to .gitignore, rotate every credential it "
        "contained, and commit a .env.example with placeholder values instead.",
        f"'{rel_path}' is committed to version control and defines {len(keys)} variable(s).",
    )


class ConfigScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "config_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for root, dirs, files in os.walk(repo_path, followlinks=False):
            dirs[:] = [d for d in dirs if d not in SKIPPED_DIRECTORIES]
            for file in files:
                full = os.path.join(root, file)
                if os.path.islink(full):
                    continue
                try:
                    if os.path.getsize(full) > MAX_FILE_BYTES:
                        continue
                except OSError:
                    continue
                rel_path = os.path.relpath(full, repo_path).replace("\\", "/")
                if _ENV_FILE.match(file):
                    finding = _env_file_finding(full, rel_path)
                    if finding:
                        findings.append(finding)
                    continue
                suffix = os.path.splitext(file)[1].lower()
                rules = [rule for rule in LINE_RULES if suffix in rule[3]]
                if not rules:
                    continue
                with open(full, "r", encoding="utf-8", errors="ignore") as handle:
                    lines = handle.read().splitlines()
                for index, line in enumerate(lines):
                    if len(line) > 2000:
                        continue  # minified or generated content
                    for title, severity, pattern, _, recommendation, escalate in rules:
                        if not pattern.search(line):
                            continue
                        description = f"{title} in {rel_path} at line {index + 1}."
                        if escalate and _CREDENTIALS.search("\n".join(lines[max(0, index - 12): index + 12])):
                            severity = "critical"
                            description += " Credentials are also allowed, so any website can make authenticated requests for a signed-in user."
                        findings.append(_finding(title, severity, rel_path, index + 1, line.strip(), recommendation, description))
        return findings
