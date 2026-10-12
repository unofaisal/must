"""Inbox helper — Quest Option A. Stdlib only."""
from __future__ import annotations
import argparse
import csv
import sys
from dataclasses import dataclass

REQUIRED = ["id", "sender", "subject", "body"]

RULES: list[tuple[str, list[str]]] = [
    ("withdrawal", ["withdraw", "drop out", "not interested", "quit", "stop"]),
    ("technical_issue", ["error", "failed", "cannot", "can't", "login", "broken", "bug", "upload fail", "trouble", "access"]),
    ("quest_status", ["quest", "submit", "submission", "deadline", "deliverable", "upload"]),
    ("schedule", ["schedule", "interview", "call", "meet", "available", "reschedule", "slot"]),
    ("salary", ["salary", "pay", "compensation", "offer", "ctc", "stipend"]),
]

DRAFTS = {
    "quest_status": "Hi {sender}, thanks for checking — your Quest deadline is 5 days from assignment. Upload intent.md, code+README, logs, video link, and unlearned note. Reply here if stuck and we'll unblock. — Team",
    "schedule": "Hi {sender}, happy to schedule — please share 2-3 slots (with timezone) and we'll confirm. — Team",
    "salary": "Hi {sender}, comp is aligned post-Quest/Paid Test based on scope. Please share expectations and we'll discuss on HR call. — Team",
    "technical_issue": "Hi {sender}, sorry for the trouble — please forward the exact error/screenshot + file size/link and we'll fix within a day. — Team",
    "withdrawal": "Hi {sender}, noted — you're withdrawn, no further action. Reply if you want back in later. — Team",
    "other": "Hi {sender}, thanks — a human will review and reply shortly. — Team",
}

@dataclass
class Result:
    id: str
    sender: str
    intent: str
    confidence: str
    draft: str

def classify(subject: str, body: str) -> tuple[str, str]:
    text = f"{subject} {body}".lower()
    for intent, keywords in RULES:
        hits = sum(1 for k in keywords if k in text)
        if hits >= 2:
            return intent, "high"
        if hits == 1:
            # check no higher-priority double-hit later? first single wins per order
            # to keep deterministic, return on first single hit
            return intent, "medium"
    return "other", "low"

def process(csv_path: str) -> list[Result]:
    out: list[Result] = []
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
            intent, conf = classify(row["subject"] or "", row["body"] or "")
            draft = DRAFTS[intent].format(sender=(row["sender"] or "").strip() or "there")
            out.append(Result(id=row["id"], sender=row["sender"], intent=intent, confidence=conf, draft=draft))
    return out

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Inbox helper: group + draft, human reviews.")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--output", default=None)
    args = ap.parse_args(argv)
    try:
        results = process(args.csv)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    groups: dict[str, list[Result]] = {}
    for r in results:
        groups.setdefault(r.intent, []).append(r)
    for intent in sorted(groups):
        print(f"\n== {intent} ({len(groups[intent])}) ==")
        for r in groups[intent]:
            print(f"[{r.id}] {r.sender} ({r.confidence}): {r.draft}")
    print(f"\nGrouped {len(results)} messages into {len(groups)} intents. All drafts need human review before send.")
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "sender", "intent", "confidence", "draft", "needs_review"])
            for r in results:
                w.writerow([r.id, r.sender, r.intent, r.confidence, r.draft, "true"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
