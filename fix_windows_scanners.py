import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "backend_app_test")

runner_code = '''import os
import stat
import shutil
import tempfile
import asyncio
import subprocess
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

def remove_readonly(func, path, exc_info):
    """Windows fix: Clears read-only flag on .git files before deletion."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

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

def _sync_clone(repo_url: str, branch: str, target_dir: str) -> tuple[bool, str]:
    git_bin = shutil.which("git") or "git"
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    # Try 1: Clone specific branch
    cmd = [git_bin, "clone", "--depth", "1", "--branch", branch, repo_url, target_dir]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=CLONE_TIMEOUT_SECONDS)
        if res.returncode == 0:
            return True, ""
    except Exception as e:
        logger.warning(f"Branch clone failed: {e}")

    # Try 2: Fallback clone default branch
    try:
        shutil.rmtree(target_dir, onerror=remove_readonly)
        os.makedirs(target_dir, exist_ok=True)
        cmd_fallback = [git_bin, "clone", "--depth", "1", repo_url, target_dir]
        res2 = subprocess.run(cmd_fallback, capture_output=True, text=True, env=env, timeout=CLONE_TIMEOUT_SECONDS)
        if res2.returncode == 0:
            return True, ""
        return False, res2.stderr or "Git clone returned non-zero exit code"
    except Exception as e:
        return False, str(e)

async def clone_repository(repo_url: str, branch: str, target_dir: str) -> bool:
    ok, err = await asyncio.to_thread(_sync_clone, repo_url, branch, target_dir)
    if not ok:
        logger.error(f"Git clone error for {repo_url}: {err}")
    return ok

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
            raise RuntimeError(f"Repository size ({size_mb:.1f}MB) exceeds limit of {MAX_CLONE_SIZE_MB}MB.")

        if progress_callback:
            await progress_callback(30)

        total_scanners = len(SCANNERS)
        for idx, scanner in enumerate(SCANNERS):
            try:
                findings = await asyncio.wait_for(scanner.run(workspace_dir), timeout=60.0)
                all_findings.extend(findings)
            except Exception as e:
                logger.error(f"Scanner '{scanner.name}' error: {e}")

            if progress_callback:
                progress = 30 + int(((idx + 1) / total_scanners) * 60)
                await progress_callback(progress)

        if progress_callback:
            await progress_callback(100)

    finally:
        shutil.rmtree(workspace_dir, onerror=remove_readonly)

    return all_findings
'''

code_scanner_code = '''import os
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
                    "filePath": os.path.relpath(match.get("path", ""), repo_path).replace("\\\\", "/"),
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
'''

with open(os.path.join(APP_DIR, "services", "scanner", "runner.py"), "w", encoding="utf-8") as f:
    f.write(runner_code)
print("Updated runner.py")

with open(os.path.join(APP_DIR, "services", "scanner", "code_scanner.py"), "w", encoding="utf-8") as f:
    f.write(code_scanner_code)
print("Updated code_scanner.py")

print("Windows subprocess optimizations applied successfully!")