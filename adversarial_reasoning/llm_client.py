"""
llm_client.py
=============
API client layer. One LLMClient instance is created per model (Model A =
proposer/defender, Model B = adversarial critic). The orchestrator never
touches HTTP directly -- it only calls client.call(messages). This keeps
"how do we talk to the company LLM gateway" isolated from prompting,
orchestration, and validation.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

from config import ModelConfig

logger = logging.getLogger("adversarial_reasoning")


class LLMAPIError(Exception):
    """Raised when a model's API call fails after all retries."""


class LLMClient:
    """Thin wrapper around a company-hosted, OpenAI-compatible chat completions endpoint."""

    def __init__(self, config: ModelConfig):
        self.config = config

    def call(self, messages: List[Dict[str, str]]) -> str:
        """
        Sends a chat completion request for this model and returns the raw
        text content of its reply. Retries transient failures (timeouts,
        connection errors, 5xx) with exponential backoff. Raises
        LLMAPIError for non-retryable failures (4xx, misconfiguration) or
        after retries are exhausted.
        """
        if requests is None:
            raise LLMAPIError(
                "The 'requests' package is required but not installed. "
                "Install it with: pip install requests"
            )

        try:
            self.config.validate()
        except ValueError as exc:
            raise LLMAPIError(str(exc)) from exc

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

        logger.debug("[%s] Outgoing request messages: %s", self.config.label, messages)

        last_error: Optional[Exception] = None

        for attempt in range(1, self.config.max_network_retries + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=payload, timeout=self.config.timeout_seconds
                )

                if response.status_code == 200:
                    data = response.json()
                    content = self._extract_content(data)
                    logger.debug("[%s] Raw response content: %s", self.config.label, content)
                    return content

                if 400 <= response.status_code < 500:
                    raise LLMAPIError(
                        f"{self.config.label}: API returned client error "
                        f"{response.status_code}: {response.text[:500]}"
                    )

                last_error = LLMAPIError(
                    f"{self.config.label}: API returned server error "
                    f"{response.status_code}: {response.text[:500]}"
                )
                logger.warning(
                    "[%s] Attempt %d/%d: server error %s, will retry",
                    self.config.label, attempt, self.config.max_network_retries, response.status_code,
                )

            except requests.exceptions.Timeout as exc:
                last_error = LLMAPIError(f"{self.config.label}: request timed out: {exc}")
                logger.warning("[%s] Attempt %d/%d: timeout", self.config.label, attempt, self.config.max_network_retries)

            except requests.exceptions.RequestException as exc:
                last_error = LLMAPIError(f"{self.config.label}: network error: {exc}")
                logger.warning(
                    "[%s] Attempt %d/%d: network error: %s",
                    self.config.label, attempt, self.config.max_network_retries, exc,
                )

            except (KeyError, IndexError, ValueError) as exc:
                raise LLMAPIError(f"{self.config.label}: unexpected response shape from API: {exc}") from exc

            if attempt < self.config.max_network_retries:
                time.sleep(self.config.backoff_base_seconds ** attempt)

        raise LLMAPIError(
            f"{self.config.label}: API call failed after "
            f"{self.config.max_network_retries} attempts: {last_error}"
        )

    @staticmethod
    def _extract_content(response_json: Dict[str, Any]) -> str:
        try:
            return response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMAPIError(f"Could not find message content in API response: {response_json}") from exc


class MockLLMClient(LLMClient):
    """
    Returns canned, schema-conforming responses so the orchestration,
    validation, and CLI plumbing can be tested end-to-end without real
    API credentials. Canned content is written around a "should we adopt
    a 4-day work week" scenario -- use that (or something lexically
    similar) as the input when testing with --mock, since responses are
    static text rather than genuinely generated.
    """

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._call_count = 0

    def call(self, messages: List[Dict[str, str]]) -> str:
        self._call_count += 1
        logger.info("[MOCK %s] Returning canned response for call #%d", self.config.label, self._call_count)

        import json

        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        if "FINAL_EVALUATION" in last_user_msg:
            return json.dumps({
                "robustness_summary": (
                    "The revised proposal for a four-day work week is reasonably robust: it "
                    "directly addresses the coverage and client-availability concerns raised "
                    "in the critique with a staggered-team model, and preserves the original "
                    "productivity and retention rationale."
                ),
                "remaining_risks": [
                    "Staggered scheduling adds coordination overhead that was not fully quantified",
                    "Effectiveness likely varies significantly by team/role and may not generalize company-wide",
                    "No pilot data yet exists to confirm the productivity assumptions hold in practice",
                ],
            })

        if self.config.label == "Model A":
            if self._call_count == 1:
                return json.dumps({
                    "proposal": (
                        "The company should adopt a four-day work week, compressing the "
                        "standard 40 hours into four 10-hour days. This is expected to "
                        "improve employee satisfaction and retention while maintaining "
                        "output, based on productivity gains from reduced burnout and "
                        "fewer context-switching interruptions across a shorter week."
                    ),
                    "key_reasoning_points": [
                        "Reduces burnout by concentrating focused work into fewer days",
                        "Improves retention and recruiting appeal versus five-day competitors",
                        "Total weekly hours stay the same, so output should not meaningfully drop",
                    ],
                })
            # Revision (2nd call for Model A)
            return json.dumps({
                "revised_response": (
                    "To address the coverage concern, the four-day work week will use "
                    "staggered team schedules rather than a single company-wide day off, "
                    "ensuring client-facing coverage five days a week while every employee "
                    "still works only four days. This preserves the original productivity "
                    "and retention rationale while directly closing the gap the critique "
                    "identified."
                ),
                "changes_made": [
                    "Introduced staggered team schedules instead of a uniform day off",
                    "Explicitly preserved five-day client coverage",
                    "Kept the original 10-hour compressed day structure unchanged",
                ],
            })

        # Model B critique (its only call)
        return json.dumps({
            "critique": (
                "The proposal assumes output stays flat simply because total hours are "
                "unchanged, but it does not address how client-facing coverage will work "
                "if the whole company is off the same day, nor whether 10-hour days are "
                "sustainable for roles requiring sustained attention, such as support or "
                "manufacturing shifts."
            ),
            "identified_weaknesses": [
                "No plan for maintaining client coverage on the shared day off",
                "Assumes uniform applicability across roles with very different work patterns",
                "10-hour days may increase fatigue-related errors in attention-heavy roles",
            ],
        })
