#!/usr/bin/env python3
"""
main.py
=======
CLI entry point for the Multi-Model Adversarial Reasoning System.

Usage:
    python main.py --input "We should require all employees to return to office 5 days a week."
    python main.py --input "..." --mock                # no network calls, for testing
    python main.py --input "..." --output result.json
    python main.py --input "..." --verbose              # also log full prompts to console

Environment variables required for real (non-mock) runs:
    MODEL_A_BASE_URL, MODEL_A_API_KEY, MODEL_A_MODEL
    MODEL_B_BASE_URL, MODEL_B_API_KEY, MODEL_B_MODEL
"""

from __future__ import annotations

import argparse
import json
import sys

from config import OrchestrationConfig, load_model_a_config, load_model_b_config
from llm_client import LLMClient, MockLLMClient
from orchestrator import AdversarialReasoningOrchestrator, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a structured proposal -> critique -> revision -> evaluation cycle on a scenario."
    )
    parser.add_argument("--input", type=str, required=True, help="The scenario or problem statement to analyze.")
    parser.add_argument("--output", type=str, default=None, help="Optional path to write the JSON result to.")
    parser.add_argument("--mock", action="store_true", help="Use mock clients for both models (no network calls).")
    parser.add_argument("--verbose", action="store_true", help="Also print full prompts/responses to the console.")
    args = parser.parse_args()

    orchestration_config = OrchestrationConfig()
    setup_logging(orchestration_config.log_file, verbose=args.verbose)

    config_a = load_model_a_config()
    config_b = load_model_b_config()

    if args.mock:
        client_a = MockLLMClient(config_a)
        client_b = MockLLMClient(config_b)
    else:
        client_a = LLMClient(config_a)
        client_b = LLMClient(config_b)

    orchestrator = AdversarialReasoningOrchestrator(client_a, client_b, orchestration_config)
    result = orchestrator.run(args.input)

    if result.success:
        output_str = json.dumps(result.data, indent=2, ensure_ascii=False)
        print(output_str)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_str)
        sys.exit(0)
    else:
        print(json.dumps({"success": False, "error": result.error}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
