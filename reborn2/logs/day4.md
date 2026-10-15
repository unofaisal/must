# Day 4 — reborn2 Review backend

- Built the FastAPI review surface so the project moved from CLI-only into a real inbox helper workflow.
- Added batch persistence, CSV upload, item patching, approval state, and export for approved drafts.
- Logged every stage to session JSON and history files so a refresh or restart would restore the human review state.
- Broke work into components: backend logic, app API, and storage, instead of keeping everything in one script.
- Verified the flow with tests and learned that persistence bugs are easy to miss unless you rebuild the session from disk.
- Honest note: I had to unlearn the instinct to keep everything in memory only; the real workflow depends on durable state.
