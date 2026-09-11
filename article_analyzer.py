#!/usr/bin/env python3
"""
Article Analysis System
========================

Sends article text to a company-hosted LLM API and extracts a structured
analysis:

    - summary            : <= 150 words
    - important_points   : 5-10 clear points (list[str])
    - key_themes         : 3-5 short phrases (list[str])
    - target_audience    : brief description of who the article is for

The LLM is instructed to return ONLY a JSON object. This module validates
that output, enforces the stated constraints, retries with a corrective
prompt if the model drifts, and retries the network call itself on
transient failures.

--------------------------------------------------------------------------
ASSUMPTION ABOUT THE "COMPANY-HOSTED LLM API"
--------------------------------------------------------------------------
No concrete API contract was given, so this implementation targets the
most common shape for internal LLM gateways: an OpenAI-compatible
    POST {base_url}/chat/completions
endpoint (this is what vLLM, LiteLLM, Azure OpenAI proxies, Bedrock
gateways with an OpenAI shim, etc. typically expose).

If your real gateway uses a different contract (Anthropic's native
/v1/messages, a bespoke internal schema, etc.), you only need to change
LLMClient.call() -- prompting, validation, retry logic, and the CLI are
all API-shape agnostic.

--------------------------------------------------------------------------
CONFIGURATION (environment variables)
--------------------------------------------------------------------------
    LLM_API_BASE_URL   e.g. https://llm.internal.mycompany.com/v1
    LLM_API_KEY        bearer token used for Authorization header
    LLM_MODEL          model / deployment name (default: "company-llm")

--------------------------------------------------------------------------
CLI USAGE
--------------------------------------------------------------------------
    python article_analyzer.py --file article.txt
    python article_analyzer.py --file article.txt --title "Article Title"
    cat article.txt | python article_analyzer.py
    python article_analyzer.py --file article.txt --mock   # no network call, for testing
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # handled at call time with a clear error


logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("article_analyzer")


# ===========================================================================
# Configuration
# ===========================================================================

@dataclass
class LLMConfig:
    base_url: str = field(default_factory=lambda: os.environ.get("LLM_API_BASE_URL", "").rstrip("/"))
    api_key: str = field(default_factory=lambda: os.environ.get("LLM_API_KEY", ""))
    model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "company-llm"))
    timeout_seconds: int = 60
    max_network_retries: int = 3
    backoff_base_seconds: float = 1.5
    max_correction_attempts: int = 2  # re-prompts if the model returns invalid/out-of-spec JSON
    temperature: float = 0.2

    def validate(self) -> None:
        if not self.base_url:
            raise ValueError(
                "LLM_API_BASE_URL is not set. Configure it as an environment "
                "variable pointing at your company-hosted LLM gateway."
            )


# ===========================================================================
# Exceptions
# ===========================================================================

class LLMAPIError(Exception):
    """Raised when the LLM API call fails after all retries (network, auth, 5xx, etc.)."""


class LLMResponseValidationError(Exception):
    """Raised when the model's output cannot be parsed/validated as a conforming analysis."""


# ===========================================================================
# Prompt construction
# ===========================================================================

REQUIRED_FIELDS = ("summary", "important_points", "key_themes", "target_audience")

SYSTEM_PROMPT = """You are a precise, structured content-analysis engine.

You will be given the full text of an article. Analyze it carefully and \
respond with ONLY a single valid JSON object. Do not include markdown \
code fences, commentary, headings, or any text before or after the JSON.

The JSON object must have EXACTLY these four fields and no others:

{
  "summary": "<string, 150 words or fewer>",
  "important_points": ["<string>", "... 5 to 10 items total"],
  "key_themes": ["<short phrase>", "... 3 to 5 items total"],
  "target_audience": "<string>"
}

Field rules:
- summary: a concise, self-contained summary of the article. Must be 150 words or fewer.
- important_points: an array of 5 to 10 strings. Each must be a clearly written, \
self-contained point capturing one core idea of the article. No numbering or \
bullet characters inside the strings themselves.
- key_themes: an array of 3 to 5 strings. Each must be a SHORT PHRASE of 2 to 5 \
words (e.g. "climate policy reform", "AI in healthcare") -- NOT a full sentence, \
and not ending in a period.
- target_audience: one or two sentences identifying the specific group of readers \
the article is most relevant to (e.g. "Software engineers evaluating managed \
database options", not just "general readers").

If the article is short, ambiguous, or low quality, still do your best to \
produce a conforming analysis rather than refusing or apologizing.

Output ONLY the JSON object. Nothing else."""


