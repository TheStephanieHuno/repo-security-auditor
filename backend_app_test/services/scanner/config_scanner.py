import os
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
                rel_path = os.path.relpath(os.path.join(root, file), repo_path).replace("\\", "/")
                if file in (".env", ".env.local", ".env.production") and not file.endswith(".example"):
                    findings.append({
                        "title": "Committed Environment Secrets File",
                        "category": "Insecure Configuration",
                        "severity": "critical",
                        "confidence": "high",
                        "description": f"File '{rel_path}' is committed to version control.",
                        "filePath": rel_path,
                        "lineStart": 1,
                        "lineEnd": 1,
                        "codeSnippet": f"# Config: {file}",
                        "recommendation": "Remove from git and add to .gitignore."
                    })
        return findings
