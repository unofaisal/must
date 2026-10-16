# Day 3 (Oct 14)

I added a test message, "Deadline is close but login failed and I can't open the page", and it came out as `other`. It is really two things, a deadline extension and a technical problem, and my six intents had no place for either. That pushed the list to ten: technical issue, deadline extension, submission or documents, and thanks or acknowledgement joined the original six. Every intent is read for every message now. In practice that is ten yes/no questions sent to the decision model in one request, next to the three safety questions in another, so adding an intent is one new question and one new template. `other` only appears when nothing scores.

The rest of the day was about making it usable by someone who isn't me:

- Templates for the four new intents, and a fallback to the template when the model gives a blank reply.
- One shared path for processing a message, used by both the CLI and the new API, so they can't drift apart.
- A FastAPI backend for review: upload, edit a draft, approve, reject, send. The rules live in the API, not just the screen. You can't approve an empty draft or one with placeholders left in it, and you can't send something that isn't approved.
- A first React screen for reviewing, written in plain JavaScript.

The model ran the tests after each change and fixed its own failures before I looked.
