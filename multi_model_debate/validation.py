"""
validation.py
==============
Parsing and validation logic, kept separate from both the API client and
the orchestration loop. Two kinds of checks are performed on every model
turn:

1. Structural validation -- does the output match the required JSON
   schema (right fields, right types, right cardinality)?
2. Relevance validation -- does the response actually engage with the
   user-provided topic, rather than drifting off-topic?

Relevance checking here uses a cheap lexical-overlap heuristic (no extra
API calls, no external NLP dependencies). It intentionally errs toward
being permissive -- see `validate_relevance` docstring for why, and how
to swap in a stricter model-based judge if your use case needs one.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

# A small stopword list -- enough to strip common function words for a
# lexical-overlap heuristic. Not intended to be linguistically complete.
_STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or", "but",
    "is", "are", "was", "were", "be", "been", "being", "this", "that", "these",
    "those", "it", "its", "as", "by", "with", "from", "about", "into", "over",
    "after", "before", "than", "then", "so", "such", "not", "no", "do", "does",
    "did", "have", "has", "had", "will", "would", "should", "could", "can",
    "may", "might", "must", "if", "we", "you", "they", "i", "he", "she",
}


class LLMResponseValidationError(Exception):
    """Raised when a model's output cannot be parsed as JSON at all."""


def extract_json_object(raw_text: str) -> str:
    """Strips markdown fences / surrounding prose to isolate a JSON object."""
    text = raw_text.strip()

    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    return text


def parse_llm_json(raw_text: str) -> Dict[str, Any]:
    candidate = extract_json_object(raw_text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMResponseValidationError(
            f"Model output was not valid JSON: {exc}. Raw output (truncated): {raw_text[:300]}"
        ) from exc


def _word_count(text: str) -> int:
    return len(text.split())


def validate_turn_schema(data: Any) -> List[str]:
    """Validates a single discussion turn: {"response": str, "key_points": [str, ...]}."""
    problems: List[str] = []

    if not isinstance(data, dict):
        return [f"Turn output must be a JSON object, got {type(data).__name__}."]

    expected_fields = {"response", "key_points"}
    missing = expected_fields - data.keys()
    extra = data.keys() - expected_fields
    if missing:
        problems.append(f"Missing required field(s): {', '.join(sorted(missing))}.")
    if extra:
        problems.append(f"Unexpected extra field(s): {', '.join(sorted(extra))}.")

    response = data.get("response")
    if not isinstance(response, str) or not response.strip():
        problems.append("'response' must be a non-empty string.")
    elif _word_count(response) < 15:
        problems.append("'response' is too short to be substantive (fewer than 15 words).")

    points = data.get("key_points")
    if not isinstance(points, list) or not all(isinstance(p, str) and p.strip() for p in points):
        problems.append("'key_points' must be a list of non-empty strings.")
    elif not (2 <= len(points) <= 5):
        problems.append(f"'key_points' must contain 2-5 items (found {len(points)}).")

    return problems


def validate_synthesis_schema(data: Any) -> List[str]:
    """Validates the final synthesis step: {"conclusion": str}."""
    problems: List[str] = []

    if not isinstance(data, dict):
        return [f"Synthesis output must be a JSON object, got {type(data).__name__}."]

    if "conclusion" not in data:
        problems.append("Missing required field: 'conclusion'.")
    else:
        conclusion = data.get("conclusion")
        if not isinstance(conclusion, str) or not conclusion.strip():
            problems.append("'conclusion' must be a non-empty string.")

    extra = set(data.keys()) - {"conclusion"}
    if extra:
        problems.append(f"Unexpected extra field(s): {', '.join(sorted(extra))}.")

    return problems


def _significant_words(text: str) -> set:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def validate_relevance(topic: str, response_text: str, min_overlap_ratio: float = 0.12) -> Tuple[bool, float]:
    """
    Cheap lexical-overlap relevance check: what fraction of the topic's
    significant words show up somewhere in the response text?

    This is deliberately a heuristic, not a semantic judgment -- it will
    not catch a response that is topically "on-brand" but factually
    unrelated, and it may occasionally flag a genuinely relevant response
    that simply paraphrases the topic heavily. It is meant as a cheap
    guardrail against gross topic drift (e.g. the model ignoring the
    topic and answering something else entirely), not as a substitute for
    human review.

    To upgrade this to a semantic check, replace this function's body
    with a small extra LLM call that asks a model
    ("Is this response about topic X? yes/no") and returns its verdict --
    the orchestrator only cares that this function returns (bool, float).

    Returns (is_relevant, overlap_ratio).
    """
    topic_words = _significant_words(topic)
    if not topic_words:
        # Degenerate topic (e.g. all stopwords/short words) -- can't meaningfully
        # judge relevance, so don't penalize the model for it.
        return True, 1.0

    response_words = _significant_words(response_text)
    overlap = topic_words & response_words
    ratio = len(overlap) / len(topic_words)

    return ratio >= min_overlap_ratio, ratio
