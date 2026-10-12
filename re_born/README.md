# re_born — Stall Alerter (Quest Option C)

Reads a hiring-board CSV, finds candidates stalled ≥ N days, ranks who to follow up first.

## Run (stdlib only, Python 3.10+)

```bash
cd re_born
python -m src.stall_alerter --csv data/hiring_board.csv --days 7
# deterministic demo:
python -m src.stall_alerter --csv data/hiring_board.csv --days 7 --today 2026-10-12
# save to file:
python -m src.stall_alerter --csv data/hiring_board.csv --days 7 --output out.csv
```

## Test

```bash
python -m pytest -q
```

## Files
- `src/stall_alerter.py` — core + CLI
- `data/hiring_board.csv` — sample data (12 rows, mixed stalls)
- `tests/test_stall_alerter.py` — 7 tests
- `intent.md` — day-1 intent
- `Final directive.md` — frozen spec
- `logs/day1.md` … `day5.md` — daily log
- `docs/unlearned.md` — one-page unlearning note