def build_user_prompt(article_text: str, title: Optional[str] = None) -> str:
    header = f"Title: {title}\n\n" if title else ""
    return (
        f"{header}Article:\n\"\"\"\n{article_text.strip()}\n\"\"\"\n\n"
        "Return the JSON object now."
    )


def build_correction_prompt(previous_output: str, problem_description: str) -> str:
    return (
        "Your previous response did not conform to the required schema. "
        f"Problem(s): {problem_description}\n\n"
        "Here is your previous response:\n"
        f"{previous_output}\n\n"
        "Re-read the original instructions and produce a corrected response. "
        "Output ONLY the corrected JSON object -- no explanation, no markdown fences."
    )


# ===========================================================================
# LLM client (network layer)
# ===========================================================================

class LLMClient:
    """Thin wrapper around a company-hosted, OpenAI-compatible chat completions endpoint."""

    def __init__(self, config: LLMConfig):
        self.config = config

    def call(self, messages: List[Dict[str, str]]) -> str:
        """
        Sends a chat completion request and returns the raw text content of
        the model's reply. Retries on network errors and 5xx responses with
        exponential backoff. Raises LLMAPIError if all retries are exhausted
        or a non-retryable error occurs (e.g. 4xx auth/validation errors).
        """
        if requests is None:
            raise LLMAPIError(
                "The 'requests' package is required but not installed. "
                "Install it with: pip install requests"
            )

        self.config.validate()

        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }

        last_error: Optional[Exception] = None

        for attempt in range(1, self.config.max_network_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout_seconds,
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._extract_content(data)

                if 400 <= response.status_code < 500:
                    # Non-retryable: bad request, auth failure, invalid model, etc.
                    raise LLMAPIError(
                        f"LLM API returned client error {response.status_code}: "
                        f"{response.text[:500]}"
                    )

                # 5xx -> retryable
                last_error = LLMAPIError(
                    f"LLM API returned server error {response.status_code}: "
                    f"{response.text[:500]}"
                )
                logger.warning(
                    "Attempt %d/%d: server error %s, will retry",
                    attempt, self.config.max_network_retries, response.status_code,
                )

            except requests.exceptions.Timeout as exc:
                last_error = LLMAPIError(f"Request timed out: {exc}")
                logger.warning("Attempt %d/%d: timeout", attempt, self.config.max_network_retries)

            except requests.exceptions.RequestException as exc:
                last_error = LLMAPIError(f"Network error calling LLM API: {exc}")
                logger.warning("Attempt %d/%d: network error: %s", attempt, self.config.max_network_retries, exc)

            except (KeyError, IndexError, ValueError) as exc:
                # Malformed response envelope (not the article JSON -- the HTTP envelope itself)
                raise LLMAPIError(f"Unexpected response shape from LLM API: {exc}") from exc

            if attempt < self.config.max_network_retries:
                sleep_time = self.config.backoff_base_seconds ** attempt
                time.sleep(sleep_time)

        raise LLMAPIError(
            f"LLM API call failed after {self.config.max_network_retries} attempts: {last_error}"
        )

    @staticmethod
    def _extract_content(response_json: Dict[str, Any]) -> str:
        """Pulls the assistant message text out of an OpenAI-shaped response body."""
        try:
            return response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMAPIError(
                f"Could not find message content in API response: {response_json}"
            ) from exc


# ===========================================================================
# Parsing & validation of the model's JSON output
# ===========================================================================

def extract_json_object(raw_text: str) -> str:
    """
    Best-effort extraction of a JSON object from model output that may be
    wrapped in markdown fences or have stray whitespace/text around it.
    """
    text = raw_text.strip()

    # Strip markdown code fences if present, e.g. ```json ... ``` or ``` ... ```
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    # If there's leading/trailing prose, grab the outermost {...} span.
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]

    return text


