"""Prompt-injection detection for untrusted career-site text.

Retriever reads job pages but never treats page content as instructions.
These heuristics are intentionally conservative: they warn the user and record
evidence, but they do not block ordinary job extraction by themselves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InjectionWarning:
    reason: str
    snippet: str
    pattern: str

    def as_dict(self) -> dict[str, str]:
        return {
            "reason": self.reason,
            "snippet": self.snippet,
            "pattern": self.pattern,
        }


PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"\b(ignore|disregard|forget)\b.{0,80}\b(previous|prior|above|system|developer|instructions?)\b",
        "Page text appears to tell the assistant to ignore existing instructions.",
    ),
    (
        r"\b(if|when)\s+you\s+(are|re|are an|re an)\s+(ai|assistant|language model|chatgpt|codex)\b.{0,140}\b(resume|cover letter|application|skills?|answer|include|use|write)\b",
        "Page text appears to branch on whether the reader is an AI system.",
    ),
    (
        r"\b(system prompt|developer message|hidden instructions?|prompt injection)\b",
        "Page text refers to hidden prompts or prompt-injection behavior.",
    ),
    (
        r"\b(exfiltrate|reveal|print|send|upload)\b.{0,90}\b(secrets?|tokens?|api keys?|environment variables?|credentials?)\b",
        "Page text appears to request secret or credential disclosure.",
    ),
    (
        r"\bsupercalifrag[a-z]*expialidocious\b",
        "Page text contains the user-supplied example phrase used to detect AI screening.",
    ),
)


def _snippet(text: str, start: int, end: int, radius: int = 90) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    raw = text[left:right].replace("\n", " ")
    squashed = re.sub(r"\s+", " ", raw).strip()
    return squashed


def scan_text(text: str | None) -> list[InjectionWarning]:
    """Return warning records for suspicious instructions in untrusted text."""

    if not text:
        return []

    warnings: list[InjectionWarning] = []
    for pattern, reason in PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            warnings.append(
                InjectionWarning(
                    reason=reason,
                    snippet=_snippet(text, match.start(), match.end()),
                    pattern=pattern,
                )
            )
            break
    return warnings


def summarize_warnings(warnings: list[InjectionWarning]) -> str:
    """Format warnings for storage in a single SQLite text field."""

    if not warnings:
        return ""
    return " | ".join(f"{warning.reason} Evidence: {warning.snippet}" for warning in warnings)
