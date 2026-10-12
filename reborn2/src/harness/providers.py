"""Providers for the harness. Rule-based today, LLM hook tomorrow. Stdlib only."""
from __future__ import annotations
from typing import Protocol

class Provider(Protocol):
    name: str
    def complete(self, prompt: str, files: list[str] | None = None) -> str: ...

class RuleProvider:
    """Deterministic fallback — maps to inbox_helper DRAFTS logic without import cycle."""
    name = "rule"

    def complete(self, prompt: str, files: list[str] | None = None) -> str:
        p = prompt.lower()
        if any(k in p for k in ("withdraw", "quit", "not interested")):
            return "noted — you're withdrawn."
        if any(k in p for k in ("error", "failed", "cannot", "login", "broken")):
            return "sorry — send error/screenshot and we'll fix."
        if "quest" in p or "deadline" in p or "submit" in p:
            return "deadline is 5 days; upload intent, code, logs, video."
        if any(k in p for k in ("schedule", "interview", "meet", "available")):
            return "share 2-3 slots with timezone."
        if any(k in p for k in ("salary", "pay", "offer", "ctc")):
            return "comp aligned post-Quest; share expectations."
        return "human will review."
