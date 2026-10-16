# Demo script (5 minutes)

Start the backend with `DEMO_DELAY_MS=400` and the web app, and open the home screen. Everything works offline.

- **0:00** Say what it is: messages in, grouped, drafted, and a person approves every reply.
- **0:20** Press **Try the sample inbox**: 42 messages from 30 candidates.
- **0:30** Pipeline screen: safety, grouping, drafting, review. Click an email to see the scores behind each decision.
- **1:15** Upload the unsafe demo file. Two rows are held with no draft (one gives the assistant instructions, one asks about another candidate), and the third gets a normal draft.
- **1:45** Review screen: messages grouped by topic. Show one with two labels and explain the strongest is the main one.
- **2:15** Edit a draft and approve it. Then try approving one with a `[placeholder]` left in it and show it being refused.
- **3:00** Gmail: fetch by subject keyword from a test mailbox and send one approved reply in-thread. Don't use a real candidate inbox, and don't show past work from Gmail, it has real addresses.
- **3:40** Run the tests and show them passing.
- **4:15** Show the daily logs and the unlearning note.
- **4:45** Finish on the Known Issues in the README: what's still open, said plainly.
