# What I Unlearned (one page)

1. Dropped: writing code before the directive. Old habit was "code first, spec later."
   New way: froze Final directive.md first, then every prompt referenced it. Fewer rewrites.

2. Dropped: "senior = no prompts shown." Showed prompts, failures, rewrites in logs/.
   Example: kept the crashing date parser output, then the fix. Honesty > polish.

3. Dropped: manual edge-case hunting. Asked AI to attack the CSV (bad dates, future,
   missing cols, 10k rows), then I verified. Found 2 real bugs in 20 min.

4. Dropped: over-building. No DB, no web UI, no deps. Stdlib CLI that runs + tests.
   Human reviews every draft/action — same principle as Option A inbox helper.

5. Raise the load: Day 4 synthetic stress broke the parser; I logged it instead of hiding.
   One year into five: pressure + review loop beats coasting.

Stack: Python 3.10+, stdlib only, pytest for tests.