def parse_llm_json(raw_text: str) -> Dict[str, Any]:
    """Parses the model's raw text into a dict, raising LLMResponseValidationError on failure."""
    candidate = extract_json_object(raw_text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMResponseValidationError(
            f"Model output was not valid JSON: {exc}. Raw output (truncated): {raw_text[:300]}"
        ) from exc


def _count_words(text: str) -> int:
    return len(text.split())


def _looks_like_full_sentence(phrase: str) -> bool:
    """Heuristic: flags key_themes entries that look like sentences rather than short phrases."""
    stripped = phrase.strip()
    if stripped.endswith((".", "!", "?")):
        return True
    if _count_words(stripped) > 6:
        return True
    return False


def validate_analysis(data: Any) -> List[str]:
    """
    Validates the parsed JSON against the required schema and constraints.
    Returns a list of human-readable problem descriptions (empty list = valid).
    Does not raise -- callers decide whether to retry or fail based on the list.
    """
    problems: List[str] = []

    if not isinstance(data, dict):
        return [f"Top-level output must be a JSON object, got {type(data).__name__}."]

    # Unknown / missing fields
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        problems.append(f"Missing required field(s): {', '.join(missing)}.")

    extra = [k for k in data.keys() if k not in REQUIRED_FIELDS]
    if extra:
        problems.append(f"Unexpected extra field(s) present: {', '.join(extra)}.")

    # Continue validating whichever fields ARE present, even if others are
    # missing, so the model gets a complete picture of every problem in one
    # correction round-trip rather than discovering issues one at a time.

    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        problems.append("'summary' must be a non-empty string.")
    else:
        word_count = _count_words(summary)
        if word_count > 150:
            problems.append(f"'summary' exceeds 150 words (found {word_count}).")

    points = data.get("important_points")
    if not isinstance(points, list) or not all(isinstance(p, str) and p.strip() for p in points):
        problems.append("'important_points' must be a list of non-empty strings.")
    else:
        if not (5 <= len(points) <= 10):
            problems.append(f"'important_points' must contain 5-10 items (found {len(points)}).")

    themes = data.get("key_themes")
    if not isinstance(themes, list) or not all(isinstance(t, str) and t.strip() for t in themes):
        problems.append("'key_themes' must be a list of non-empty strings.")
    else:
        if not (3 <= len(themes) <= 5):
            problems.append(f"'key_themes' must contain 3-5 items (found {len(themes)}).")
        sentence_like = [t for t in themes if _looks_like_full_sentence(t)]
        if sentence_like:
            problems.append(
                "'key_themes' must be short phrases (2-5 words), not full sentences. "
                f"Offending entries: {sentence_like}"
            )

    audience = data.get("target_audience")
    if not isinstance(audience, str) or not audience.strip():
        problems.append("'target_audience' must be a non-empty string.")

    return problems


# ===========================================================================
# High-level analyzer: orchestrates prompting, calling, validating, retrying
# ===========================================================================

@dataclass
class AnalysisResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_last_response: Optional[str] = None
    attempts_used: int = 0


class ArticleAnalyzer:
    def __init__(self, config: Optional[LLMConfig] = None, client: Optional[LLMClient] = None):
        self.config = config or LLMConfig()
        self.client = client or LLMClient(self.config)

    def analyze(self, article_text: str, title: Optional[str] = None) -> AnalysisResult:
        if not article_text or not article_text.strip():
            return AnalysisResult(success=False, error="Article text is empty.")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(article_text, title)},
        ]

        last_raw: Optional[str] = None
        total_attempts = self.config.max_correction_attempts + 1

        for attempt in range(1, total_attempts + 1):
            try:
                raw_response = self.client.call(messages)
            except LLMAPIError as exc:
                logger.error("LLM API call failed: %s", exc)
                return AnalysisResult(
                    success=False,
                    error=f"LLM API error: {exc}",
                    raw_last_response=last_raw,
                    attempts_used=attempt,
                )

            last_raw = raw_response

            try:
                parsed = parse_llm_json(raw_response)
            except LLMResponseValidationError as exc:
                logger.warning("Attempt %d: JSON parse failure: %s", attempt, exc)
                if attempt < total_attempts:
                    messages.append({"role": "assistant", "content": raw_response})
                    messages.append(
                        {"role": "user", "content": build_correction_prompt(raw_response, str(exc))}
                    )
                    continue
                return AnalysisResult(
                    success=False,
                    error=f"Model did not return valid JSON after {attempt} attempt(s): {exc}",
                    raw_last_response=raw_response,
                    attempts_used=attempt,
                )

            problems = validate_analysis(parsed)
            if not problems:
                return AnalysisResult(
                    success=True,
                    data=parsed,
                    raw_last_response=raw_response,
                    attempts_used=attempt,
                )

            logger.warning("Attempt %d: schema/constraint violations: %s", attempt, problems)
            if attempt < total_attempts:
                messages.append({"role": "assistant", "content": raw_response})
                messages.append(
                    {"role": "user", "content": build_correction_prompt(raw_response, "; ".join(problems))}
                )
                continue

            return AnalysisResult(
                success=False,
                error=(
                    f"Model output failed validation after {attempt} attempt(s): "
                    + "; ".join(problems)
                ),
                raw_last_response=raw_response,
                attempts_used=attempt,
            )

        # Unreachable, but keeps type checkers happy.
        return AnalysisResult(success=False, error="Unknown failure.", attempts_used=total_attempts)


