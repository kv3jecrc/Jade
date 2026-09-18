"""
validation.py
==============
Parsing and validation logic, kept separate from the API client and the
orchestration loop. Two kinds of checks run on every turn:

1. Structural validation -- does the output match that turn's specific
   required JSON schema (proposal / critique / revision / evaluation each
   have their own field names and constraints)?
2. Relevance validation -- does the response actually engage with the
   user's original scenario, rather than drifting off-topic?

Relevance checking uses a cheap lexical-overlap heuristic (no extra API
calls, no external NLP dependencies). It intentionally errs toward being
permissive -- see `validate_relevance` docstring for why, and how to swap
in a stricter model-based judge if your use case needs one.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple

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


def _validate_text_and_list_fields(
    data: Any,
    text_field: str,
    list_field: str,
    min_text_words: int = 15,
    list_min: int = 2,
    list_max: int = 5,
) -> List[str]:
    """Shared shape check used by every turn's schema: one substantive text
    field plus one short-phrase list field, with no other fields."""
    problems: List[str] = []

    if not isinstance(data, dict):
        return [f"Turn output must be a JSON object, got {type(data).__name__}."]

    expected_fields = {text_field, list_field}
    missing = expected_fields - data.keys()
    extra = data.keys() - expected_fields
    if missing:
        problems.append(f"Missing required field(s): {', '.join(sorted(missing))}.")
    if extra:
        problems.append(f"Unexpected extra field(s): {', '.join(sorted(extra))}.")

    text_value = data.get(text_field)
    if not isinstance(text_value, str) or not text_value.strip():
        problems.append(f"'{text_field}' must be a non-empty string.")
    elif _word_count(text_value) < min_text_words:
        problems.append(f"'{text_field}' is too short to be substantive (fewer than {min_text_words} words).")

    list_value = data.get(list_field)
    if not isinstance(list_value, list) or not all(isinstance(p, str) and p.strip() for p in list_value):
        problems.append(f"'{list_field}' must be a list of non-empty strings.")
    elif not (list_min <= len(list_value) <= list_max):
        problems.append(f"'{list_field}' must contain {list_min}-{list_max} items (found {len(list_value)}).")

    return problems


def validate_proposal_schema(data: Any) -> List[str]:
    return _validate_text_and_list_fields(data, "proposal", "key_reasoning_points")


def validate_critique_schema(data: Any) -> List[str]:
    return _validate_text_and_list_fields(data, "critique", "identified_weaknesses")


def validate_revision_schema(data: Any) -> List[str]:
    return _validate_text_and_list_fields(data, "revised_response", "changes_made")


def validate_final_evaluation_schema(data: Any) -> List[str]:
    return _validate_text_and_list_fields(
        data, "robustness_summary", "remaining_risks", min_text_words=10
    )


def _significant_words(text: str) -> set:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def validate_relevance(user_input: str, response_text: str, min_overlap_ratio: float = 0.10) -> Tuple[bool, float]:
    """
    Cheap lexical-overlap relevance check: what fraction of the user
    scenario's significant words show up somewhere in the response text?

    This is deliberately a heuristic, not a semantic judgment -- it will
    not catch a response that stays "on-brand" but is factually unrelated,
    and it may occasionally flag a genuinely relevant response that
    paraphrases the scenario very heavily. It's a cheap guardrail against
    gross topic drift, not a substitute for human review.

    To upgrade this to a semantic check, replace this function's body with
    a small extra LLM call ("Is this response about scenario X? yes/no")
    and return its verdict -- callers only care that this returns
    (bool, float).

    Returns (is_relevant, overlap_ratio).
    """
    input_words = _significant_words(user_input)
    if not input_words:
        return True, 1.0

    response_words = _significant_words(response_text)
    overlap = input_words & response_words
    ratio = len(overlap) / len(input_words)

    return ratio >= min_overlap_ratio, ratio
