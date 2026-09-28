"""
workflow.py
============
Builds and runs the multi-agent LangGraph workflow:

    Input SRS
        |
        v
    Document Analyzer
        |
    +---+---+
    |       |
    v       v
Requirement  Risk
  Agent     Agent
    |         |
    v         v
Architecture  Test Case
  Agent        Agent
    |         |
    +----+----+
         |
         v
   Merge Results
         |
         v
  Human Review (HITL)
         |
         v
    Final Report

Requirement Agent and Risk Agent run in the same LangGraph superstep (true
parallel fan-out from Document Analyzer); Architecture Agent and Test Case
Agent likewise run in parallel before both are required to reach Merge
Results (fan-in). Human Review genuinely pauses graph execution via
LangGraph's `interrupt()` -- the process can stop, and resume later from
a persisted checkpoint, without re-running the four analysis agents.
"""

from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from json_utils import parse_agent_json
from llm_setup import get_llm
from prompts import (
    ARCHITECTURE_AGENT_PROMPT,
    DOCUMENT_ANALYZER_PROMPT,
    FINAL_REPORT_PROMPT,
    REQUIREMENT_AGENT_PROMPT,
    RISK_AGENT_PROMPT,
    TEST_CASE_AGENT_PROMPT,
    fill,
)


# ---------------------------------------------------------------------
# State
# ---------------------------------------------------------------------

class SRSWorkflowState(TypedDict, total=False):
    srs_text: str
    document_summary: Dict[str, Any]
    requirements: Dict[str, Any]
    risks: Dict[str, Any]
    architecture: Dict[str, Any]
    test_cases: Dict[str, Any]
    merged_report: Dict[str, Any]
    human_decision: Dict[str, Any]
    final_report: Dict[str, Any]


def _call_agent(prompt: str, agent_name: str) -> Dict[str, Any]:
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    return parse_agent_json(response.content, agent_name)


# ---------------------------------------------------------------------
# Agent nodes
# ---------------------------------------------------------------------

def document_analyzer_node(state: SRSWorkflowState) -> dict:
    print("[Document Analyzer] Reading SRS and producing structural summary...")
    prompt = fill(DOCUMENT_ANALYZER_PROMPT, srs_text=state["srs_text"])
    result = _call_agent(prompt, "Document Analyzer")
    return {"document_summary": result}


def requirement_agent_node(state: SRSWorkflowState) -> dict:
    print("[Requirement Agent] Extracting functional/non-functional requirements...")
    prompt = fill(
        REQUIREMENT_AGENT_PROMPT,
        document_summary=state["document_summary"], srs_text=state["srs_text"]
    )
    result = _call_agent(prompt, "Requirement Agent")
    return {"requirements": result}


def risk_agent_node(state: SRSWorkflowState) -> dict:
    print("[Risk Agent] Identifying project and technical risks...")
    prompt = fill(
        RISK_AGENT_PROMPT,
        document_summary=state["document_summary"], srs_text=state["srs_text"]
    )
    result = _call_agent(prompt, "Risk Agent")
    return {"risks": result}


def architecture_agent_node(state: SRSWorkflowState) -> dict:
    print("[Architecture Agent] Proposing architecture from requirements...")
    prompt = fill(ARCHITECTURE_AGENT_PROMPT, requirements=state["requirements"])
    result = _call_agent(prompt, "Architecture Agent")
    return {"architecture": result}


def test_case_agent_node(state: SRSWorkflowState) -> dict:
    print("[Test Case Agent] Designing test cases targeting identified risks...")
    prompt = fill(TEST_CASE_AGENT_PROMPT, risks=state["risks"])
    result = _call_agent(prompt, "Test Case Agent")
    return {"test_cases": result}


def merge_results_node(state: SRSWorkflowState) -> dict:
    """Pure aggregation -- no LLM call. Combines every agent's structured
    output into a single merged_report dict for human review."""
    print("[Merge Results] Combining outputs from all five agents...")
    merged = {
        "document_summary": state.get("document_summary", {}),
        "requirements": state.get("requirements", {}),
        "risks": state.get("risks", {}),
        "architecture": state.get("architecture", {}),
        "test_cases": state.get("test_cases", {}),
    }
    return {"merged_report": merged}


