# Multi-Model Adversarial Reasoning System

Orchestrates a structured proposal → critique → revision → evaluation
cycle between two company-hosted LLMs (Model A = proposer/defender,
Model B = adversarial critic) on a user-supplied scenario, and returns a
single strictly-valid JSON result.

## Module layout (separation of concerns, as required)

| File              | Responsibility |
|--------------------|----------------|
| `config.py`         | Loads Model A / Model B configuration (base URL, key, model name) from env vars; orchestration settings (retry counts, relevance threshold). |
| `llm_client.py`     | API client layer — `LLMClient.call()` talks HTTP to a model's endpoint, with retry/backoff. Also a `MockLLMClient` for testing without credentials. One instance per model. |
| `prompts.py`        | All prompt text/templates for each turn (proposal, critique, revision, evaluation) plus the corrective re-prompt template. No API or validation logic. |
| `validation.py`     | JSON parsing, per-turn (role-specific) schema validation, and a topic-relevance heuristic. No API or prompting logic. |
| `orchestrator.py`   | Ties it together: runs the 4-step cycle, retries a turn with a corrective prompt when validation fails, logs everything, and reports pass/fail. |
| `main.py`           | CLI entry point. |

## Assumption about the API contract

Each model's `base_url` is assumed to expose an OpenAI-compatible
`POST {base_url}/chat/completions` endpoint (the common shape for
internal LLM gateways). Only `llm_client.py` needs to change if either
company gateway uses a different contract — Model A and Model B can even
use *different* contracts, since each gets its own `LLMClient` instance.

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
python main.py --input "We should require all employees to return to office 5 days a week."

# Save result to a file
python main.py --input "..." --output result.json

# Print full prompts/responses to console as well as the log file
python main.py --input "..." --verbose

# Test the whole pipeline without any real API credentials
python main.py --input "We should adopt a four-day work week across the company." --mock
```

Every run also writes a full log (prompts, raw model outputs, retries,
validation failures) to `adversarial_reasoning.log` (configurable via
`ADVERSARIAL_LOG_FILE`), regardless of `--verbose`.

## The reasoning cycle

1. **Turn 1 — Model A proposal**: given the scenario, generates an
   initial solution/position with reasoning.
2. **Turn 2 — Model B critique**: given the scenario and Model A's
   proposal, stress-tests it — weaknesses, risks, edge cases,
   counterarguments.
3. **Turn 3 — Model A revision**: given the scenario, its own proposal,
   and Model B's critique, revises or defends its position, addressing
   the specific points raised.
4. **Turn 4 — Final evaluation**: a final orchestration call (to Model A)
   judges the *revised* proposal's robustness and names remaining risks —
   deliberately not just a positive rubber stamp.

Each turn has its own role-specific JSON schema (not one generic shape),
so the structure itself reflects what that turn is supposed to produce:

- Proposal: `{"proposal": str, "key_reasoning_points": [str, ...]}`
- Critique: `{"critique": str, "identified_weaknesses": [str, ...]}`
- Revision: `{"revised_response": str, "changes_made": [str, ...]}`
- Evaluation: `{"robustness_summary": str, "remaining_risks": [str, ...]}`

(each list field: 2–5 short phrases, not full sentences)

## Final output schema

```json
{
  "original_input": "string",
  "model_a_initial_proposal": {"proposal": "string", "key_reasoning_points": ["string", "..."]},
  "model_b_critique": {"critique": "string", "identified_weaknesses": ["string", "..."]},
  "model_a_revised_response": {"revised_response": "string", "changes_made": ["string", "..."]},
  "final_evaluation": {"robustness_summary": "string", "remaining_risks": ["string", "..."]}
}
```

On failure, the CLI prints `{"success": false, "error": "..."}` and exits
with status 1, instead of raising an unhandled exception.

## How correctness is enforced, per turn

1. **Schema validation** (`validation.py`): each turn's specific required
   fields must be present with no extras, the main text field must be
   non-empty and substantive (minimum word count), and the list field
   must contain 2–5 non-empty short-phrase strings.
2. **Relevance validation** (`validation.validate_relevance`): a cheap
   lexical-overlap heuristic checks that a meaningful fraction of the
   original scenario's significant words appear in each turn's response,
   to catch gross topic drift. This is intentionally a heuristic, not a
   semantic judgment — see the docstring in `validation.py` for its
   limits and how to swap in a model-based relevance judge if you need
   something stricter. The final evaluation step skips this check since
   it legitimately discusses the critique/revision rather than restating
   the scenario.
3. **Self-correction retries**: if either check fails, the specific
   problem list is sent back to the *same* model as a follow-up message
   asking it to fix that exact issue (`max_correction_attempts`, default
   2 extra tries per turn).
4. **Network resilience**: each model's client independently retries
   timeouts/connection errors/5xx responses with exponential backoff;
   4xx errors and misconfiguration (e.g. missing `base_url`) fail fast
   without retrying, but are still caught and reported as a clean
   `success: false` result rather than crashing.
5. **Graceful failure**: if a turn can't be salvaged after retries, or
   either model's API is unreachable, `run()` returns
   `ReasoningResult(success=False, error=...)` with a clear error message
   identifying which turn and why.

## Testing without real credentials

```bash
python main.py --input "We should adopt a four-day work week across the company." --mock
```

`MockLLMClient` returns canned, schema-conforming responses for both
models, matched to a four-day-work-week scenario specifically (since the
canned text is static, not genuinely generated). Using `--mock` with an
unrelated scenario will correctly trigger the relevance-check retry path
— that's the validator doing its job, not a bug.
