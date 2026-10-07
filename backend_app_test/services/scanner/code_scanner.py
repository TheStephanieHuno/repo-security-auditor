import os
import json
import shutil
import subprocess
import asyncio
from typing import List, Dict, Any
from backend_app_test.services.scanner.base import SecurityCheck

def _sync_semgrep(repo_path: str) -> List[Dict[str, Any]]:
    findings = []
    semgrep_bin = shutil.which("semgrep")
    if not semgrep_bin:
        return findings

    try:
        res = subprocess.run(
            [semgrep_bin, "scan", "--config", "auto", "--json", repo_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        if res.stdout:
            result = json.loads(res.stdout)
            for match in result.get("results", []):
                sev = match.get("extra", {}).get("severity", "WARNING").upper()
                severity_map = {"ERROR": "critical", "WARNING": "high", "INFO": "medium"}
                findings.append({
                    "title": match.get("check_id", "Insecure Code Pattern").split(".")[-1].replace("-", " ").title(),
                    "category": "Source Code Vulnerability",
                    "severity": severity_map.get(sev, "medium"),
                    "confidence": "high",
                    "description": match.get("extra", {}).get("message", "Insecure pattern detected."),
                    "filePath": os.path.relpath(match.get("path", ""), repo_path).replace("\\", "/"),
                    "lineStart": match.get("start", {}).get("line", 1),
                    "lineEnd": match.get("end", {}).get("line", 1),
                    "codeSnippet": match.get("extra", {}).get("lines", "").strip()[:200],
                    "recommendation": "Refactor code to sanitize inputs or use safe standard libraries."
                })
    except Exception:
        pass
    return findings

class CodeScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "code_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(_sync_semgrep, repo_path)
