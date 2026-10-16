# Day 4 (Oct 15)

The biggest jump so far: from a script to something with real state and a real mailbox.

**Running and saving.** Processing now runs as a background job with progress for each stage, so the screen shows the pipeline working. The open batch is saved after every edit, finished batches go to a history you can reopen, and settings (key, the decision model and the chat model, custom drafting instructions) are stored too, with a check button that tests the key and both models. Approved replies can be exported.

**Gmail.** This is where the model's first attempt didn't work. Wiring Gmail for the first time, it built the integration on Google's Gmail MCP server. That route needs an organisational email to register in Google's developer program, and I'm on a personal account, so it could never work for me. We rewrote it on the regular Gmail API with Google login. It fetches by subject keywords and dates, one message per thread, skips my own sent mail, and replies inside the original thread only after approval. At first a CSV upload could not trigger an in-thread Gmail send, but we later added support so CSV rows including `message_id` or `thread_id` are treated as Gmail-origin and can be replied to in-thread when the server is connected to Gmail. The tests run against a fake Gmail, so the real flow was only exercised by hand.

**The screen.** The JavaScript UI became a TypeScript app: Home, Pipeline, Review, Past work and Settings.

What broke: making upload asynchronous broke a test that still expected the result straight away.
