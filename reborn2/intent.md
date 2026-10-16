# Intent

I'm building the inbox helper (option A). It takes a pile of candidate messages, groups them by what each person wants, and drafts a short reply for each one. A person reads and approves every draft before anything is sent.

## Starting point
A small offline classifier: six intents, keyword rules, one template reply per intent, run from the command line. I wanted something I could read and test before adding a model.

## Where it ended up
The aim stayed the same and the build grew. The safety check and the grouping are done by a decision model: it answers yes/no questions with a probability, not text, and my code applies the thresholds. The keyword rules are the fallback when there's no key or the model fails. A chat model is only used to write the draft. A safety check runs first and holds back anything suspicious. There are ten intents. It has a review app, saved sessions and history, and it can read from and reply through Gmail.

## What doesn't change
- Nothing is sent unless a person approved it.
- If the model fails, the tool still works: rules for grouping, templates for drafting, and quarantine for the safety check.
- Anything unclear stays in front of a human instead of being guessed.
- It runs with no API key, so the tests and the demo need no network.

## Out of scope
Auto-sending, learning from replies, user accounts, a database, and deploying anywhere but my own machine.

## How I'm working
I give the model a lot of context and let it ask me questions until we agree, then build one stage at a time. It writes and runs its own tests. I make the work harder each day and write down what breaks, in the daily logs.
