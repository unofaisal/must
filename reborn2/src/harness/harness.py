"""Harness: prompt → run → verify → log. Human reviews every output."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from .providers import RuleProvider

@dataclass
class HarnessResult:
    prompt: str
    output: str
    provider: str
    passed: bool
    notes: str = ""
    files: list[str] = field(default_factory=list)
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Harness:
    def __init__(self, provider=None, verify: Callable[[str], bool] | None = None):
        self.provider = provider or RuleProvider()
        self.verify = verify or (lambda out: bool(out.strip()))
        self.history: list[HarnessResult] = []

    def run(self, prompt: str, files: list[str] | None = None) -> HarnessResult:
        output = self.provider.complete(prompt, files=files)
        try:
            passed = bool(self.verify(output))
            notes = ""
        except Exception as e:  # verify must never crash the loop
            passed = False
            notes = f"verify error: {e}"
        res = HarnessResult(prompt=prompt, output=output,
                            provider=getattr(self.provider, "name", "?"),
                            passed=passed, notes=notes, files=list(files or []))
        self.history.append(res)
        return res

    def logline(self, r: HarnessResult) -> str:
        status = "PASS" if r.passed else "FAIL"
        return f"[{r.at}] {status} ({r.provider}): {r.prompt!r} -> {r.output!r} {r.notes}"
