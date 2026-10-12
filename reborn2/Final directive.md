# Final Directive — reborn2 / Inbox Helper

## Goal
Group candidate messages by intent and draft one short reply each for human review.

## Input
`python -m src.inbox_helper --csv data/messages.csv --output out.csv`
- CSV header required: `id,sender,subject,body`
- `--output`: optional CSV with drafts

## Output
Stdout grouped by intent, plus summary counts. Output CSV columns:
`id,sender,intent,confidence,draft,needs_review`

## Intent rules (first match wins, keyword substring, case-insensitive)
- quest_status: quest, submit, submission, deadline, 5 days, upload, deliverable
- schedule: schedule, interview, call, meet, time, available, reschedule
- salary: salary, pay, compensation, offer, ctc, stipend
- technical_issue: error, bug, failed, cannot, can't, login, upload fail, link
- withdrawal: withdraw, drop out, not interested, quit, stop
- other: fallback, confidence low

Confidence: high (2+ keywords), medium (1 keyword), low (fallback).

## Draft templates (short, human reviews)
- quest_status: "Hi {sender}, thanks for checking — your Quest deadline is 5 days from assignment. Upload intent.md, code+README, logs, video link, and unlearned note. Reply here if stuck and we'll unblock. — Team"
- schedule: "Hi {sender}, happy to schedule — please share 2-3 slots (with timezone) and we'll confirm. — Team"
- salary: "Hi {sender}, comp is aligned post-Quest/Paid Test based on scope. Please share expectations and we'll discuss on HR call. — Team"
- technical_issue: "Hi {sender}, sorry for the trouble — please forward the exact error/screenshot + file size/link and we'll fix within a day. — Team"
- withdrawal: "Hi {sender}, noted — you're withdrawn, no further action. Reply if you want back in later. — Team"
- other: "Hi {sender}, thanks — a human will review and reply shortly. — Team"

## Non-goals
- No auto-send, no LLM API, no web UI. Stdlib only, Python 3.10+.
- Every draft has needs_review=true.

## Quality bar
- pytest passes (classify each intent + fallback + output csv).
- README run instructions. Logs honest about misclassifies.
