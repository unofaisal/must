# Day 4 — Raise the load (what broke)
- Load raised: 10k-row synthetic CSV + bad dates + future dates + missing column.
- Broke: parse crashed on "2026/10/01" format — decided to fail fast with clear error (no silent guess).
- Broke: future dates gave negative days — fixed to clamp 0.
- Honest: still no video; large-file run ~0.3s, fine.
