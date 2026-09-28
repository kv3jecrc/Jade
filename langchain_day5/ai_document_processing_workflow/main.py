#!/usr/bin/env python3
"""
main.py
=======
CLI entry point for the AI Document Processing Workflow.

Usage:
    python main.py --file sample_srs.txt
    python main.py --file sample_srs.txt --human-feedback "approved"
    python main.py --file sample_srs.txt --human-feedback "revise: tighten the security NFR"
    python main.py --file sample_srs.txt --mock   # no LLM calls, for testing the graph wiring

If --human-feedback is omitted, the script pauses at the Human Review
step and prompts interactively (this is the genuine HITL pause -- the
process really stops and waits; it isn't simulated). Passing
--human-feedback skips the interactive prompt, e.g. for automated runs.
"""

import argparse
import json
from pathlib import Path

from langgraph.types import Command

from workflow import build_graph, print_final_report, print_merged_report

DEFAULT_SRS_FILE = Path(__file__).parent / "sample_srs.txt"


def run(srs_text: str, human_feedback: str | None, thread_id: str = "srs-run-1") -> dict:
    app = build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    print("Starting workflow: Document Analyzer -> Requirement/Risk Agents (parallel) "
          "-> Architecture/Test Case Agents (parallel) -> Merge -> Human Review -> Final Report\n")

    # Runs everything up to (and including triggering) the Human Review
    # interrupt. Execution genuinely pauses here.
    state_after_pause = app.invoke({"srs_text": srs_text}, config=config)

    snapshot = app.get_state(config)
    if not snapshot.next:
        # No interrupt was hit -- shouldn't happen with this graph, but
        # guard against it rather than assuming.
        return state_after_pause

    # Pull the interrupt's payload (what Human Review wants reviewed).
    interrupt_payload = snapshot.tasks[0].interrupts[0].value
    print_merged_report(interrupt_payload["merged_report"])

    if human_feedback is None:
        print(interrupt_payload["message"])
        human_feedback = input(
            "Enter your decision (e.g. 'approved' or 'revise: <what to change>'): "
        ).strip()
        if not human_feedback:
            human_feedback = "approved"

    print(f"\n[Human Review] Decision received: {human_feedback!r}\n")

    human_decision = {"decision": human_feedback}
    final_state = app.invoke(Command(resume=human_decision), config=config)

    return final_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI Document Processing Workflow on an SRS.")
    parser.add_argument("--file", type=str, default=str(DEFAULT_SRS_FILE), help="Path to the SRS text file.")
    parser.add_argument(
        "--human-feedback", type=str, default=None,
        help="Skip the interactive prompt and use this as the human reviewer's decision."
    )
    parser.add_argument("--output", type=str, default=None, help="Optional path to write the final report JSON to.")
    args = parser.parse_args()

    srs_text = Path(args.file).read_text(encoding="utf-8")

    final_state = run(srs_text, human_feedback=args.human_feedback)

    final_report = final_state.get("final_report", {})
    print_final_report(final_report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(final_state, f, indent=2, ensure_ascii=False)
        print(f"\nFull final state written to {args.output}")


if __name__ == "__main__":
    main()
