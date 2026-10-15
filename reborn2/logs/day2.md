# Day 2 — reborn2 Pipeline build

- Goal: turn the idea into a real working pipeline with staged processing.
- Built the first pass of safety gating and deterministic message classification.
- Focused on reviewability: rules were explicit, not hidden in model output.
- Learned that ordering matters. Some ambiguous messages were misclassified unless withdrawal and technical issues were checked before generic labels.
- Added the first end-to-end run flow so the script could process a CSV and surface grouped results.
- Honest note: the first version felt “done” too soon; the real work was making edge cases explainable and testable.
