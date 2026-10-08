import os
import json
import re
import httpx
from typing import List, Dict, Any
from backend_app_test.services.scanner.base import SecurityCheck

class DependencyScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "dependency_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        findings = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            req_file = os.path.join(repo_path, "requirements.txt")
            if os.path.exists(req_file):
                try:
                    with open(req_file, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, start=1):
                            line = line.strip()
                            if line and not line.startswith("#") and "==" in line:
                                pkg, ver = line.split("==")[0].strip(), line.split("==")[1].strip()
                                res = await client.post("https://api.osv.dev/v1/query", json={"package": {"name": pkg, "ecosystem": "PyPI"}, "version": ver})
                                if res.status_code == 200:
                                    for v in res.json().get("vulns", []):
                                        findings.append({
                                            "title": f"{pkg}@{ver}: {v.get('id', 'CVE')}",
                                            "category": "Dependency Vulnerability",
                                            "severity": "high",
                                            "confidence": "high",
                                            "description": (v.get("summary") or v.get("details", ""))[:250],
                                            "filePath": "requirements.txt",
                                            "lineStart": line_num,
                                            "lineEnd": line_num,
                                            "codeSnippet": f'"{pkg}": "{ver}"',
                                            "recommendation": f"Upgrade {pkg}."
                                        })
                except Exception:
                    pass
        return findings
