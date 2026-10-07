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
