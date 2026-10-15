# Final Directive — reborn2 / Inbox Helper

## Goal
Build the real Quest Option A project in reborn2: read candidate messages, group them by intent, draft one short reply per message, and keep the human in the loop before anything is sent.

## Deliverable definition
This project is the actual submission folder. The older re_born directory is only a prototype/reference. The final build lives in reborn2 and includes the Python pipeline, the review API, the web app, and the Gmail integration.

## Inputs
- CSV upload: `id,sender,email,subject,body`
- Gmail fetch: keywords, optional date range, and max results
- Settings: API key, chat model, decision model, and custom prompt

## Main run paths
```bash
cd reborn2
python -m src.inbox_helper --csv data/messages.csv
python -m src.inbox_helper --csv data/messages.csv --output out.csv
```

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload
```

```bash
cd web && npm install
npm run dev
```

## Output
- Structured item records with intent, confidence, draft, reasons, and status
- Human-review workflow: pending, approved, rejected
- Export of approved responses as CSV
- Persistent session data in `data/session.json` and saved batch history in `data/history/`
- Gmail-in-thread replies for approved drafts only

## Intent rules
The pipeline uses explicit, reviewable rules. First match wins in a fixed priority order.

- quest_status: quest, submit, submission, deadline, 5 days, upload, deliverable
- schedule: schedule, interview, call, meet, time, available, reschedule
- salary: salary, pay, compensation, offer, ctc, stipend
- technical_issue: error, bug, failed, cannot, can't, login, upload fail, link
- withdrawal: withdraw, drop out, not interested, quit, stop
- other: fallback when nothing matches well

Confidence is based on rule strength and the number of matching signals.

## Review behavior
- Human reviews every draft before it is sent.
- No automatic send path.
- Approved text may be edited before sending.
- Editing an approved draft cancels approval until it is re-approved.

## Non-goals
- No hidden auto-send. The human has to approve and click send.
- No model-only decisions without a fallback.
- No premature scaling beyond the real workflow needed for this Quest.

## Quality bar
- Code runs and is readable.
- README explains how to run it.
- Tests cover classification, fallback logic, and the main Gmail/API flow.
- Logs are honest about what failed and what was learned.
- The project stays focused on the Quest objective instead of drifting into a broader product.
