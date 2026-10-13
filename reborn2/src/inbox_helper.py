"""Inbox helper — Quest Option A. Stdlib only."""
from __future__ import annotations
import argparse
import csv
import sys
from dataclasses import dataclass

REQUIRED = ["id", "sender", "subject", "body"]

from .grouping import Grouper
from .drafting import Drafter

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

def process(csv_path: str, grouper=None, drafter=None) -> list[Result]:
    results, _ = run_pipeline(csv_path, grouper=grouper, drafter=drafter)
    return results


def run_pipeline(csv_path: str, grouper=None, drafter=None, safety=None):
    """Full pipeline: safety gate -> grouping -> drafting.

    Returns (results, quarantined). Quarantined messages skip grouping and
    drafting entirely and go to a human.
    """
    from .grouping import OTHER
    from .safety import SafetyGate
    grouper = grouper or Grouper()
    drafter = drafter or Drafter()  # templates when provider is None
    safety = safety or SafetyGate()  # RuleDecide fallback when no key
    cands = {}
    try:
        with open("data/candidates.csv", newline="", encoding="utf-8") as f:
            for c in csv.DictReader(f):
                cands[c["email"]] = c
    except FileNotFoundError:
        pass
    out: list[Result] = []
    quarantined: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("empty CSV")
        missing = [c for c in REQUIRED if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"missing columns: {', '.join(missing)}")
        for row in reader:
            if not any((v or "").strip() for v in row.values()):
                continue
            sender = cands.get(row.get("email") or "", {"name": row["sender"]})
            msg = {"subject": row["subject"] or "", "body": row["body"] or ""}
            s = safety.check(msg, sender)
            if s.quarantined:
                quarantined.append({"id": row["id"], "sender": row["sender"],
                                    "email": row.get("email") or "",
                                    "reasons": s.reasons})
                continue
            g = grouper.label(msg, sender)
            primary = g.primary
            conf = "high" if primary != OTHER and g.scores.get(primary, 0) >= 0.8 else (
                "medium" if primary != OTHER else "low")
            d = drafter.draft(msg, g.labels, sender)
            out.append(Result(id=row["id"], sender=row["sender"], email=(row.get("email") or ""),
                              intent=primary, labels=g.labels, confidence=conf,
                              draft=d.draft, placeholders=d.placeholders))
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
        from .grouping import Grouper
        from .drafting import Drafter
        from .safety import SafetyGate
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
