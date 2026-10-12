# reborn2 — Quest Option A: Inbox Helper

## Intent
Takes a pile of candidate messages, groups by intent, drafts a short reply for each. Human reviews every draft before send (no auto-send).

## Scope
- Rule-based classifier (stdlib only), explicit keyword rules so behavior is reviewable
- Intents: quest_status, schedule, salary, technical_issue, withdrawal, other
- CLI: `python -m src.inbox_helper --csv data/messages.csv --output out.csv`

## Why A second
re_born (Option C) proved CSV+tests+CLI loop. reborn2 raises load: NLP-ish grouping + drafting, still deterministic and testable.
