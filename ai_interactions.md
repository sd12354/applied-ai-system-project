# AI Interactions Log

> Optional stretch documentation. My primary graded responsible-AI
> reflection is in `model_card.md` (Section 10).

---

## Agentic Workflow (SF8)

**What task did you give the agent?**

Extend my Module 3 Music Recommender into a full applied-AI system: a
natural-language planner, a self-checking agent loop, a confidence score,
a reliability harness, tests, logging, and the required docs/diagram.

**Prompts used (summarized):**

- "Build off the Module 3 recommender — add an agentic plan/act/check/revise
  loop with natural-language input, confidence scoring, and guardrails."
- "Make the self-correction meaningful and keep it reproducible without an
  API key."
- "Add a reliability harness that writes a parseable report, and tests for
  each component."

**What did the agent generate or change?**

New modules `src/planner.py`, `src/evaluator.py`, `src/agent.py`, the
`src/evaluate.py` harness, `src/main.py` CLI, tests for planner/evaluator/
agent, the Mermaid architecture diagram, and the execution-evidence files
in `assets/`. The Module 3 scoring core (`src/recommender.py`) was left
unchanged.

**What did you verify or fix manually?**

I ran `pytest` and `python -m src.evaluate` after each step and read the
agent logs. The main fix I directed was the confidence design: the first
version normalized only against specified dimensions, which made vague
requests look overconfident, so I changed it to a fixed full-match ceiling
(see model_card Section 10).

---

## Design Pattern (SF10)

**Which design pattern did you use?**

A lightweight **Strategy / pipeline** split: planner → recommender →
evaluator are independent components the agent orchestrates, and the two
scoring interfaces share one `_score` helper so they can't drift.

**How does the pattern appear in your final code?**

`src/agent.py` owns the control loop and calls into each component through
its public function, so any one of them (e.g. swapping the rule-based
planner for an LLM planner) can be replaced without touching the others.
