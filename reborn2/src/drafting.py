"""Pipeline stage 3: drafting. Review-only output — a human edits and sends.

The model gets the email + its group labels + the sender record and writes
a short reply. One fixed instruction line: unknown facts become bracket
placeholders for the human to fill. No send step exists; placeholders are
plain text, extracted into `placeholders` so review tooling can list them.

Offline path (no key): template replies per primary label — same DRAFTS
inbox_helper has always used.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

from .harness.chat import ChatProvider

PLACEHOLDER_RE = re.compile(r"\[([^\[\]]+)\]")

DRAFTS = {
    "status_update": "Hi {sender}, thanks for checking — here is where your application stands; we will update you as soon as the stage moves. Reply here if anything looks stuck. — Team",
    "reschedule": "Hi {sender}, happy to reschedule — please share 2-3 slots (with timezone) and we'll confirm. — Team",
    "hiring_process": "Hi {sender}, here is how the process works: screening, Quest, HR alignment, Paid Test, offer. Most stages take a few days each. — Team",
    "pay_or_contract": "Hi {sender}, comp is aligned post-Quest/Paid Test based on scope. Please share expectations and we'll discuss on HR call. — Team",
    "withdrawal": "Hi {sender}, noted — you're withdrawn, no further action. Reply if you want back in later. — Team",
    "feedback": "Hi {sender}, thanks for asking — a recruiter will share brief feedback on your last stage within a few days. — Team",
    "other": "Hi {sender}, thanks — a human will review and reply shortly. — Team",
}


def build_prompt(message: dict, labels: list[str], sender: dict) -> str:
    name = sender.get("name", "the candidate")
    return (
        "You are drafting a recruiter reply to a job candidate. "
        "Write a short reply (under 120 words), friendly and professional.\n"
        f"Candidate: {name} ({sender.get('email', 'no email')}), "
        f"applied for {sender.get('role_applied', 'unknown role')}, "
        f"currently at stage: {sender.get('stage', 'unknown')}.\n"
        f"Intent labels: {', '.join(labels)}.\n"
        f"Candidate's message (subject: {message.get('subject', '')}):\n"
        f"{message.get('body', '')}\n"
        "If the reply needs a fact you don't have (a date, a salary), "
        'write "[place_holder_text eg date]".\n'
        "Never assert a fact you were not given — pay amounts, dates, contract "
        "terms, decisions, or names of people. When in doubt, use a [placeholder].\n"
        "Draft only the reply body, no explanations."
    )


def find_placeholders(draft: str) -> list[str]:
    return PLACEHOLDER_RE.findall(draft)


@dataclass
class DraftResult:
    draft: str
    placeholders: list[str] = field(default_factory=list)
    provider: str = "?"


class Drafter:
    """Provider-agnostic: any object with `complete(prompt)`. None -> templates."""

    def __init__(self, provider=None):
        self.provider = provider

    def draft(self, message: dict, labels: list[str], sender: dict) -> DraftResult:
        name = (sender.get("name", "") or "").strip() or "there"
        if self.provider is None:  # offline path: templates by design
            primary = labels[0] if labels else "other"
            return DraftResult(draft=DRAFTS.get(primary, DRAFTS["other"]).format(sender=name),
                               placeholders=[], provider="template")
        prompt = build_prompt(message, labels, sender)
        text = self.provider.complete(prompt)
        return DraftResult(draft=text, placeholders=find_placeholders(text),
                           provider=getattr(self.provider, "name", "?"))