# ===========================================================================
# Mock client (for local testing without a real API endpoint / credentials)
# ===========================================================================

class MockLLMClient(LLMClient):
    """Returns a canned, schema-conforming response. Useful for testing the
    validation/CLI plumbing without needing real API credentials."""

    def call(self, messages: List[Dict[str, str]]) -> str:
        logger.info("[MOCK MODE] Returning a canned example response instead of calling the network.")
        return json.dumps(
            {
                "summary": (
                    "The article discusses recent advances in renewable energy storage, "
                    "focusing on how improved battery chemistry and grid-scale deployment "
                    "are helping utilities integrate more solar and wind power. It covers "
                    "cost trends, policy incentives, and remaining technical challenges, "
                    "concluding that storage is becoming the key bottleneck -- and "
                    "opportunity -- for the clean energy transition."
                ),
                "important_points": [
                    "Battery storage costs have fallen significantly over the past decade.",
                    "Grid-scale storage helps balance intermittent solar and wind generation.",
                    "New chemistries beyond lithium-ion are entering commercial deployment.",
                    "Government incentives are accelerating utility-scale storage projects.",
                    "Permitting and interconnection delays remain a major bottleneck.",
                    "Storage is increasingly viewed as essential infrastructure, not an add-on.",
                ],
                "key_themes": [
                    "energy storage economics",
                    "renewable grid integration",
                    "battery technology innovation",
                    "clean energy policy",
                ],
                "target_audience": (
                    "Energy sector professionals, policymakers, and investors tracking "
                    "the renewable energy transition."
                ),
            }
        )


# ===========================================================================
# CLI
# ===========================================================================

def _read_article_text(args: argparse.Namespace) -> str:
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("No input provided. Use --file <path> or pipe article text via stdin.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze an article using a company-hosted LLM API.")
    parser.add_argument("--file", type=str, help="Path to a text file containing the article.")
    parser.add_argument("--title", type=str, default=None, help="Optional article title.")
    parser.add_argument("--output", type=str, default=None, help="Optional path to write the JSON result to.")
    parser.add_argument(
        "--mock", action="store_true",
        help="Use a mock LLM client (no network call) -- useful for testing without credentials."
    )
    args = parser.parse_args()

    article_text = _read_article_text(args)

    config = LLMConfig()
    client = MockLLMClient(config) if args.mock else LLMClient(config)
    analyzer = ArticleAnalyzer(config=config, client=client)

    result = analyzer.analyze(article_text, title=args.title)

    if result.success:
        output_str = json.dumps(result.data, indent=2, ensure_ascii=False)
        print(output_str)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_str)
            logger.info("Result written to %s", args.output)
        sys.exit(0)
    else:
        logger.error("Analysis failed: %s", result.error)
        print(json.dumps({"success": False, "error": result.error}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
