# re_born — Quest Submission (Option C: Stall Alerter)

## Intent (Day 1)
Build a small, AI-first tool that reads a hiring-board CSV, finds stalled candidates, and tells a recruiter who to follow up first and what to do.

**Why C:** Deterministic, testable, demoable in 5 min, directly useful to MUST hiring flow. No external API needed — runs offline.

## Scope (5 days)
- Day 1: intent.md + scaffold + sample CSV
- Day 2: core logic (parse CSV, compute days-stalled, rank)
- Day 3: CLI + tests + README
- Day 4: raise load (edge cases, large file, bad dates) + video script
- Day 5: unlearned note + final polish + submission zip

## AI-first rules for this repo
1. Every non-trivial function is prompted, then reviewed.
2. Prompts + failures go in `logs/`.
3. Human reviews every output (like the inbox-helper human-in-loop principle).
4. Raise load each day — log what broke.

## Deliverables checklist
- [ ] intent.md (this file)
- [ ] Final directive.md
- [ ] Working code + README how to run
- [ ] logs/day1-5.md
- [ ] 5-min demo video + Loom link
- [ ] docs/unlearned.md (one page)

## Option C spec (my interpretation)
Input CSV columns: `candidate_id,name,stage,last_moved_date,owner,role`
- `stage`: e.g. Applied, Screen, Quest, HR, Paid Test, Offer
- `last_moved_date`: YYYY-MM-DD
- Flag if `days_stalled >= threshold` (default 7 days)
- Output: sorted by days_stalled desc, with `action` suggestion per stage + one-sentence `reason`
- Exit code 0 always; empty result = "no stalls"
