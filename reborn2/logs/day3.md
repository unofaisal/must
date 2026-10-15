# Day 3 — reborn2 Grouping and drafting

- Expanded the classifier from a single label to a multi-stage pipeline: safety, grouping, drafting.
- Reworked grouping around confidence and rule precedence so one message could map to the most likely intent without becoming opaque.
- Added draft templates that were short, human-readable, and safe by default.
- Kept every reply flagged for manual review instead of pretending automation was final.
- Added test coverage around the intent logic and the full run pipeline to catch regressions.
- Honest note: the main failure mode was overconfidence. A “good enough” classifier was not enough; we needed explainable rules and conservative fallback behavior.
