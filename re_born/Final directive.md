# Final Directive — re_born / Stall Alerter

This is the directive I gave the AI (and myself) for the final build. It is frozen for evaluation.

## Goal
CLI tool `stall_alerter` that answers: who is stalled, who first, what to do.

## Input
`python -m src.stall_alerter --csv data/hiring_board.csv --days 7`
- `--csv`: path to hiring board CSV (required)
- `--days`: stall threshold in days (default 7)
- `--today`: override today as YYYY-MM-DD (for tests/demo determinism)
- `--output`: optional output CSV path

CSV schema (header required):
```
candidate_id,name,stage,last_moved_date,owner,role
101,Amina Yusuf,Quest,2026-10-01,HR-A,Backend
```

## Output
Stdout table sorted by days_stalled DESC:
```
candidate_id | name | stage | days_stalled | owner | action | reason
```
Plus summary line: `Flagged N of M candidates stalled >=7d as of YYYY-MM-DD`.

Action map:
- Applied -> "Send screening invite or reject"
- Screen -> "Schedule interview or close"
- Quest -> "Nudge submission or mark dropped"
- HR -> "Align on salary/availability"
- Paid Test -> "Review output and decide"
- Offer -> "Follow up daily until signed"
- Unknown/other -> "Review manually"

Reason template (one sentence):
`"{name} in {stage} for {days}d (last move {date}) — {action_lower}."`

## Non-goals
- No auto-email, no DB, no web UI. Human reviews every action.
- No external deps. Stdlib only. Python 3.10+.

## Quality bar
- `pytest` passes, coverage of edge cases: bad date, missing col, future date, empty file.
- README tells exactly how to run + demo.
- Honest log of what broke in logs/day4.md
