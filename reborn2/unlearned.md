# What I Unlearned: reborn2 (Inbox Helper, Option A)

The brief asked how much I would change the way I work, not how much I already know. This note is about how I used to build things and how I built this one.

## 1. Starting from code → starting from a written plan

**Before:** open the editor and work out what I'm building as I go.
**Now:** I write down the intent and a directive first: the goal, the exact input and output, the rules, and what it will not do. Then the model builds against that, not against whatever is in my head.
**Evidence:** `intent.md`, `Final directive.md`, `logs/day1.md`.

## 2. Reading the documentation myself → sending the model to get it

**Before:** I opened the docs, read them, and worked out which parts mattered before writing anything.
**Now:** I tell the model what I'm trying to do and point it at the documentation. It fetches the pages and pulls out what it needs to do the job. My time goes into deciding what I want, not into finding the right page.
**Evidence:** openrouter and the Gmail setup

## 3. Writing my own tests → letting the model write and run them

**Before:** I wrote the tests myself after the code, and sometimes skipped them.
**Now:** I don't write tests. I let the model write its own tests and run them, because a test passing or failing is a task it can verify by itself. I read the results and push back when something fails or looks too easy.
**Evidence:** `tests/` and the test runs in the logs.

## 4. Thinking the whole project through alone → thinking it through together

**Before:** I held the whole design in my head and decided everything on my own before anyone saw it.
**Now:** I brainstorm with the model from the start: options, trade-offs, what could go wrong. It widens what I consider, and I still make the call.