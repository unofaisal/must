# Final directive

This describes what the finished tool does.

## Input
- A CSV of messages (id, sender, subject, body, and optionally email), up to 500 rows. Emails are matched to a candidate record when there is one.
- Or Gmail: subject keywords, optional dates, up to 100, inbox only, one message per thread.
- An API key is optional. The decision model and the chat model are separate settings. Without a key, keyword rules stand in for the first and templates for the second.

## What happens to each message
1. **Safety check.** Three yes/no questions go to a decision model, which returns a probability for each rather than text: is the sender giving the assistant instructions, asking about another candidate, or angry or distressed. A score of 0.8 or more quarantines the message and no draft is written. If the call fails or an answer isn't the expected type, the message is quarantined too.
2. **Grouping.** Ten intents plus `other`, each a yes/no question to the decision model, scored from 0 to 1. Everything at 0.5 or above is kept, strongest first, and the strongest is the main group. If nothing reaches 0.5 it goes to `other`. If the model fails, keyword rules score that message instead.

   Intents: status update, reschedule, hiring process, pay or contract, withdrawal, feedback, technical issue, deadline extension, submission or documents, thanks or acknowledgement.
3. **Drafting.** The only step where a chat model writes text. It writes a reply of under 120 words, and puts `[placeholders]` where it lacks a fact. With no key, on failure or on a blank reply, a template for the main group is used.

## Review rules
A reply is pending, approved, rejected or sent.
- You can't approve an empty draft or one that still contains a placeholder.
- Editing an approved draft cancels the approval.
- Only an approved reply can be sent. There is no automatic sending.
- A quarantined message starts with no draft. A recruiter writes one, and it goes through the same rules.
- A message that came from Gmail is replied to in its original thread. A CSV row that includes a `message_id` or `thread_id` is treated the same way when the server is connected to Gmail. CSV rows without those ids are never sent through Gmail.
- For those other CSV rows, "send" opens the reply in the mail app and you mark it sent afterwards.

## Output
The grouped, drafted and reviewed list, an export of the approved replies as CSV, and a saved copy of every batch.

## Done when
- [x] It runs from the command line and from the web app, offline.
- [x] Safety, grouping, drafting, the API and Gmail have tests.
- [x] The README says how to run it.
- [x] There is a log for each day.
- [x] The full test suite passes.
