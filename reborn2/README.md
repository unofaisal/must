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

## Web page (review UI)

FastAPI backend (`api/`) plus a small React page (`web/`). Upload a CSV, review the
groups, edit each draft, then approve, reject, or send it. Send is a stub: it records
the reply in `outbox/sent.csv` and sends no email (replace `deliver()` in `api/service.py`).

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload          # API on :8000

cd web && npm install
npm run dev                            # page on http://localhost:5173 (proxies /api)
# or: npm run build, then open http://localhost:8000 (FastAPI serves web/dist)
```

- Offline by default (rule-based decisions, template drafts). Set `OPENROUTER_API_KEY`
  before starting the server to use the live decision and chat models.
- Approve is blocked while a draft is empty or still has `[placeholders]`. Editing an
  approved draft cancels the approval.
- One in-memory batch for one user: restarting the server clears it.
- API tests: `pip install -r requirements-dev.txt && python -m pytest -q`
