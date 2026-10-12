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
- `src/inbox_helper.py` — classifier + drafter + CLI
- `data/messages.csv` — 12 sample messages
- `tests/test_inbox_helper.py` — tests
- `intent.md`, `Final directive.md`, `logs/`, `docs/unlearned.md`
