import os
import re
from typing import List, Dict, Any
from backend_app_test.services.scanner.base import SecurityCheck

SECRET_PATTERNS = [
    {"title": "Hardcoded AWS Access Key", "category": "Secret Exposure", "severity": "critical", "confidence": "high", "pattern": r"\b(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b", "recommendation": "Revoke AWS key immediately."},
    {"title": "Hardcoded GitHub Personal Access Token", "category": "Secret Exposure", "severity": "critical", "confidence": "high", "pattern": r"\bghp_[a-zA-Z0-9]{36}\b|\bgithub_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}\b", "recommendation": "Revoke GitHub token."},
    {"title": "Exposed Private Cryptographic Key", "category": "Secret Exposure", "severity": "critical", "confidence": "high", "pattern": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "recommendation": "Rotate private key pair."},
    {"title": "Hardcoded Stripe Secret API Key", "category": "Secret Exposure", "severity": "high", "confidence": "high", "pattern": r"\bsk_live_[0-9a-zA-Z]{24,}\b", "recommendation": "Rotate Stripe key."}
]


# Source, config, and key-material files that can hold credentials (US-09:
# AWS keys, GitHub tokens, Stripe keys, RSA/SSH private keys).
SCANNED_SUFFIXES = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".yaml", ".yml", ".env", ".txt",
    ".conf", ".cfg", ".ini", ".toml", ".properties", ".xml", ".sh", ".rb", ".go", ".java", ".php",
    ".cs", ".tf", ".key", ".pem", ".p8", ".ppk",
)
KEY_FILE_NAMES = {"id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}


def should_scan(file_name: str) -> bool:
    lowered = file_name.lower()
    return lowered.endswith(SCANNED_SUFFIXES) or lowered.startswith(".env") or lowered in KEY_FILE_NAMES


def mask_secret(line: str, secret: str) -> str:
    """Never store a usable credential: keep the first 4 characters only."""
    return line.replace(secret, secret[:4] + "*" * 8)


class SecretScanner(SecurityCheck):
    @property
    def name(self) -> str:
        return "secret_scanner"

    async def run(self, repo_path: str) -> List[Dict[str, Any]]:
        findings = []
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv", "__pycache__")]
            for file in files:
                if should_scan(file):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path).replace("\\", "/")
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, start=1):
                                for p in SECRET_PATTERNS:
                                    # Case-sensitive: key formats have fixed case, and
                                    # IGNORECASE matched base64 hashes in lock files.
                                    match = re.search(p["pattern"], line)
                                    if match:
                                        findings.append({
                                            "title": p["title"],
                                            "category": p["category"],
                                            "severity": p["severity"],
                                            "confidence": p["confidence"],
                                            "description": f"Detected {p['title']} in {rel_path}.",
                                            "filePath": rel_path,
                                            "lineStart": line_num,
                                            "lineEnd": line_num,
                                            "codeSnippet": mask_secret(line.strip(), match.group(0))[:150],
                                            "recommendation": p["recommendation"]
                                        })
                    except Exception:
                        continue
        return findings
