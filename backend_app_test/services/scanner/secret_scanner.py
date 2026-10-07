import os
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
                                "filePath": os.path.relpath(item.get("File", ""), repo_path).replace("\\", "/"),
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
                    rel_path = os.path.relpath(file_path, repo_path).replace("\\", "/")
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
