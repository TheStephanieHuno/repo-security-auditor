"""Source code vulnerability analysis with Semgrep (backlog US-10, FR-04).

Runs the project's own rules (rules/semgrep, validated with `semgrep --test`)
plus the OWASP Top 10 registry pack. Metrics are off, and the scanned
repository cannot silence findings (nosemgrep comments, .semgrepignore,
.gitignore). If the registry is unreachable the local rules still run.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from backend_app_test.services.scanner.base import SecurityCheck

logger = logging.getLogger(__name__)

LOCAL_RULES = os.path.join(os.path.dirname(__file__), "rules", "semgrep")
REGISTRY_PACKS = ["p/owasp-top-ten"]
SEMGREP_TIMEOUT_SECONDS = 55
SEVERITY_MAP = {"ERROR": "critical", "WARNING": "high", "INFO": "medium"}


def _command(semgrep_bin: str, configs: List[str], repo_path: str) -> List[str]:
    command = [semgrep_bin, "scan"]
    for config in configs:
        command += ["--config", config]
    return command + [
        "--json",
        "--quiet",
        "--metrics=off",
        "--disable-version-check",
        "--disable-nosem",
        "--no-git-ignore",
        "--x-ignore-semgrepignore-files",
        "--timeout", "20",
        "--max-target-bytes", "1000000",
        repo_path,
    ]


def _run(command: List[str]) -> Optional[Dict[str, Any]]:
    env = {**os.environ, "SEMGREP_SEND_METRICS": "off", "PYTHONUTF8": "1"}
    res = subprocess.run(command, capture_output=True, text=True, timeout=SEMGREP_TIMEOUT_SECONDS, env=env)
    if not res.stdout:
        return None
    try:
        result = json.loads(res.stdout)
    except json.JSONDecodeError:
        return None
    # Semgrep exits non-zero for fatal errors such as an unreachable registry.
    if res.returncode not in (0, 1) and not result.get("results"):
        return None
    return result


def _snippet(repo_path: str, match: Dict[str, Any]) -> str:
    lines = match.get("extra", {}).get("lines", "") or ""
    if lines.strip() and lines.strip().lower() != "requires login":
        return lines.strip()[:200]
    # Semgrep without a login returns "requires login"; read the lines ourselves.
    path = os.path.join(repo_path, os.path.relpath(match.get("path", ""), repo_path))
    start = match.get("start", {}).get("line", 1)
    end = min(match.get("end", {}).get("line", start), start + 19)
    try:
        if os.path.islink(path) or not os.path.realpath(path).startswith(os.path.realpath(repo_path)):
            return ""
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return "\n".join(text.rstrip("\r\n") for n, text in enumerate(handle, 1) if start <= n <= end).strip()[:200]
    except OSError:
        return ""


def _sync_semgrep(repo_path: str) -> List[Dict[str, Any]]:
    semgrep_bin = shutil.which("semgrep")
    if not semgrep_bin:
        logger.warning("semgrep is not installed; code scanning skipped")
        return []
    result = None
    for configs in ([LOCAL_RULES, *REGISTRY_PACKS], [LOCAL_RULES]):
        try:
            result = _run(_command(semgrep_bin, configs, repo_path))
        except subprocess.TimeoutExpired:
            logger.warning("semgrep timed out with configs %s", configs)
            result = None
        if result is not None:
            break
    findings: List[Dict[str, Any]] = []
    seen = set()
    for match in (result or {}).get("results", []):
        rel_path = os.path.relpath(match.get("path", ""), repo_path).replace("\\", "/")
        start = match.get("start", {}).get("line", 1)
        rule = match.get("check_id", "code-pattern").split(".")[-1]
        if (rule, rel_path, start) in seen:
            continue  # the same rule can arrive from local and registry configs
        seen.add((rule, rel_path, start))
        extra = match.get("extra", {})
        metadata = extra.get("metadata", {}) or {}
        findings.append({
            "title": metadata.get("title") or rule.replace("-", " ").title(),
            "category": "Source Code Vulnerability",
            "severity": SEVERITY_MAP.get(str(extra.get("severity", "WARNING")).upper(), "medium"),
            "confidence": str(metadata.get("confidence", "high")).lower() if str(metadata.get("confidence", "")).lower() in ("high", "medium", "low") else "high",
            "description": extra.get("message", "Insecure pattern detected."),
            "filePath": rel_path,
            "lineStart": start,
            "lineEnd": match.get("end", {}).get("line", start),
            "codeSnippet": _snippet(repo_path, match),
            "recommendation": metadata.get("recommendation") or "Sanitize inputs and use safe abstractions.",
        })
    return findings


class CodeScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "code_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(_sync_semgrep, repo_path)
