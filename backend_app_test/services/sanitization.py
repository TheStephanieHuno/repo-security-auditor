import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

MAX_SNIPPET_LENGTH = 500
MAX_PATH_LENGTH = 256

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"new\s+instructions?:",
    r"system\s*:\s*",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"###\s*(system|instruction|user|assistant)",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(all\s+)?(your|previous|prior)",
    r"do\s+not\s+follow\s+(any|previous|prior)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

def strip_control_characters(text: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

def neutralize_injection_patterns(text: str) -> str:
    sanitized = text
    for pattern in _COMPILED:
        sanitized = pattern.sub("[REDACTED_INSTRUCTION]", sanitized)
    return sanitized

def escape_markdown(text: str) -> str:
    return text.replace("```", "` ` `").replace("{{", "{ {").replace("}}", "} }")

def sanitize_file_path(path: Optional[str]) -> str:
    if not path:
        return "unknown"
    return re.sub(r"\.\.[\\/]", "", path.strip())[:MAX_PATH_LENGTH] or "unknown"

def sanitize_code_snippet(snippet: Optional[str]) -> str:
    if not snippet:
        return "No code snippet available."
    text = strip_control_characters(snippet.strip())
    text = neutralize_injection_patterns(text)
    text = escape_markdown(text)
    if len(text) > MAX_SNIPPET_LENGTH:
        text = text[:MAX_SNIPPET_LENGTH] + "\n... [truncated]"
    return text or "No code snippet available."

def sanitize_finding_for_llm(title: str, description: str, file_path: str, code_snippet: Optional[str], category: str) -> dict:
    return {
        "title": sanitize_code_snippet(title)[:200],
        "description": sanitize_code_snippet(description)[:400],
        "file_path": sanitize_file_path(file_path),
        "code_snippet": sanitize_code_snippet(code_snippet),
        "category": strip_control_characters(category)[:100],
    }
