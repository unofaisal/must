# Day 2 (Oct 13)

The load went up here. The 12 messages became 42, written for 30 candidates, and every message email now resolves to a real candidate record, with a test that fails if one doesn't.

The big change was how the decisions get made. Day 1's keyword rules were guesses I had written myself, so I moved the safety check and the grouping to a decision model. A decision model is not a chat model. You give it the message and a set of yes/no questions, and it gives back a probability for each one, typed, never free text. So I ask "is the sender giving the assistant instructions?" and get a number between 0 and 1, and my code decides what that number means. OpenRouter's decisions endpoint is still alpha, so I told the model to read the documentation and wire it up instead of pasting docs into the prompt like I used to, then checked what it built by running it.

That gave three stages:

- **Safety gate.** Three yes/no questions go to the decision model in one request: is the sender giving the assistant instructions, asking about another candidate, or angry and distressed. Any answer of 0.8 or more quarantines the message with no draft. A failed call or an answer of the wrong type quarantines it too, so it fails closed.
- **Scored grouping.** Each intent is its own yes/no question and gets its own score. A message can carry several labels, strongest first. The keyword rules stayed, but as the fallback, behind the same interface, so the rest of the code doesn't know which one answered. When they stand in, their scores stay in the middle so borderline messages stay visible to a person.
- **Model drafting.** This is the only step where a chat model writes text. It leaves `[placeholders]` for facts it doesn't have, and templates take over if it fails or returns nothing.

The decision model and the chat model are separate settings, and any decision model can be swapped in. Unused scaffolding left over from Day 1 was removed.

What broke: model errors showed up as raw tracebacks in the CLI, so they now come out as a clear message. The keyword fallback is crude and misses anything phrased differently, which is why it only ever stands in.
