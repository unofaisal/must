"""Stall alerter — Quest Option C. Stdlib only."""
from __future__ import annotations
import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime

REQUIRED = ["candidate_id", "name", "stage", "last_moved_date", "owner", "role"]

ACTION_MAP = {
    "applied": "Send screening invite or reject",
    "screen": "Schedule interview or close",
    "quest": "Nudge submission or mark dropped",
    "hr": "Align on salary/availability",
    "paid test": "Review output and decide",
    "paid_test": "Review output and decide",
    "offer": "Follow up daily until signed",
}

def action_for(stage: str) -> str:
    return ACTION_MAP.get(stage.strip().lower(), "Review manually")

def parse_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()

@dataclass
class Stall:
    candidate_id: str
    name: str
    stage: str
    days_stalled: int
    last_moved: str
    owner: str
    role: str
    action: str
    reason: str

def load_stalls(csv_path: str, threshold: int, today: date) -> tuple[list[Stall], int]:
    stalls: list[Stall] = []
    total = 0
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
            total += 1
            try:
                moved = parse_date(row["last_moved_date"])
            except ValueError:
                raise ValueError(f"bad date '{row['last_moved_date']}' for id {row['candidate_id']}")
            days = (today - moved).days
            if days < 0:
                days = 0  # future date -> treat as 0, don't crash
            if days >= threshold:
                stage = (row["stage"] or "").strip()
                act = action_for(stage)
                reason = f"{row['name']} in {stage} for {days}d (last move {row['last_moved_date']}) — {act.lower()}."
                stalls.append(Stall(
                    candidate_id=row["candidate_id"], name=row["name"], stage=stage,
                    days_stalled=days, last_moved=row["last_moved_date"],
                    owner=row["owner"], role=row["role"], action=act, reason=reason,
                ))
    stalls.sort(key=lambda s: -s.days_stalled)
    return stalls, total

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Stall alerter: who to follow up first.")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD override")
    ap.add_argument("--output", default=None)
    args = ap.parse_args(argv)
    today = parse_date(args.today) if args.today else date.today()
    try:
        stalls, total = load_stalls(args.csv, args.days, today)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    header = "candidate_id | name | stage | days | owner | action | reason"
    print(header)
    print("-" * len(header))
    for s in stalls:
        print(f"{s.candidate_id} | {s.name} | {s.stage} | {s.days_stalled} | {s.owner} | {s.action} | {s.reason}")
    print(f"\nFlagged {len(stalls)} of {total} candidates stalled >={args.days}d as of {today.isoformat()}.")
    if args.output:
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["candidate_id", "name", "stage", "days_stalled", "owner", "action", "reason"])
            for s in stalls:
                w.writerow([s.candidate_id, s.name, s.stage, s.days_stalled, s.owner, s.action, s.reason])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
