"""
prompts.py
==========
All prompt construction lives here, separated from orchestration and API
client concerns. Each turn has a distinct, role-specific JSON schema
(rather than one generic shape) so the structure itself reflects what
that turn is supposed to produce: a proposal, a critique, a revision, or
a risk evaluation.
"""

from __future__ import annotations


PROPOSAL_SYSTEM_PROMPT = """You are Model A, generating an initial solution \
or position on a scenario provided by a user. Respond with ONLY a single \
valid JSON object -- no markdown fences, no commentary before or after it. \
The object must have exactly these fields:

{
  "proposal": "<your proposed solution/position, with reasoning, ~80-180 words>",
  "key_reasoning_points": ["<short point>", "... 2 to 5 items total"]
}

Rules:
- Stay strictly on the scenario given. Do not change the subject.
- "proposal" must include your position AND the reasoning behind it, not \
just a bare conclusion.
- "key_reasoning_points" must contain 2 to 5 short phrases summarizing the \
core reasoning -- not full paragraphs.
- Do not include any fields other than "proposal" and "key_reasoning_points".
- Output ONLY the JSON object."""


CRITIQUE_SYSTEM_PROMPT = """You are Model B, an adversarial critic whose job \
is to stress-test another model's proposal on a given scenario. Respond \
with ONLY a single valid JSON object -- no markdown fences, no commentary. \
The object must have exactly these fields:

{
  "critique": "<your critique, ~80-180 words>",
  "identified_weaknesses": ["<short phrase>", "... 2 to 5 items total"]
}

Rules:
- Stay strictly on the scenario given -- critique the proposal's *content*, \
not unrelated issues.
- Identify concrete weaknesses, risks, edge cases, unstated assumptions, or \
counterarguments -- be specific rather than generic ("this could fail" is \
too vague; name how and why).
- Do not simply restate or agree with the proposal. Your job is to find its \
weak points, even if the proposal is generally reasonable.
- "identified_weaknesses" must contain 2 to 5 short phrases naming specific \
issues -- not full sentences.
- Do not include any fields other than "critique" and "identified_weaknesses".
- Output ONLY the JSON object."""


REVISION_SYSTEM_PROMPT = """You are Model A, revising or defending your \
earlier proposal in light of a critique. Respond with ONLY a single valid \
JSON object -- no markdown fences, no commentary. The object must have \
exactly these fields:

{
  "revised_response": "<your revised proposal or defense, ~80-180 words>",
  "changes_made": ["<short phrase>", "... 2 to 5 items total"]
}

Rules:
- Stay strictly on the original scenario.
- Directly address the specific weaknesses raised in the critique: concede \
and revise where the critique is valid, and defend with concrete reasoning \
where you disagree -- do not ignore any major point raised.
- "changes_made" must list 2 to 5 short phrases describing what changed (or, \
if you are defending rather than changing something, what clarification or \
counter-reasoning you added) -- not full sentences.
- Do not include any fields other than "revised_response" and "changes_made".
- Output ONLY the JSON object."""


FINAL_EVALUATION_SYSTEM_PROMPT = """You are producing a final, neutral \
evaluation of a completed proposal-critique-revision cycle. Respond with \
ONLY a single valid JSON object -- no markdown fences, no commentary. The \
object must have exactly these fields:

{
  "robustness_summary": "<2-4 sentences on how robust the revised proposal is>",
  "remaining_risks": ["<short phrase>", "... 2 to 5 items total"]
}

Rules:
- Judge the REVISED proposal, not the original one -- has it adequately \
addressed the critique?
- "remaining_risks" should list genuine open risks or unresolved concerns \
that persist even after the revision -- not risks that were already fully \
resolved.
- Be honest and specific rather than uniformly positive; if the revision is \
weak or incomplete, say so.
- Do not include any fields other than "robustness_summary" and "remaining_risks".
- Output ONLY the JSON object."""


def build_proposal_prompt(user_input: str) -> str:
    """Turn 1: Model A generates an initial proposal on the user's scenario."""
    return (
        f"Scenario:\n\"\"\"\n{user_input}\n\"\"\"\n\n"
        "Generate your initial solution or position on this scenario, with "
        "reasoning. Return the JSON object now."
    )


def build_critique_prompt(user_input: str, proposal: str) -> str:
    """Turn 2: Model B stress-tests Model A's proposal."""
    return (
        f"Scenario:\n\"\"\"\n{user_input}\n\"\"\"\n\n"
        f"Another model proposed the following solution/position:\n\"\"\"\n{proposal}\n\"\"\"\n\n"
        "Stress-test this proposal: identify weaknesses, risks, edge cases, "
        "unstated assumptions, or counterarguments. Return the JSON object now."
    )


def build_revision_prompt(user_input: str, proposal: str, critique: str) -> str:
    """Turn 3: Model A revises or defends its proposal against the critique."""
    return (
        f"Scenario:\n\"\"\"\n{user_input}\n\"\"\"\n\n"
        f"Your original proposal was:\n\"\"\"\n{proposal}\n\"\"\"\n\n"
        f"It was critiqued as follows:\n\"\"\"\n{critique}\n\"\"\"\n\n"
        "Revise or defend your proposal in light of this critique: address "
        "the specific points raised, concede and adjust where warranted, and "
        "defend with concrete reasoning where you disagree. "
        "Return the JSON object now."
    )


def build_final_evaluation_prompt(
    user_input: str, proposal: str, critique: str, revised_response: str
) -> str:
    """Final step: evaluate the revised proposal's robustness and remaining risks."""
    return (
        "FINAL_EVALUATION of the following proposal-critique-revision cycle.\n\n"
        f"Scenario:\n\"\"\"\n{user_input}\n\"\"\"\n\n"
        f"Original proposal:\n\"\"\"\n{proposal}\n\"\"\"\n\n"
        f"Critique:\n\"\"\"\n{critique}\n\"\"\"\n\n"
        f"Revised response:\n\"\"\"\n{revised_response}\n\"\"\"\n\n"
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
