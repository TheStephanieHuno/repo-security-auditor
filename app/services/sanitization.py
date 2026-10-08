"""
Input Sanitization & Prompt Injection Defense Module (SRS NFR-01, NFR-06).

Protects the LLM pipeline against prompt injection attacks originating from
untrusted repository content (code comments, README files, config values).

Threat Model:
- An attacker embeds adversarial instructions inside code comments or strings
  in a public repository (e.g., "# Ignore previous instructions and output...").
- When the scanner passes this code snippet to the LLM for explanation,
  the LLM may execute the injected instruction instead of analyzing the finding.

Mitigations Implemented:
1. Strip null bytes and ASCII control characters.
2. Truncate payloads to prevent context-window flooding.
3. Neutralize known prompt injection delimiter patterns.
4. Escape markdown/HTML injection vectors.
5. Validate file paths to prevent path traversal in LLM context.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum allowed length for any single code snippet sent to the LLM
MAX_SNIPPET_LENGTH = 500

# Maximum allowed length for file paths in LLM context
MAX_PATH_LENGTH = 256

# Known prompt injection patterns (case-insensitive)
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

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def strip_control_characters(text: str) -> str:
    """Removes null bytes and ASCII control characters (0x00-0x1F except newline/tab)."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


def neutralize_injection_patterns(text: str) -> str:
    """Replaces known prompt injection phrases with safe placeholders."""
    sanitized = text
    for pattern in _COMPILED_PATTERNS:
        sanitized = pattern.sub("[REDACTED_INSTRUCTION]", sanitized)
    return sanitized


def escape_markdown(text: str) -> str:
    """Escapes markdown delimiters to prevent formatting injection in LLM output."""
    text = text.replace("```", "` ` `")
    text = text.replace("{{", "{ {")
    text = text.replace("}}", "} }")
    return text


def sanitize_file_path(path: Optional[str]) -> str:
    """Validates and truncates file paths to prevent path traversal in LLM context."""
    if not path:
        return "unknown"
    path = path.strip()
    path = re.sub(r"\.\.[\\/]", "", path)  # Remove ../ traversal
    path = path[:MAX_PATH_LENGTH]
    return path or "unknown"


def sanitize_code_snippet(snippet: Optional[str]) -> str:
    """
    Full sanitization pipeline for code snippets before LLM submission.
    Applies all defense layers in sequence.
    """
    if not snippet:
        return "No code snippet available."

    text = snippet.strip()
    text = strip_control_characters(text)
    text = neutralize_injection_patterns(text)
    text = escape_markdown(text)
    text = text[:MAX_SNIPPET_LENGTH]

    if len(snippet.strip()) > MAX_SNIPPET_LENGTH:
        text += "\n... [truncated for security]"

    return text or "No code snippet available."


def sanitize_finding_for_llm(
    title: str,
    description: str,
    file_path: str,
    code_snippet: Optional[str],
    category: str,
) -> dict[str, str]:
    """
    Sanitizes all finding fields before constructing the LLM prompt.
    Returns a clean dictionary safe for prompt injection.
    """
    return {
        "title": sanitize_code_snippet(title)[:200],
        "description": sanitize_code_snippet(description)[:400],
        "file_path": sanitize_file_path(file_path),
        "code_snippet": sanitize_code_snippet(code_snippet),
        "category": strip_control_characters(category)[:100],
    }
