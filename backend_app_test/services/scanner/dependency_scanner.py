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
                                pkg, version = line.split("==")[0].strip(), line.split("==")[1].strip()
                                vulns = await self._query_osv(client, pkg, version, "PyPI")
                                for v in vulns:
                                    findings.append(self._format_finding(v, pkg, version, "requirements.txt", line_num))
                except Exception:
                    pass

            pkg_file = os.path.join(repo_path, "package.json")
            if os.path.exists(pkg_file):
                try:
                    with open(pkg_file, "r", encoding="utf-8", errors="ignore") as f:
                        data = json.load(f)
                        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                        for pkg, ver in deps.items():
                            clean_ver = re.sub(r"[^\d.]", "", ver)
                            if clean_ver:
                                vulns = await self._query_osv(client, pkg, clean_ver, "npm")
                                for v in vulns:
                                    findings.append(self._format_finding(v, pkg, clean_ver, "package.json", 1))
                except Exception:
                    pass

        return findings

    async def _query_osv(self, client: httpx.AsyncClient, package: str, version: str, ecosystem: str) -> List[Dict[str, Any]]:
        try:
            res = await client.post(
                "https://api.osv.dev/v1/query",
                json={"package": {"name": package, "ecosystem": ecosystem}, "version": version}
            )
            if res.status_code == 200:
                return res.json().get("vulns", [])
        except Exception:
            pass
        return []

    def _format_finding(self, vuln: Dict[str, Any], pkg: str, ver: str, file_path: str, line: int) -> Dict[str, Any]:
        vuln_id = vuln.get("id", "VULN-ID")
        summary = vuln.get("summary") or vuln.get("details", f"Vulnerability detected in {pkg}")
        return {
            "title": f"{pkg}@{ver}: {vuln_id}",
            "category": "Dependency Vulnerability",
            "severity": "high",
            "confidence": "high",
            "description": f"{summary[:250]} (Advisory: {vuln_id})",
            "filePath": file_path,
            "lineStart": line,
            "lineEnd": line,
            "codeSnippet": f'"{pkg}": "{ver}"',
            "recommendation": f"Upgrade {pkg} to the latest patched version to resolve {vuln_id}."
        }
