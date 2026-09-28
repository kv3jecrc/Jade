# AI Document Processing Workflow

A LangGraph-based multi-agent workflow that processes a Software
Requirement Specification (SRS) document and produces a structured,
human-reviewed final report.

## Workflow graph

```
Input SRS
    |
    v
Document Analyzer
    |
+---+---+
|       |
v       v
Requirement  Risk
  Agent      Agent
    |         |
    v         v
Architecture  Test Case
  Agent        Agent
    |         |
    +----+----+
         |
         v
   Merge Results
         |
         v
  Human Review (HITL)
         |
         v
    Final Report
```

- **Document Analyzer** reads the raw SRS text and produces a structural
  summary (overview, key modules, stated goals).
- **Requirement Agent** and **Risk Agent** run in the same LangGraph
  superstep — a genuine parallel fan-out from Document Analyzer, not a
  sequential simulation. Both edges originate from the same node, so
  LangGraph schedules them together.
- **Architecture Agent** (built from the Requirement Agent's output) and
  **Test Case Agent** (built from the Risk Agent's output) likewise run
  in parallel.
- **Merge Results** is a pure-Python aggregation node (no LLM call) that
  only runs once *both* Architecture Agent and Test Case Agent have
  completed — LangGraph waits for all incoming edges of a node before
  scheduling it, giving a true fan-in.
- **Human Review** calls LangGraph's `interrupt()`, which genuinely
  pauses graph execution and persists state via the compiled graph's
  checkpointer. The process can exit entirely at this point; resuming
  later (via `Command(resume=...)`) re-enters this exact node with the
  human's decision, without re-running any of the four analysis agents
  that already completed. This is verified by the test script (see
  below) — it asserts none of the earlier agents are called a second
  time after resume.
- **Final Report** is an LLM call that synthesizes the merged analysis
  plus the human reviewer's decision into a stakeholder-readable report
  (title, executive summary, full report body).

## Design decisions / assumptions

- **Merge Results has no LLM call.** Combining five agents' already-
  structured JSON outputs into one dict is a deterministic operation;
  spending an LLM call on it would add latency, cost, and a new failure
  mode for no benefit. Final Report is the one place narrative synthesis
  happens, once the human has had a chance to weigh in.
- **Non-retrying JSON parsing.** `json_utils.parse_agent_json()`
  extracts and parses each agent's JSON response, but if parsing fails
  it does **not** retry the LLM call — it logs a warning and falls back
  to `{"raw_response": <text>}`, so one flaky agent doesn't take down
  the whole multi-agent run. This is a deliberate difference from the
  stricter, retry-until-valid JSON contracts used in earlier assignments
  in this series, appropriate here because losing one agent's structured
  fields still leaves a usable (if degraded) report.
- **Prompt templates use `<<placeholder>>` + `.replace()`, not
  `str.format()`.** Every agent prompt embeds a literal JSON schema
  example (e.g. `{"summary": "...", ...}`) to show the model exactly
  what to return. `str.format()` would try to interpret those literal
  braces as its own placeholders and raise `KeyError`. `prompts.fill()`
  does plain string substitution instead, sidestepping the collision
  entirely. See `prompts.py`'s module docstring.
- **Human decision is free text** (`"approved"`, `"revise: <what to
  change>"`, etc.), passed straight into the Final Report prompt so the
  report's closing note can reflect it. No fixed enum is enforced, since
  the assignment doesn't specify one and free text is more informative
  for a stakeholder-facing report.
- **`MemorySaver` checkpointer.** Keeps state in process memory, which
  is enough to prove the pause/resume mechanism genuinely works. A real
  deployment where the pause might outlive the process should swap in a
  persistent checkpointer (e.g. SQLite or Postgres) — the rest of the
  graph is unaffected, since checkpointing is decided entirely by
  `build_graph()`'s `graph.compile(checkpointer=...)` call.

## Setup

```bash
pip install -r requirements.txt --break-system-packages
```

Default provider is a local Ollama model (to work around corporate IT
blocks on external SaaS API keys, per the established convention in this
assignment series). Configure via a `.env` file if you want to override
defaults or switch provider — see `llm_setup.py`'s docstring for the
full list of variables (`LLM_PROVIDER`, `OLLAMA_MODEL`,
`OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.). No API
keys are hardcoded anywhere in this repo.

## Running

```bash
# Interactive: pauses at Human Review and prompts for your decision
python main.py --file sample_srs.txt

# Non-interactive: supply the human decision up front
python main.py --file sample_srs.txt --human-feedback "approved"
python main.py --file sample_srs.txt --human-feedback "revise: tighten the security NFR"

# Save the full final state (including all intermediate agent outputs) to a file
python main.py --file sample_srs.txt --human-feedback "approved" --output result.json
```

`sample_srs.txt` is a sample SRS for a "Campus Library Management
System" used as the default input.

## Testing / verification honesty note

This sandbox has no reachable Ollama server, no GPU, and no network
access to external LLM providers, so the workflow could not be
end-to-end tested against a real model here. What **was** verified,
using a fake LLM that returns fixed, valid JSON per agent (swapping out
`workflow._call_agent`):

- The `prompts.fill()` substitution no longer collides with the literal
  JSON braces in each prompt (this was an actual bug caught during
  development — see below).
- Requirement Agent and Risk Agent are called in the same parallel
  superstep, confirmed via call-order tracking against Architecture
  Agent / Test Case Agent (which must run strictly after their
  respective upstream agent).
- Merge Results only runs after both Architecture Agent and Test Case
  Agent have completed, and its `merged_report` contains all five
  agents' structured outputs.
- Execution genuinely pauses before Final Report: `app.get_state()`
  reports `next == ("human_review",)`, `final_report` is absent from
  state, and the interrupt payload carries the expected `message` and
  `merged_report` keys.
- Resuming via `Command(resume={"decision": ...})` produces a
  `final_report` with the expected structure, and — critically — none
  of Document Analyzer, Requirement Agent, Risk Agent, Architecture
  Agent, or Test Case Agent are called again after resume, confirming
  the checkpointer is genuinely preserving state across the pause
  rather than the "pause" being cosmetic.

What was **not** verified (needs real infrastructure): actual LLM output
quality/accuracy for a given SRS, behavior under a genuinely malformed
(non-JSON) LLM response in production conditions, and multi-process /
restart durability of the pause (this sandbox only exercises `interrupt`
within a single process using `MemorySaver`; a persistent checkpointer
would need its own test against a real datastore).

### Bugs caught and fixed during development

1. **Node/state-key name collision.** LangGraph raised
   `ValueError: 'final_report' is already being used as a state key`
   when a node was also named `"final_report"` (the state's `TypedDict`
   already has a `final_report` field). Fixed by naming the node
   `"generate_final_report"` instead, leaving the state key untouched.
2. **`.format()` vs. literal JSON braces.** Described above under
   "Design decisions" — fixed by switching prompt templates to
   `<<placeholder>>` markers filled via a custom `fill()` function.