def human_review_node(state: SRSWorkflowState) -> dict:
    """
    Genuine human-in-the-loop pause: calls LangGraph's `interrupt()`,
    which suspends graph execution and persists state via the compiled
    graph's checkpointer. The process can exit entirely here; resuming
    later re-enters this exact node with the human's input, WITHOUT
    re-running the Document Analyzer / Requirement / Risk / Architecture /
    Test Case agents that already ran.
    """
    decision = interrupt(
        {
            "message": "Human review required before the final report is generated.",
            "merged_report": state["merged_report"],
        }
    )
    return {"human_decision": decision}


def final_report_node(state: SRSWorkflowState) -> dict:
    print("[Final Report] Synthesizing final report from merged results + human decision...")
    prompt = fill(
        FINAL_REPORT_PROMPT,
        merged_report=state["merged_report"], human_decision=state["human_decision"]
    )
    result = _call_agent(prompt, "Final Report")
    return {"final_report": result}


# ---------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------

def build_graph():
    graph = StateGraph(SRSWorkflowState)

    graph.add_node("document_analyzer", document_analyzer_node)
    graph.add_node("requirement_agent", requirement_agent_node)
    graph.add_node("risk_agent", risk_agent_node)
    graph.add_node("architecture_agent", architecture_agent_node)
    graph.add_node("test_case_agent", test_case_agent_node)
    graph.add_node("merge_results", merge_results_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("generate_final_report", final_report_node)

    graph.set_entry_point("document_analyzer")

    # Fan-out #1: Document Analyzer -> Requirement Agent AND Risk Agent
    # (both edges from the same source run in the same superstep, i.e.
    # genuinely in parallel, not one after the other).
    graph.add_edge("document_analyzer", "requirement_agent")
    graph.add_edge("document_analyzer", "risk_agent")

    # Each branch continues independently.
    graph.add_edge("requirement_agent", "architecture_agent")
    graph.add_edge("risk_agent", "test_case_agent")

    # Fan-in: Merge Results only runs once BOTH architecture_agent and
    # test_case_agent have completed (LangGraph waits for all incoming
    # edges of a node before scheduling it).
    graph.add_edge("architecture_agent", "merge_results")
    graph.add_edge("test_case_agent", "merge_results")

    graph.add_edge("merge_results", "human_review")
    graph.add_edge("human_review", "generate_final_report")
    graph.add_edge("generate_final_report", END)

    # A checkpointer is required for interrupt()/resume to work -- it's
    # what persists state across the pause. MemorySaver keeps it in
    # process memory; swap for a persistent checkpointer (e.g. Postgres,
    # SQLite) in a real deployment so a pause can survive a restart.
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------
# Pretty-printing helpers
# ---------------------------------------------------------------------

def print_merged_report(merged_report: Dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print("MERGED RESULTS -- awaiting human review")
    print("=" * 70)
    doc = merged_report.get("document_summary", {})
    print(f"\nSummary: {doc.get('summary', '(none)')}")
    print(f"Key modules: {doc.get('key_modules', [])}")

    reqs = merged_report.get("requirements", {})
    print(f"\nFunctional requirements ({len(reqs.get('functional_requirements', []))}):")
    for r in reqs.get("functional_requirements", []):
        print(f"  - {r}")
    print(f"Non-functional requirements ({len(reqs.get('non_functional_requirements', []))}):")
    for r in reqs.get("non_functional_requirements", []):
        print(f"  - {r}")

    risks = merged_report.get("risks", {})
    print(f"\nRisks ({len(risks.get('risks', []))}):")
    for r in risks.get("risks", []):
        if isinstance(r, dict):
            print(f"  - [{r.get('severity', '?')}] {r.get('description', r)}")
        else:
            print(f"  - {r}")

    arch = merged_report.get("architecture", {})
    print(f"\nArchitecture recommendation: {arch.get('architecture_recommendation', '(none)')}")
    print(f"Components: {arch.get('components', [])}")

    tests = merged_report.get("test_cases", {})
    print(f"\nTest cases ({len(tests.get('test_cases', []))}):")
    for t in tests.get("test_cases", []):
        if isinstance(t, dict):
            print(f"  - {t.get('title', t)} (targets: {t.get('targets_risk', '?')})")
        else:
            print(f"  - {t}")
    print("\n" + "=" * 70 + "\n")


def print_final_report(final_report: Dict[str, Any]) -> None:
    print("\n" + "#" * 70)
    print(f"FINAL REPORT: {final_report.get('title', '(untitled)')}")
    print("#" * 70)
    print(f"\nExecutive Summary:\n{final_report.get('executive_summary', '(none)')}")
    print(f"\n{final_report.get('report_body', '(no report body)')}")
    print("\n" + "#" * 70)
