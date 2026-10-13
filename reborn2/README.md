# reborn2 — Inbox Helper (Quest Option A)

Groups candidate messages by intent, drafts short replies. Human reviews all.

## Run
```bash
cd reborn2
python -m src.inbox_helper --csv data/messages.csv
python -m src.inbox_helper --csv data/messages.csv --output out.csv
```

## Test
```bash
python -m pytest -q
```

## Files
- `src/safety.py` — stage 1: SafetyGate (3 noul checks, 0.8 quarantine gate)
- `src/grouping.py` — stage 2: Grouper (6 noul intent checks, multi-label, `other` fallback)
- `src/drafting.py` — stage 3: Drafter (chat prompt + templates fallback, bracket placeholders)
- `src/harness/chat.py` — ChatProvider (OpenAI-compatible completions, default dots-3-note-preview:free)
- `src/harness/decide.py` — DecideProvider (Decisions API) + RuleDecide (offline fallback)
- `src/inbox_helper.py` — classifier + drafter + CLI (downstream of safety gate)
- `data/messages.csv` — 42 messages (id,sender,email,subject,body), every email matches a candidate
- `data/candidates.csv` — 30 candidate records (candidate_id,name,email,role_applied,stage,last_stage_change,interview_date,interview_time,recruiter)
- `data/candidate_emails.csv` — source 30-email set (same senders/emails as candidates)
- `tests/` — inbox_helper, message↔candidate consistency, safety-gate tests
- `intent.md`, `Final directive.md`, `logs/`, `docs/unlearned.md`
