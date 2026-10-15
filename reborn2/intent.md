# reborn2 — Quest Option A: Inbox Helper

## Intent
This is the real project for the Quest submission. We built a human-reviewed inbox helper that reads candidate messages, groups them by intent, drafts a short reply for each one, and leaves the final decision to a person before anything is sent.

## What the tool does
- Reads candidate email bodies from a CSV file or from Gmail
- Classifies each incoming message by intent using explicit, reviewable rules
- Produces a short draft response for the reviewer to approve or edit
- Keeps the workflow human-in-the-loop: no automatic send, no silent model decisions
- Persists the current batch so a refresh or restart restores the review state

## Scope of the actual project
- Rule-based grouping and safe fallback behavior, with a deterministic decision path
- Intents: quest_status, schedule, salary, technical_issue, withdrawal, and other
- Review surface with batch persistence, item editing, status tracking, and export
- Gmail integration for fetching and sending approved replies in-thread
- React + FastAPI web app for reviewing and approving drafts

## Why this is the real submission
The older re_born folder is a prototype and reference point. The actual Quest work lives in reborn2: it is the project that includes the code, tests, UI, API, data, and logs used in the final submission.

## AI-first workflow used here
- Start with a concrete rule set, not a black-box model
- Make the behavior explainable and testable
- Iterate on edge cases and misclassifications before expanding the surface area
- Keep the human in the loop for every outbound message

## Primary run path
```bash
cd reborn2
python -m src.inbox_helper --csv data/messages.csv
python -m src.inbox_helper --csv data/messages.csv --output out.csv
```

## Quality bar
- Deterministic rules over hidden behavior
- Honest logs about what failed or misclassified
- Working code, readable tests, and a real review workflow
