# What I unlearned

**Researching integrations myself.** I used to read the docs for a service, copy the relevant parts and paste them into my prompt. This time I told the model to go and read the documentation itself, for OpenRouter and for Gmail among others, and build from that. It saves the copy-paste work, and the model reads the whole page instead of the slice I picked. The Gmail case also showed the limit: it read the docs and still built the version that needed an organisational Google account, and I only found that out when I tried to use it. So I still check what it builds against my real situation.

**Decisions from text.** For the checks that gate everything, safety and grouping, I used decision models instead of a chat model. A decision model takes the message and yes/no questions and returns a probability for each, never text. There is no free text to parse and no wording to second-guess: my code reads a number and applies a threshold I can see and test. It also changed what "the model failed" means. A wrong-typed or missing answer is an error to handle (quarantine, or fall back to keyword scores), never a value to guess. The chat model is left with the one job that needs words, the draft.

**Checking code by hand.** Code is a verifiable task, so I stopped being the one to verify it. The model writes tests with each change, runs them and fixes its own failures. I read the result and decide whether it's right. My checking moved from "does this line work" to "is this the right thing to test", which is where it was more useful.

**Doing git by hand.** I let the model commit, push and pull. I don't type those commands any more. The cost is that the history is the model's idea of a good grouping: several commits can land seconds apart, so the log shows what was built but not the order I worked in. That's why the daily logs here are written separately.

**Starting with code.** I used to open an editor and start building. Now I start by giving the model rich context about what I'm trying to do and letting it ask me clarifying questions until we agree on the goal. The intent and the directive came out of that conversation. It changed the shape of the work: the early decisions (a human approves everything, nothing breaks if the model fails) were settled before any code existed and never moved.

**What I haven't fixed.** I still tend to build a version, then replace it. The review screen was written twice, and the first one is still lying around.
