# reborn2 — Inbox Helper (Quest Option A)

This is the real project for the Quest submission. The older re_born directory is a prototype/reference only; the actual code, UI, tests, and submission artifacts live in this reborn2 folder.

This project takes a pile of candidate messages, classifies each one by intent, drafts a short reply, and leaves every decision for a human reviewer before anything is sent.

The repository includes the rule-based classifier, review pipeline, web UI, and Gmail
connector used for a real inbox workflow.

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

## Web page

FastAPI backend (`api/`) plus the "Candidate desk" web app (`web/`: Vite, React, TypeScript,
Tailwind, TanStack Router). The app holds no pipeline logic of its own: every decision comes
from the backend through `/api`. It has four screens:

- **Home** (`/#/`) is the landing page: drop a CSV, try the sample, pick up the open batch,
  or reopen recent work. The `Desk` name and the **Home** link in the sidebar always lead back.
- **Past work** (`/#/history`) lists every finished batch with its counts. Open one to keep
  reviewing, or delete it.

- **Pipeline** shows the run live. Four stations (safety check, grouping, drafting, your
  review) fill up as emails move through, a feed shows each email's result at every step,
  and clicking an email shows the scores behind each decision.
- **Review** is a mail-style workspace: a queue grouped by topic, the original email next
  to an editable draft, and approve / reject / send on each one. Shortcuts: `J`/`K` move,
  `A` approve, `S` open mail app, `X` reject.

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload          # API on :8000

cd web && npm install
npm run dev                            # page on http://localhost:5173 (proxies /api)
# or: npm run build, then open http://localhost:8000 (FastAPI serves web/dist)
# views live at /#/ (Review) and /#/pipeline (hash routing, so refresh works)
```

- "Try the sample inbox" on the first screen runs `data/messages.csv`.
- Sending: on an approved reply, **Open in mail app** (shortcut `S`) opens your default mail
  app with the recipient, `Re:` subject and reply already filled in. A web page can't tell
  whether you actually sent it, so after sending click **Mark as sent**, which records it in
  `outbox/sent.csv`. Very long replies are also copied to the clipboard in case the mail app
  trims the body. Replace `deliver()` in `api/service.py` if you later want the server to send.
- **Settings** (Settings button): API key, chat model, decision model, and custom drafting
  instructions. Saved to `data/settings.json`. Env `OPENROUTER_API_KEY` is still used as a
  fallback if no key is stored in settings.
- **Past work is stored as plain JSON files**, one per batch, in `data/history/` (newest 50
  kept), next to `data/session.json` for the open batch. No database. Edits and approvals
  are saved to the batch as you make them. Delete a file to remove a batch by hand.
- Error banners (failed uploads, model failures) each have a Dismiss button.
- Offline by default (rule-based decisions, template drafts) when no API key is set.
- Offline runs finish in milliseconds. To watch the pipeline while recording a demo, start
  the server with `DEMO_DELAY_MS=400`; the sidebar says when a run was slowed this way.
- Approve is blocked while a draft is empty or still has `[placeholders]`. Editing an
  approved draft cancels the approval.
- **Session persistence**: after a run finishes, the current batch (drafts + statuses) is
  written to `data/session.json`. A page refresh or server restart restores the review
  workspace. Uploading a new CSV replaces it.
- Tests: `pip install -r requirements-dev.txt && python -m pytest -q` (the Gmail tests are in `tests/test_gmail.py`)

### Gmail connector (read and send through the Gmail API)

The backend talks to Gmail's regular REST API (`https://gmail.googleapis.com/gmail/v1`) with your own Google
login. It works with any personal Gmail account. (Google's hosted Gmail *MCP* server is not used: it is in the
Workspace Developer Preview, which does not accept personal Gmail accounts.)
You sign in once with Google; after that **Home** can pull emails by subject and **Review** can send replies.

**One-time setup in Google Cloud (about 10 minutes):**
1. Create a project at `console.cloud.google.com`.
2. APIs & Services, Library: enable **Gmail API** (the Gmail MCP API is not needed).
3. OAuth consent screen: External; add your own Gmail under **Test users**; add scopes
   `gmail.readonly` and `gmail.compose`.
4. Credentials, OAuth client ID, **Web application**; Authorized redirect URI
   `http://localhost:8000/api/gmail/callback`. Copy the Client ID and Client secret.

**In the app:** Settings, Gmail section: paste the client ID and secret, press **Connect Gmail**,
press Allow on Google's page. **Test** checks the login and shows which account you are signed in as. (Or set the env vars
`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` instead of using Settings.)

- **Fetch**: Home, "Or pull from Gmail". Subject keywords (comma separated, any one matches), optional
  From/To dates, max 100. Inbox only; your own sent mail is skipped. One row per thread (its newest incoming
  message). The emails then go through safety, grouping and drafting like a CSV.
- **Send**: for Gmail batches the approved reply gets a **Send via Gmail** button (shortcut `S`, with a
  confirm). It replies inside the original thread. Nothing is ever sent before you approve and click.
  CSV batches keep the mail-app flow, and a CSV can never trigger a Gmail send.
- **Files** (both git-ignored): `data/gmail.json` (client id/secret, advanced overrides) and
  `data/gmail_token.json` (the login). Delete the second, or press Disconnect, to sign out.
- While the Google app is in Testing mode Google expires the login about every 7 days; press Connect again.
- Backend code: `api/gmail.py`. Tests: `tests/test_gmail.py` (uses a fake in-process Gmail API, no Google needed).

### Web app layout

```
web/src/
  main.tsx, router.tsx        entry and routes (Home "/", Review "/review", Pipeline "/pipeline", Past work "/history")
  lib/api.ts, types.ts        typed client for the FastAPI endpoints (incl. /api/history)
  lib/store.tsx               batch state, polling while a run is active
  lib/groups.ts               group names, stage labels, formatting helpers
  components/                 Shell, Home, History, Review, Pipeline, Settings, parts
```