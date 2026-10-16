# Inbox Helper

Takes a pile of candidate messages, groups each one by what the person wants, and drafts a short reply. A person approves every reply before anything is sent. It works fully offline with no API key; a key makes the grouping and drafting smarter.

## Run it

Needs Python 3.12 and Node 18+.

```bash
cd reborn2

# command line
python -m src.inbox_helper --csv data/messages.csv
python -m src.inbox_helper --csv data/messages.csv --output out.csv
python -m src.inbox_helper --csv data/messages.csv --live      # uses a model, needs a key

# review app
pip install -r requirements.txt
uvicorn api.main:app --reload          # backend on :8000
cd web && npm install && npm run dev   # app on :5173

# tests
pip install -r requirements-dev.txt
python -m pytest -q
```

In the app, press **Try the sample inbox** on the home screen. To see the pipeline run, start the backend with `DEMO_DELAY_MS=400`. The sample has no unsafe messages, so upload `data/demo_unsafe.csv` to see the safety check hold two of its three rows.

## How it works

Each message goes through three steps, and each one falls back instead of failing.

1. **Safety check.** Catches messages that try to instruct the assistant, ask about another candidate, or come from someone angry or distressed. These are held back with no draft for a person to handle.
2. **Grouping.** Ten intents plus `other`, each scored from 0 to 1. A message can belong to several groups; the strongest is the main one.
3. **Drafting.** A short reply with `[placeholders]` for anything it doesn't know. Templates are used offline or if the model fails.

Intents: status update, reschedule, hiring process, pay or contract, withdrawal, feedback, technical issue, deadline extension, submission or documents, thanks or acknowledgement.

## Decision models

The safety check and the grouping don't ask a chat model to write an answer. They use a decision model (OpenRouter's decisions endpoint). It gets the message plus yes/no questions and returns a probability for each, typed and never free text, and the code applies the thresholds: 0.8 to quarantine, 0.5 for an intent to count. Each message costs two decision calls, three safety questions and then ten intent questions. Because the answers are typed, an unexpected one is treated as an error: the safety check quarantines, and grouping falls back to keyword scoring for that message.

Drafting is the only step where a chat model writes text. Set the key in Settings (or `OPENROUTER_API_KEY`); the decision model and the chat model are separate settings and either can be swapped. With no key, keyword counts stand in for the decision model and templates for the chat model.

## Review

You can't approve a draft that is empty or still has a placeholder, editing an approved draft cancels the approval, and only approved replies can be sent. In the review screen: `J`/`K` to move, `A` approve, `S` send, `X` reject. Messages from Gmail are replied to in the original thread after a confirmation. So are CSV rows that include a `message_id` or `thread_id`, as long as the server is connected to Gmail. For all other CSV rows, send opens your mail app and you mark it as sent afterwards.

## Gmail

It uses the regular Gmail API with your own Google login, so a personal account works. (Google's Gmail MCP server needs an organisational account to register, so it isn't used.)

One-time setup in Google Cloud:
1. Create a project and enable the **Gmail API**.
2. Set up the OAuth consent screen as External, add your Gmail as a test user, and add the `gmail.readonly` and `gmail.compose` scopes.
3. Create an OAuth client of type **Web application** with the redirect URI `http://localhost:8000/api/gmail/callback` or you hosted domain address.

Then in Settings, paste the client ID and secret, press **Connect Gmail** and allow access. While the Google app is in testing mode the login expires after about a week, so connect again when that happens. To fetch, use "Or pull from Gmail" on the home screen: keywords, optional dates, up to 100 messages.

## Saved data

The open batch is saved after every edit and finished batches are kept in a history (newest 50) you can reopen from the app. Settings and Google credentials are stored locally and ignored by git. There is no database.

## Tests

The tests cover safety, grouping, drafting, the model providers, the pipeline and CLI, the sample data, the API and Gmail. The Gmail tests use a fake Gmail, so no Google account is needed.


## Documents

`intent.md`, `Final directive.md`, `logs/` for each day, and `docs/unlearned.md`.
