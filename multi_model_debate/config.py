"""
config.py
=========
Configuration for the Multi-Model Interaction System.

Two independent model configs (Model A, Model B) are loaded from
environment variables so each can point at a different company-hosted
LLM deployment, with different credentials, if needed.

Environment variables
----------------------
    MODEL_A_BASE_URL, MODEL_A_API_KEY, MODEL_A_MODEL
    MODEL_B_BASE_URL, MODEL_B_API_KEY, MODEL_B_MODEL

Same assumption as before: each base_url is expected to expose an
OpenAI-compatible POST {base_url}/chat/completions endpoint. If either
company gateway uses a different contract, only LLMClient.call() in
llm_client.py needs to change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ModelConfig:
    label: str            # human-readable label used in logs/output, e.g. "Model A"
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 60
    max_network_retries: int = 3
    backoff_base_seconds: float = 1.5
    temperature: float = 0.4

    def validate(self) -> None:
        if not self.base_url:
            raise ValueError(
                f"{self.label}: base_url is not configured. Set the corresponding "
                f"*_BASE_URL environment variable."
            )


def load_model_a_config() -> ModelConfig:
    return ModelConfig(
        label="Model A",
        base_url=os.environ.get("MODEL_A_BASE_URL", "").rstrip("/"),
        api_key=os.environ.get("MODEL_A_API_KEY", ""),
        model=os.environ.get("MODEL_A_MODEL", "model-a"),
    )


def load_model_b_config() -> ModelConfig:
    return ModelConfig(
        label="Model B",
        base_url=os.environ.get("MODEL_B_BASE_URL", "").rstrip("/"),
        api_key=os.environ.get("MODEL_B_API_KEY", ""),
        model=os.environ.get("MODEL_B_MODEL", "model-b"),
    )


@dataclass
class OrchestrationConfig:
    # How many extra corrective re-prompts a model gets if its output is
    # malformed JSON, off-schema, or fails the relevance check.
    max_correction_attempts: int = 2

    # Minimum fraction of the topic's significant words that must appear
    # (directly or as simple stems) somewhere in a model's response for it
    # to be considered "on topic". This is a cheap lexical heuristic, not
    # a semantic judge -- see validation.py for details and how to swap in
    # a model-based relevance judge instead.
    min_relevance_overlap: float = 0.12

    log_file: str = os.environ.get("DEBATE_LOG_FILE", "multi_model_debate.log")
