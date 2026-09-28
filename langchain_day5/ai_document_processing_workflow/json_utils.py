"""
json_utils.py
=============
A small, dependency-free helper for pulling a JSON object out of an LLM's
raw text response, tolerating markdown code fences or stray text around
it. Used by every agent node so parsing logic isn't duplicated five times.

Unlike the stricter JSON-contract assignments earlier in this series,
this workflow does NOT retry a malformed response against the model --
if parsing fails, the raw text is preserved under a "raw_response" key so
the pipeline can keep moving (a single flaky agent shouldn't take down
the whole document-processing run), and a warning is printed so the
failure is visible rather than silently swallowed.
"""

import json
import re
from typing import Any, Dict


def extract_json_object(raw_text: str) -> str:
    text = raw_text.strip()

    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    return text


def parse_agent_json(raw_text: str, agent_name: str) -> Dict[str, Any]:
    """Parses an agent's raw LLM output as JSON. On failure, prints a
    warning and returns {"raw_response": raw_text} instead of raising, so
    one agent's bad output doesn't crash the whole workflow."""
    candidate = extract_json_object(raw_text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        print(
            f"  [WARNING] {agent_name}: could not parse JSON output ({exc}). "
            f"Falling back to raw text for this agent's result."
        )
        return {"raw_response": raw_text}
