"""Pipeline stage 2: grouping. One noul per intent — a message can carry several.

Ten intent checks; if none fires, the message is `other` — so every message
always ends up with at least one high label. Labels are ordered by score, so
`primary` is the strongest one. No quarantine path here:
grouping routes, it never blocks (safety already ran in stage 1).

Provider-agnostic: any object with `ask(state, questions)`. Live path is
DecideProvider; default/fallback is RuleDecide (same fallback style as safety).
A live-provider error falls back to RuleDecide for that message, never to nothing.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from .harness.decide import RuleDecide

GROUP_THRESHOLD = 0.5  # routing, not blocking — docs' default probe gate

INTENTS = ("status_update", "reschedule", "hiring_process",
           "pay_or_contract", "withdrawal", "feedback",
           "technical_issue", "deadline_extension",
           "submission_or_documents", "thanks_or_ack")
OTHER = "other"

GROUP_SPECS: dict[str, tuple[str, str, str]] = {
    "status_update": (
        "Is the sender asking for a status update — progress, news, or a decision on their own application or submission?",
        "Requests where their case stands or when they will hear back.",
        "No status request; different topic.",
    ),
    "reschedule": (
        "Is the sender asking to schedule, reschedule, move, confirm, or apologise for missing a call, interview, or meeting?",
        "Any scheduling request, slot proposal, or missed-interview recovery.",
        "No scheduling content.",
    ),
    "hiring_process": (
        "Is the sender asking how the hiring process works — steps, timeline, documents, interview format, referrals, or background checks?",
        "Questions about process mechanics or what comes next.",
        "Not about process mechanics.",
    ),
    "pay_or_contract": (
        "Is the sender asking about pay, salary, compensation, contract type or terms, offer details, hours, remote work, or visa/sponsorship?",
        "Any money, contract, or employment-terms question.",
        "No pay-or-contract content.",
    ),
    "withdrawal": (
        "Is the sender withdrawing from the process, quitting, or saying they are no longer interested?",
        "Explicit or implied withdrawal.",
        "Staying in the process.",
    ),
    "feedback": (
        "Is the sender asking for feedback on a rejection, why they were rejected, how to improve, or whether they can reapply?",
        "Post-rejection feedback or reapplication question.",
        "No feedback request.",
    ),
    "technical_issue": (
        "Is the sender reporting a technical problem, such as a login failure, broken link, upload error, or not being able to open a page, portal, or file?",
        "Access, login, upload, or portal problems.",
        "No technical problem.",
    ),
    "deadline_extension": (
        "Is the sender asking for more time, an extension, or whether a deadline can be moved?",
        "Asks to extend or move a deadline.",
        "No deadline request.",
    ),
    "submission_or_documents": (
        "Is the sender sending or attaching documents (CV, portfolio, test answers), or asking whether something they submitted was received?",
        "Document submissions and receipt confirmations.",
        "No submission or document content.",
    ),
    "thanks_or_ack": (
        "Is the sender only saying thanks or acknowledging a message, with no question or request?",
        "Pure thanks or acknowledgement.",
        "Contains a question or request.",
    ),
    "other": (
        "Is this email about something that none of the other topics cover?",
        "Anything that doesn't fit the groups above.",
        "Clearly fits one of the other topics.",
    ),
}


@dataclass
class GroupingResult:
    labels: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    provider: str = "?"

    @property
    def primary(self) -> str:
        return self.labels[0] if self.labels else OTHER


class Grouper:
    def __init__(self, provider=None, threshold: float = GROUP_THRESHOLD):
        self.provider = provider or RuleDecide()
        self.threshold = threshold
        self._fallback = RuleDecide()

    def build_state(self, message: dict, sender: dict) -> dict:
        return {
            "sender": {
                "name": sender.get("name", ""),
                "email": sender.get("email", ""),
                "stage": sender.get("stage", ""),
                "role_applied": sender.get("role_applied", ""),
            },
            "message": {
                "subject": message.get("subject", ""),
                "body": message.get("body", ""),
            },
        }

    def build_questions(self) -> dict:
        return {
            qid: {"type": "noul", "instructions": ins,
                  "criteria": {"true": t, "false": f}}
            for qid, (ins, t, f) in GROUP_SPECS.items()
        }

    def _scores(self, answers: dict) -> dict[str, float]:
        scores = {}
        for qid in GROUP_SPECS:
            ans = (answers or {}).get(qid, {})
            if ans.get("type") == "noul" and "noul" in ans:
                scores[qid] = float(ans["noul"])
            else:
                scores[qid] = 0.0  # malformed answer = no signal, `other` catches it
        return scores

    def label(self, message: dict, sender: dict) -> GroupingResult:
        state = self.build_state(message, sender)
        try:
            answers = self.provider.ask(state, self.build_questions())
        except Exception:
            answers = self._fallback.ask(state, self.build_questions())  # never labelless
        scores = self._scores(answers)
        labels = sorted((qid for qid in INTENTS if scores[qid] >= self.threshold),
                        key=lambda qid: -scores[qid])  # stable: ties keep INTENTS order
        if not labels:
            labels = [OTHER]
            scores[OTHER] = 1.0
        return GroupingResult(labels=labels, scores=scores,
                              provider=getattr(self.provider, "name", "?"))
