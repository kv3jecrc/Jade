"""
prompts.py
==========
All prompt construction lives here, separated from orchestration and
API-client concerns. Every model turn is instructed to return a small,
strictly structured JSON object so responses can be validated and
composed programmatically rather than treated as free text.
"""

from __future__ import annotations

from typing import Optional


TURN_SYSTEM_PROMPT = """You are participating in a structured, good-faith \
discussion between two AI models on a given topic. Respond with ONLY a \
single valid JSON object -- no markdown fences, no commentary before or \
after it. The object must have exactly these fields:

{
  "response": "<your full response, several sentences>",
  "key_points": ["<short point>", "... 2 to 5 items total"]
}

Rules:
- Stay strictly on the given topic. Do not change the subject.
- "response" should be substantive (roughly 60-150 words), directly engaging \
with the topic and, where provided, with the other model's prior response.
- "key_points" must contain 2 to 5 short phrases summarizing your response's \
core claims -- not full paragraphs.
- Do not include any fields other than "response" and "key_points".
- Output ONLY the JSON object."""


SYNTHESIS_SYSTEM_PROMPT = """You are producing a brief, neutral synthesis of \
a two-model discussion. Respond with ONLY a single valid JSON object -- no \
markdown fences, no commentary. The object must have exactly this field:

{
  "conclusion": "<a short, neutral synthesis, 2-4 sentences>"
}

The conclusion should note where the two models agreed, where they \
disagreed, and what a reasonable practical takeaway is. Do not simply repeat \
one side. Output ONLY the JSON object."""


def build_initial_prompt(topic: str) -> str:
    """Turn 1: Model A states an initial position on the topic."""
    return (
        f"Topic: \"{topic}\"\n\n"
        "Give your initial position, explanation, or argument on this topic. "
        "Return the JSON object now."
    )


def build_critique_prompt(topic: str, model_a_response: str) -> str:
    """Turn 2: Model B critiques/questions/expands on Model A's response."""
    return (
        f"Topic: \"{topic}\"\n\n"
        f"Another model gave this initial response on the topic:\n\"\"\"\n{model_a_response}\n\"\"\"\n\n"
        "Critique this response: raise questions, point out gaps or "
        "counterarguments, or expand on it with additional considerations. "
        "Stay on the original topic. Return the JSON object now."
    )


def build_rebuttal_prompt(topic: str, model_a_response: str, model_b_critique: str) -> str:
    """Turn 3: Model A replies to Model B's critique."""
    return (
        f"Topic: \"{topic}\"\n\n"
        f"Your earlier response was:\n\"\"\"\n{model_a_response}\n\"\"\"\n\n"
        f"Another model critiqued it as follows:\n\"\"\"\n{model_b_critique}\n\"\"\"\n\n"
        "Respond to this critique: address the specific points raised, "
        "concede where warranted, and defend or refine your position where "
        "you disagree. Stay on the original topic. Return the JSON object now."
    )


def build_synthesis_prompt(
    topic: str,
    model_a_response: str,
    model_b_critique: str,
    model_a_final_reply: str,
) -> str:
    """Final step: synthesize the discussion into a short neutral conclusion."""
    return (
        "SYNTHESIZE the following discussion.\n\n"
        f"Topic: \"{topic}\"\n\n"
        f"Model A's initial response:\n\"\"\"\n{model_a_response}\n\"\"\"\n\n"
        f"Model B's critique:\n\"\"\"\n{model_b_critique}\n\"\"\"\n\n"
        f"Model A's final reply:\n\"\"\"\n{model_a_final_reply}\n\"\"\"\n\n"
        "Return the JSON object now."
    )


def build_correction_prompt(previous_output: str, problem_description: str) -> str:
    return (
        "Your previous response did not conform to the required schema or "
        f"instructions. Problem(s): {problem_description}\n\n"
        f"Here is your previous response:\n{previous_output}\n\n"
        "Re-read the original instructions and produce a corrected response. "
        "Output ONLY the corrected JSON object -- no explanation, no markdown fences."
    )
