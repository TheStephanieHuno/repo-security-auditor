import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "backend_app_test")

files = {
    # 1. Base SecurityCheck interface
    os.path.join(APP_DIR, "services", "scanner", "base.py"): '''from abc import ABC, abstractmethod
from typing import List, Dict, Any

class SecurityCheck(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        pass
''',

    # 2. Secret Scanner (Gitleaks + Regex fallback)
    os.path.join(APP_DIR, "services", "scanner", "secret_scanner.py"): '''import os
import re
import json
import shutil
import asyncio
from typing import List, Dict, Any
from backend_app_test.services.scanner.base import SecurityCheck

SECRET_PATTERNS = [
    {
        "title": "Hardcoded AWS Access Key",
        "category": "Secret Exposure",
        "severity": "critical",
        "confidence": "high",
        "pattern": r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
        "recommendation": "Revoke this AWS key immediately and load credentials via environment variables."
    },
    {
        "title": "Hardcoded GitHub Personal Access Token",
        "category": "Secret Exposure",
        "severity": "critical",
        "confidence": "high",
        "pattern": r"ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}",
        "recommendation": "Revoke the exposed GitHub token immediately and rotate repository secrets."
    },
    {
        "title": "Exposed Private Cryptographic Key",
        "category": "Secret Exposure",
        "severity": "critical",
        "confidence": "high",
        "pattern": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "recommendation": "Delete the private key from source control and generate a new key pair immediately."
    },
    {
        "title": "Hardcoded Stripe Secret API Key",
        "category": "Secret Exposure",
        "severity": "high",
        "confidence": "high",
        "pattern": r"sk_live_[0-9a-zA-Z]{24}",
        "recommendation": "Rotate your Stripe secret key in the Stripe Dashboard and use environment variables."
    }
]

class SecretScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "secret_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        findings = []
        if shutil.which("gitleaks"):
            try:
                report_file = os.path.join(repo_path, "gitleaks_report.json")
                proc = await asyncio.create_subprocess_exec(
                    "gitleaks", "dir", repo_path, "--report-format", "json", "--report-path", report_file, "--no-git",
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                await proc.wait()
                if os.path.exists(report_file):
                    with open(report_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for item in data:
                            findings.append({
                                "title": f"Exposed Secret: {item.get('Description', 'Secret detected')}",
                                "category": "Secret Exposure",
                                "severity": "critical",
                                "confidence": "high",
                                "description": f"Gitleaks detected an exposed secret matching rule '{item.get('RuleID')}'.",
                                "filePath": os.path.relpath(item.get("File", ""), repo_path).replace("\\\\", "/"),
                                "lineStart": item.get("StartLine", 1),
                                "lineEnd": item.get("EndLine", 1),
                                "codeSnippet": item.get("Secret", ""),
                                "recommendation": "Rotate this credential immediately."
                            })
                    try:
                        os.remove(report_file)
                    except OSError:
                        pass
                    return findings
            except Exception:
                pass

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv", "__pycache__")]
            for file in files:
                if file.endswith((".py", ".ts", ".js", ".json", ".yaml", ".yml", ".env", ".txt", ".conf", ".ini")):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path).replace("\\\\", "/")
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()
                            for line_num, line in enumerate(lines, start=1):
                                for p in SECRET_PATTERNS:
                                    match = re.search(p["pattern"], line, re.IGNORECASE)
                                    if match:
                                        findings.append({
                                            "title": p["title"],
                                            "category": p["category"],
                                            "severity": p["severity"],
                                            "confidence": p["confidence"],
                                            "description": f"Found {p['title']} in {rel_path}.",
                                            "filePath": rel_path,
                                            "lineStart": line_num,
                                            "lineEnd": line_num,
                                            "codeSnippet": line.strip()[:150],
                                            "recommendation": p["recommendation"]
                                        })
                    except Exception:
                        continue
        return findings
''',

    # 3. Code Scanner (Semgrep)
    os.path.join(APP_DIR, "services", "scanner", "code_scanner.py"): '''import os
import json
import asyncio
from typing import List, Dict, Any
from backend_app_test.services.scanner.base import SecurityCheck

class CodeScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "code_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        findings = []
        try:
            proc = await asyncio.create_subprocess_exec(
                "semgrep", "scan", "--config", "auto", "--json", repo_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await proc.communicate()
            if stdout:
                result = json.loads(stdout.decode("utf-8", errors="ignore"))
                for match in result.get("results", []):
                    sev = match.get("extra", {}).get("severity", "WARNING").upper()
                    severity_map = {"ERROR": "critical", "WARNING": "high", "INFO": "medium"}
                    findings.append({
                        "title": match.get("check_id", "Insecure Code Pattern").split(".")[-1].replace("-", " ").title(),
                        "category": "Source Code Vulnerability",
                        "severity": severity_map.get(sev, "medium"),
                        "confidence": "high",
                        "description": match.get("extra", {}).get("message", "Insecure pattern detected."),
                        "filePath": os.path.relpath(match.get("path", ""), repo_path).replace("\\\\", "/"),
                        "lineStart": match.get("start", {}).get("line", 1),
                        "lineEnd": match.get("end", {}).get("line", 1),
                        "codeSnippet": match.get("extra", {}).get("lines", "").strip()[:200],
                        "recommendation": "Refactor code to sanitize inputs or use safe standard libraries."
                    })
        except Exception:
            pass
        return findings
''',

    # 4. Dependency Scanner (OSV API)
    os.path.join(APP_DIR, "services", "scanner", "dependency_scanner.py"): '''import os
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
                            clean_ver = re.sub(r"[^\\d.]", "", ver)
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
''',

    # 5. Config Scanner
    os.path.join(APP_DIR, "services", "scanner", "config_scanner.py"): '''import os
from typing import List, Dict, Any
from backend_app_test.services.scanner.base import SecurityCheck

class ConfigScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "config_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        findings = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), repo_path).replace("\\\\", "/")
                
                if file in (".env", ".env.local", ".env.production", ".env.staging") and not file.endswith(".example"):
                    findings.append({
                        "title": "Committed Environment Secrets File",
                        "category": "Insecure Configuration",
                        "severity": "critical",
                        "confidence": "high",
                        "description": f"Production environment file '{rel_path}' is tracked in source control.",
                        "filePath": rel_path,
                        "lineStart": 1,
                        "lineEnd": 1,
                        "codeSnippet": f"# Environment file: {file}",
                        "recommendation": "Remove this file from Git history and add it to .gitignore."
                    })

                if file.endswith((".py", ".js", ".ts", ".json", ".yaml")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, start=1):
                                if "DEBUG = True" in line or "DEBUG=true" in line:
                                    findings.append({
                                        "title": "Debug Mode Enabled in Configuration",
                                        "category": "Insecure Configuration",
                                        "severity": "medium",
                                        "confidence": "high",
                                        "description": "Application debug mode is active.",
                                        "filePath": rel_path,
                                        "lineStart": line_num,
                                        "lineEnd": line_num,
                                        "codeSnippet": line.strip(),
                                        "recommendation": "Disable application debug parameters in production."
                                    })
                                if 'allow_origins=["*"]' in line.replace(" ", "") or "origin: '*'" in line:
                                    findings.append({
                                        "title": "Permissive CORS Wildcard Configured",
                                        "category": "Insecure Configuration",
                                        "severity": "low",
                                        "confidence": "medium",
                                        "description": "CORS policy permits all origins (*).",
                                        "filePath": rel_path,
                                        "lineStart": line_num,
                                        "lineEnd": line_num,
                                        "codeSnippet": line.strip(),
                                        "recommendation": "Restrict CORS Origins to trusted domain names."
                                    })
                    except Exception:
                        continue
        return findings
''',

    # 6. Finding Normalizer
    os.path.join(APP_DIR, "services", "scanner", "normalizer.py"): '''import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from backend_app_test.db.models import Finding as DBFinding

def normalize_scanner_findings(
    raw_findings: List[Dict[str, Any]],
    scan_id: uuid.UUID,
    repository_id: uuid.UUID
) -> List[DBFinding]:
    db_findings = []
    now = datetime.now(timezone.utc)

    for item in raw_findings:
        db_finding = DBFinding(
            id=uuid.uuid4(),
            scan_id=scan_id,
            repository_id=repository_id,
            severity=item.get("severity", "medium").lower(),
            confidence=item.get("confidence", "high").lower(),
            category=item.get("category", "General Security"),
            title=item.get("title", "Security Issue"),
            description=item.get("description", ""),
            file_path=item.get("filePath", "unknown"),
            line_start=item.get("lineStart"),
            line_end=item.get("lineEnd"),
            code_snippet=item.get("codeSnippet"),
            recommendation=item.get("recommendation", "Review and remediate issue."),
            ai_explanation=item.get("aiExplanation"),
            review_status="open",
            review_note=None,
            reviewed_by=None,
            reviewed_at=None,
            created_at=now
        )
        db_findings.append(db_finding)

    return db_findings
''',

    # 7. Runner / Orchestrator
    os.path.join(APP_DIR, "services", "scanner", "runner.py"): '''import os
import shutil
import tempfile
import asyncio
import logging
from typing import List, Dict, Any, Callable

from backend_app_test.services.scanner.secret_scanner import SecretScanner
from backend_app_test.services.scanner.code_scanner import CodeScanner
from backend_app_test.services.scanner.dependency_scanner import DependencyScanner
from backend_app_test.services.scanner.config_scanner import ConfigScanner

logger = logging.getLogger(__name__)

CLONE_TIMEOUT_SECONDS = int(os.getenv("CLONE_TIMEOUT_SECONDS", 60))
SCAN_TIMEOUT_SECONDS = int(os.getenv("SCAN_TIMEOUT_SECONDS", 300))
MAX_CLONE_SIZE_MB = int(os.getenv("MAX_CLONE_SIZE_MB", 100))

SCANNERS = [
    SecretScanner(),
    CodeScanner(),
    DependencyScanner(),
    ConfigScanner(),
]

def get_directory_size_mb(path: str) -> float:
    total_bytes = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(fp)
            except OSError:
                pass
    return total_bytes / (1024 * 1024)

async def clone_repository(repo_url: str, branch: str, target_dir: str) -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "1", "--branch", branch, repo_url, target_dir,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.wait(), timeout=float(CLONE_TIMEOUT_SECONDS))
        return proc.returncode == 0
    except asyncio.TimeoutError:
        logger.error(f"Git clone timed out after {CLONE_TIMEOUT_SECONDS}s for {repo_url}")
        return False
    except Exception as e:
        logger.error(f"Git clone failed for {repo_url} on branch {branch}: {e}")
        return False

async def run_full_security_scan(
    repo_url: str,
    branch: str,
    progress_callback: Callable[[int], Any] = None
) -> List[Dict[str, Any]]:
    workspace_dir = tempfile.mkdtemp(prefix="rsa_scan_")
    all_findings: List[Dict[str, Any]] = []

    try:
        if progress_callback:
            await progress_callback(10)

        cloned = await clone_repository(repo_url, branch, workspace_dir)
        if not cloned:
            raise RuntimeError(f"Could not clone repository {repo_url} on branch '{branch}'.")

        size_mb = get_directory_size_mb(workspace_dir)
        if size_mb > MAX_CLONE_SIZE_MB:
            raise RuntimeError(f"Repository size ({size_mb:.1f}MB) exceeds allowed limit of {MAX_CLONE_SIZE_MB}MB.")

        if progress_callback:
            await progress_callback(30)

        total_scanners = len(SCANNERS)
        for idx, scanner in enumerate(SCANNERS):
            try:
                findings = await asyncio.wait_for(scanner.run(workspace_dir), timeout=60.0)
                all_findings.extend(findings)
            except Exception as e:
                logger.error(f"Scanner '{scanner.name}' failed: {e}")

            if progress_callback:
                progress = 30 + int(((idx + 1) / total_scanners) * 60)
                await progress_callback(progress)

        if progress_callback:
            await progress_callback(100)

    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)

    return all_findings
'''
}

for filepath, content in files.items():
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created: {filepath}")

print("\nAll Scanner Engine files created successfully in absolute paths!")