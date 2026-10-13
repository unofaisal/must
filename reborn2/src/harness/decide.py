"""Decision-model provider (OpenRouter Decisions API). Stdlib only.

POST https://openrouter.ai/api/alpha/decisions
  {model, state, questions} -> {answers: {qid: {type, noul|choice|...}}}

Model-agnostic: any `output_modalities=decisions` model ID works
(mercury-decide, mercury-decide:free, jev, ...). Decision models return
typed answers with probabilities — never text. Your code gates on them.

Question shapes (per docs):
  noul:   {type, instructions, criteria? {true, false}} -> {type, noul: 0..1}
  choice: {type, instructions, criteria: {opt: desc}}   -> {choice, probabilities, confidence}
  score:  {type, instructions, criteria: [low..high]}   -> {score, legend, probabilities, confidence}
"""
from __future__ import annotations
import json
import os
import urllib.request
import urllib.error

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"

class DecideProvider:
    """Thin urllib client for the Decisions API. No extra deps."""

    name = "decide"

    def __init__(self, model: str = "respan/span-01-lite",
                 api_key: str | None = None, timeout: int = 30):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.timeout = timeout

    def build_request(self, state, questions: dict) -> dict:
        # The Decisions API accepts state as text or as a Respan input/output
        # trace. Pipeline state is a structured sender/message dict, not that
        # trace format, so send it as readable JSON text.
        api_state = (json.dumps(state, ensure_ascii=False)
                     if isinstance(state, dict) else state)
        if not isinstance(api_state, str):
            raise TypeError("decision state must be a string or dictionary")
        return {"model": self.model, "state": api_state, "questions": questions}

    def ask(self, state, questions: dict) -> dict:
        """Return raw `answers` dict. Raises RuntimeError on transport/API error."""
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing (env or api_key=)")
        data = json.dumps(self.build_request(state, questions)).encode()
        req = urllib.request.Request(
            DECISIONS_URL, data=data,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:2000]
            raise RuntimeError(f"decisions {e.code}: {body}") from e
        if "answers" not in raw:
            raise RuntimeError(f"unexpected decisions response: {str(raw)[:500]}")
        return raw["answers"]

    def ask_nouls(self, state, specs: dict[str, tuple[str, str, str]]) -> dict[str, float]:
        """Convenience: {qid: (instructions, true_desc, false_desc)} -> {qid: P(yes)}.

        Validates each answer's `type` before reading `noul` (docs: treat
        unexpected type as error, never as default).
        """
        questions = {
            qid: {"type": "noul", "instructions": ins,
                  "criteria": {"true": t, "false": f}}
            for qid, (ins, t, f) in specs.items()
        }
        answers = self.ask(state, questions)
        out = {}
        for qid in specs:
            ans = answers.get(qid)
            if not isinstance(ans, dict) or ans.get("type") != "noul" or "noul" not in ans:
                raise RuntimeError(f"bad noul answer for {qid!r}: {ans!r}")
            out[qid] = float(ans["noul"])
        return out


class RuleDecide:
    """Offline fallback behind the same `ask` interface. Keyword heuristics only.

    Used when no API key is available. Never as confident as a real
    decision model — mid-range scores keep borderline cases human-visible.
    """

    name = "rule-decide"

    _SAFETY = {
        "gives_instructions": ("ignore previous instructions", "ignore your instructions",
                               "system prompt", "you are now", "do as i say", "override",
                               "jailbreak", "reveal your", "disregard"),
        "asks_about_other": ("my friend", "other candidate", "other applicant",
                             "another candidate", "on behalf of", "my son",
                             "my daughter", "my wife", "my husband"),
        "angry_or_distressed": ("angry", "furious", "disgusted", "unacceptable",
                                "lawsuit", "complaint", "outraged", "appalled",
                                "threat", "distress"),
    }

    _GROUP = {
        "status_update": ("status", "update", "hear back", "checking on",
                          "where do i stand", "submitted", "under review", "any news"),
        "reschedule": ("reschedul", "interview", "postpone", "slot", "missed",
                       "confirming", "meet", "available"),
        "hiring_process": ("process", "next steps", "timeline", "documents",
                           "format", "background check", "refer", "prepare"),
        "pay_or_contract": ("salary", "compensation", "contract", "offer",
                            "ctc", "stipend", "probation", "remote", "visa",
                            "sponsor", "part-time", "negotiat"),
        "withdrawal": ("withdraw", "drop out", "not interested", "quit", "no longer"),
        "feedback": ("feedback", "reject", "reapply", "improve", "why was"),
    }

    _BANK = {**_SAFETY, **_GROUP}

    def _text(self, state) -> str:
        if isinstance(state, str):
            return state.lower()
        msg = (state.get("message") or {}) if isinstance(state, dict) else {}
        return f"{msg.get('subject', '')} {msg.get('body', '')}".lower()

    def ask(self, state, questions: dict) -> dict:
        text = self._text(state)
        out = {}
        for qid, q in questions.items():
            if q.get("type") != "noul":
                raise ValueError(f"RuleDecide only answers noul, got {q.get('type')!r}")
            keys = self._BANK.get(qid, ())
            hits = sum(1 for k in keys if k in text)
            out[qid] = {"type": "noul", "noul": 0.9 if hits >= 2 else (0.7 if hits == 1 else 0.05)}
        return out
