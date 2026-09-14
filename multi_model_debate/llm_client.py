"""
llm_client.py
=============
API client layer. One LLMClient instance is created per model (Model A,
Model B) using that model's ModelConfig. The orchestrator never talks to
requests/HTTP directly -- it only calls client.call(messages).

This isolates the "how do we actually talk to the company LLM gateway"
concern from prompting/orchestration/validation, so swapping either
model's backend (or the API contract itself) touches only this file.
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

logger = logging.getLogger("multi_model_debate")


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
        LLMAPIError for non-retryable failures (4xx) or after retries are
        exhausted.
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
                raise LLMAPIError(
                    f"{self.config.label}: unexpected response shape from API: {exc}"
                ) from exc

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
    API credentials for either model.

    `role` controls which canned response is returned, since Model A and
    Model B play different roles across the turns.
    """

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._call_count = 0

    def call(self, messages: List[Dict[str, str]]) -> str:
        self._call_count += 1
        logger.info("[MOCK %s] Returning canned response for call #%d", self.config.label, self._call_count)

        import json

        # Look at the last user message to decide which canned turn this is.
        # NOTE: decide primarily by (model label, call number) rather than by
        # sniffing keywords in the prompt text -- keyword substrings are
        # fragile (e.g. "critique" also matches inside "critiqued").
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        if "SYNTHESIZE" in last_user_msg:
            return json.dumps({
                "conclusion": (
                    "Both models agree remote work offers flexibility and productivity "
                    "gains for many roles, but disagree on long-term effects on mentorship "
                    "and company culture -- suggesting hybrid models are the likely "
                    "practical compromise."
                )
            })

        if self.config.label == "Model A":
            if self._call_count == 1:
                # Turn 1: initial position
                return json.dumps({
                    "response": (
                        "Remote work increases productivity and employee satisfaction by "
                        "removing commutes and giving people control over their environment, "
                        "and companies that embraced it have seen measurable retention gains."
                    ),
                    "key_points": [
                        "Eliminates commute time, freeing hours for focused work",
                        "Employees report higher job satisfaction with flexible arrangements",
                        "Companies see improved retention when offering remote options",
                    ],
                })
            # Turn 3: Model A's final rebuttal (call #2 for this client)
            return json.dumps({
                "response": (
                    "The mentorship concern is valid, but it's a solvable process problem "
                    "for remote work, not an inherent flaw -- structured mentorship programs "
                    "and intentional pairing can close that gap without giving up remote "
                    "work's productivity and retention benefits."
                ),
                "key_points": [
                    "Mentorship gaps in remote work can be addressed with structured programs",
                    "Productivity and retention gains still outweigh the drawback",
                    "The tradeoff is a process fix, not a reason to abandon remote work",
                ],
            })

        # Model B: critique (its only call in this flow)
        return json.dumps({
            "response": (
                "While remote work does improve flexibility, the initial argument "
                "understates the erosion of informal mentorship and spontaneous "
                "collaboration that happens in person. Junior employees in particular "
                "may be disadvantaged by fully remote work setups."
            ),
            "key_points": [
                "Informal mentorship is harder to replicate remotely",
                "Junior employees may be disproportionately affected by remote work",
                "Spontaneous collaboration declines without shared physical space",
            ],
        })
