"""Inbox helper — Quest Option A. Stdlib only."""
from __future__ import annotations
import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from .grouping import Grouper, OTHER
from .drafting import Drafter
from .safety import SafetyGate

REQUIRED = ["id", "sender", "subject", "body"]
CANDIDATES_PATH = Path(__file__).resolve().parent.parent / "data" / "candidates.csv"


@dataclass
class Result:
    id: str
    sender: str
    email: str
    intent: str  # primary label (first of labels)
    labels: list
    confidence: str
    draft: str
    placeholders: list = None
    subject: str = ""
    body: str = ""
    draft_source: str = ""  # "template", "template (fallback)", or the model provider name


def process(csv_path: str, grouper=None, drafter=None) -> list[Result]:
    results, _ = run_pipeline(csv_path, grouper=grouper, drafter=drafter)
    return results


def load_candidates(path=CANDIDATES_PATH) -> dict:
    """Candidate records keyed by email. Missing file = no records."""
    cands = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for c in csv.DictReader(f):
                cands[c["email"]] = c
    except FileNotFoundError:
        pass
    return cands


def read_rows(f) -> list[dict]:
    """Validate the header and return the non-blank rows of a message CSV."""
    reader = csv.DictReader(f)
    if reader.fieldnames is None:
        raise ValueError("empty CSV")
    missing = [c for c in REQUIRED if c not in reader.fieldnames]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    return [row for row in reader
            if any((v or "").strip() for v in row.values() if isinstance(v, str))]


def process_row(row: dict, cands: dict, grouper, drafter, safety):
    """One message through safety -> grouping -> drafting.

    Returns (Result, None), or (None, quarantine_dict) when the safety gate
    stops it. Quarantined messages skip grouping and drafting entirely.
    """
    sender = cands.get(row.get("email") or "", {"name": row["sender"] or ""})
    msg = {"subject": row["subject"] or "", "body": row["body"] or ""}
    s = safety.check(msg, sender)
    if s.quarantined:
        return None, {"id": row["id"] or "", "sender": row["sender"] or "",
                      "email": row.get("email") or "", "subject": msg["subject"],
                      "body": msg["body"], "reasons": s.reasons}
    g = grouper.label(msg, sender)
    primary = g.primary
    conf = "high" if primary != OTHER and g.scores.get(primary, 0) >= 0.8 else (
        "medium" if primary != OTHER else "low")
    d = drafter.draft(msg, g.labels, sender)
    return Result(id=row["id"] or "", sender=row["sender"] or "", email=row.get("email") or "",
                  intent=primary, labels=g.labels, confidence=conf,
                  draft=d.draft, placeholders=d.placeholders,
                  subject=msg["subject"], body=msg["body"], draft_source=d.provider), None


def run_pipeline(csv_path: str, grouper=None, drafter=None, safety=None):
    """Full pipeline: safety gate -> grouping -> drafting.

    Returns (results, quarantined). Quarantined messages skip grouping and
    drafting entirely and go to a human.
    """
    grouper = grouper or Grouper()
    drafter = drafter or Drafter()  # templates when provider is None
    safety = safety or SafetyGate()  # RuleDecide fallback when no key
    cands = load_candidates()
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = read_rows(f)
    out: list[Result] = []
    quarantined: list[dict] = []
    for row in rows:
        result, quarantine = process_row(row, cands, grouper, drafter, safety)
        if quarantine:
            quarantined.append(quarantine)
        else:
            out.append(result)
    return out, quarantined


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Inbox helper: group + draft, human reviews.")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--output", default=None)
    ap.add_argument("--live", action="store_true",
                    help="use live decision + chat models (needs OPENROUTER_API_KEY)")
    args = ap.parse_args(argv)
    grouper = drafter = safety = None
    if args.live:
        from .harness.decide import DecideProvider
        from .harness.chat import ChatProvider
        grouper, drafter = Grouper(DecideProvider()), Drafter(ChatProvider())
        safety = SafetyGate(DecideProvider())
    try:
        results, quarantined = run_pipeline(args.csv, grouper=grouper,
                                            drafter=drafter, safety=safety)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if quarantined:
        print(f"\n!! QUARANTINED ({len(quarantined)}) — human review, no draft written:")
        for q in quarantined:
            print(f"[{q['id']}] {q['sender']} <{q['email']}>")
            for r in q["reasons"]:
                print(f"    - {r}")
    groups: dict[str, list[Result]] = {}
    for r in results:
        groups.setdefault(r.intent, []).append(r)
    for intent in sorted(groups):
        print(f"\n== {intent} ({len(groups[intent])}) ==")
        for r in groups[intent]:
            print(f"[{r.id}] {r.sender} <{r.email}> ({r.confidence}) [{';'.join(r.labels)}]: {r.draft}")
    print(f"\nGrouped {len(results)} messages into {len(groups)} intents. All drafts need human review before send.")
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "sender", "email", "intent", "labels", "confidence", "draft",
                        "placeholders", "needs_review"])
            for r in results:
                w.writerow([r.id, r.sender, r.email, r.intent, ";".join(r.labels),
                            r.confidence, r.draft, ";".join(r.placeholders or []), "true"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
