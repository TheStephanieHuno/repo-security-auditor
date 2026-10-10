import os
import re
import json
import shutil
import asyncio
from typing import List, Dict, Any
from backend_app_test.services.scanner.base import SecurityCheck

SECRET_PATTERNS = [
    {"title": "Hardcoded AWS Access Key", "category": "Secret Exposure", "severity": "critical", "confidence": "high", "pattern": r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}", "recommendation": "Revoke AWS key immediately."},
    {"title": "Hardcoded GitHub Personal Access Token", "category": "Secret Exposure", "severity": "critical", "confidence": "high", "pattern": r"ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}", "recommendation": "Revoke GitHub token."},
    {"title": "Exposed Private Cryptographic Key", "category": "Secret Exposure", "severity": "critical", "confidence": "high", "pattern": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "recommendation": "Rotate private key pair."},
    {"title": "Hardcoded Stripe Secret API Key", "category": "Secret Exposure", "severity": "high", "confidence": "high", "pattern": r"sk_live_[0-9a-zA-Z]{24}", "recommendation": "Rotate Stripe key."}
]

class SecretScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "secret_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        findings = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv", "__pycache__")]
            for file in files:
                if file.endswith((".py", ".ts", ".js", ".json", ".yaml", ".yml", ".env", ".txt", ".conf", ".ini")):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path).replace("\\", "/")
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, start=1):
                                for p in SECRET_PATTERNS:
                                    if re.search(p["pattern"], line, re.IGNORECASE):
                                        findings.append({
                                            "title": p["title"],
                                            "category": p["category"],
                                            "severity": p["severity"],
                                            "confidence": p["confidence"],
                                            "description": f"Detected {p['title']} in {rel_path}.",
                                            "filePath": rel_path,
                                            "lineStart": line_num,
                                            "lineEnd": line_num,
                                            "codeSnippet": line.strip()[:150],
                                            "recommendation": p["recommendation"]
                                        })
                    except Exception:
                        continue
        return findings
