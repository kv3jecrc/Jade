# Multi-Model Interaction System

Orchestrates a structured discussion between two company-hosted LLMs
(Model A, Model B) on a user-provided topic, and returns a single
strictly-valid JSON result.

## Module layout (separation of concerns, as required)

| File              | Responsibility |
|--------------------|----------------|
| `config.py`         | Loads Model A / Model B configuration (base URL, key, model name) from env vars; orchestration settings (retry counts, relevance threshold). |
| `llm_client.py`     | API client layer — `LLMClient.call()` talks HTTP to a model's endpoint, with retry/backoff. Also a `MockLLMClient` for testing without credentials. One instance per model. |
| `prompts.py`        | All prompt text/templates for each turn and the synthesis step, plus the corrective re-prompt template. No API or validation logic. |
| `validation.py`     | JSON parsing, per-turn schema validation, and a topic-relevance heuristic. No API or prompting logic. |
| `orchestrator.py`   | Ties it together: runs the 4-step interaction, retries a turn with a corrective prompt when validation fails, logs everything, and reports pass/fail. |
| `main.py`           | CLI entry point. |

## Assumption about the API contract

As with the Article Analysis System, each model's `base_url` is assumed to
expose an OpenAI-compatible `POST {base_url}/chat/completions` endpoint
(the common shape for internal LLM gateways). Only `llm_client.py` needs
to change if either company gateway uses a different contract — Model A
and Model B can even use *different* contracts, since each gets its own
`LLMClient` instance.

## Configuration

```bash
pip install -r requirements.txt

export MODEL_A_BASE_URL="https://llm-a.internal.company.com/v1"
export MODEL_A_API_KEY="token-for-model-a"
export MODEL_A_MODEL="model-a-deployment-name"

export MODEL_B_BASE_URL="https://llm-b.internal.company.com/v1"
export MODEL_B_API_KEY="token-for-model-b"
export MODEL_B_MODEL="model-b-deployment-name"
```

## Usage

```bash
python main.py --topic "Should companies mandate return-to-office?"

# Save result to a file
python main.py --topic "..." --output result.json

# Print full prompts/responses to console as well as the log file
python main.py --topic "..." --verbose

# Test the whole pipeline without any real API credentials
python main.py --topic "Is remote work good for company culture and productivity?" --mock
```

Every run also writes a full log (prompts, raw model outputs, retries,
validation failures) to `multi_model_debate.log` (configurable via
`DEBATE_LOG_FILE`), regardless of `--verbose`.

## The interaction flow

1. **Turn 1 — Model A initial position**: given the topic, states a
   position/argument.
2. **Turn 2 — Model B critique**: given the topic and Model A's response,
   critiques, questions, or expands on it.
3. **Turn 3 — Model A rebuttal**: given the topic, its own initial
   response, and Model B's critique, replies directly to the critique.
4. **Turn 4 — Synthesis**: a final orchestration call (to Model A) that
   produces a short, neutral conclusion noting agreement, disagreement,
   and a practical takeaway.

Every turn's model output is required to be JSON:
`{"response": "...", "key_points": ["...", ...]}` (2–5 points), which is
what "enforce structured responses from both models" means here — each
individual turn is schema-checked, not just the final assembled object.

## Final output schema

```json
{
  "topic": "string",
  "model_a_initial_response": {"response": "string", "key_points": ["string", "..."]},
  "model_b_critique": {"response": "string", "key_points": ["string", "..."]},
  "model_a_final_reply": {"response": "string", "key_points": ["string", "..."]},
  "conclusion": "string"
}
```

On failure, the CLI prints `{"success": false, "error": "..."}` and exits
with status 1, instead of raising an unhandled exception.

## How correctness is enforced, per turn

1. **Schema validation** (`validation.validate_turn_schema` /
   `validate_synthesis_schema`): required fields present, no extra
   fields, `response` non-empty and reasonably substantive, `key_points`
   a list of 2–5 non-empty strings.
2. **Relevance validation** (`validation.validate_relevance`): a cheap
   lexical-overlap heuristic checks that a meaningful fraction of the
   topic's significant words appear in the response, to catch gross
   topic drift. This is intentionally a heuristic, not a semantic
   judgment — see the docstring in `validation.py` for its limits and how
   to swap in a model-based relevance judge if you need something
   stricter (e.g. for regulatory/compliance use cases).
3. **Self-correction retries**: if either check fails, the specific
   problem list is sent back to the *same* model as a follow-up message
   asking it to fix that exact issue (`max_correction_attempts`, default
   2 extra tries per turn).
4. **Network resilience**: each model's client independently retries
   timeouts/connection errors/5xx responses with exponential backoff;
   4xx errors fail fast.
5. **Graceful failure**: if a turn can't be salvaged after retries, or
   either model's API is unreachable, `run_debate()` returns
   `DebateResult(success=False, error=...)` — the whole run fails
   cleanly with a clear error message identifying which turn and why,
   rather than a partial or corrupted result.

## Testing without real credentials

```bash
python main.py --topic "Is remote work good for company culture and productivity?" --mock
```

`MockLLMClient` returns canned, schema-conforming responses for both
models (matched to that specific topic, since the canned text is about
remote work) so you can exercise the full orchestration, validation, and
CLI/logging plumbing before pointing at real endpoints. Using `--mock`
with an unrelated topic will correctly trigger the relevance-check retry
path, since the canned responses won't lexically match a different topic
— that's the validator doing its job, not a bug.
