"""
Assignment 1: The "Confused Agent" Routing Challenge
=======================================================
Routes ambiguous, non-technical user requests to the correct tool
(refund_order vs cancel_subscription) using ONLY the LLM's own reading of
each tool's docstring via `llm.bind_tools([...])` -- no if/else, no
keyword matching, no manual routing logic anywhere in this file. Whatever
tool name the model returns in `response.tool_calls` is looked up in a
dispatch dict and executed.

Run:
    python agent.py

Note: your OLLAMA_MODEL must support tool/function calling (e.g. llama3.1,
llama3.2, qwen2.5, mistral-nemo). Not every Ollama model does.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from llm_setup import get_llm
from tools import TOOLS, TOOLS_BY_NAME

SYSTEM_PROMPT = (
    "You are a billing assistant for a SaaS platform. Based on the user's "
    "request, call exactly one of the available tools to handle it. Read "
    "each tool's description carefully -- they are worded precisely to "
    "distinguish a one-time refund from canceling future recurring "
    "billing, which are very different actions."
)


def route_and_execute(llm_with_tools, user_message: str) -> dict:
    """
    Sends the user's message to the LLM (with tools bound), reads back
    whichever tool it chose to call, and executes that exact tool. This
    function contains no logic that inspects the user's wording itself --
    the tool choice comes entirely from `response.tool_calls`.
    """
    response = llm_with_tools.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_message)]
    )

    if not response.tool_calls:
        return {
            "selected_tool": None,
            "args": None,
            "output": f"No tool was selected. Model responded instead: {response.content}",
        }

    call = response.tool_calls[0]
    tool_name = call["name"]
    tool_args = call["args"]

    selected_tool = TOOLS_BY_NAME[tool_name]
    output = selected_tool.invoke(tool_args)

    return {"selected_tool": tool_name, "args": tool_args, "output": output}


def run_test_case(llm_with_tools, label: str, user_message: str, expected_tool: str) -> None:
    print(f"=== {label} ===")
    print(f'User Input: "{user_message}"')

    result = route_and_execute(llm_with_tools, user_message)

    print(f"Agent selected tool: {result['selected_tool']}")
    print(f"Tool arguments: {result['args']}")
    print(f"Tool output: {result['output']}")

    passed = result["selected_tool"] == expected_tool
    print(f"Expected tool: {expected_tool} -> {'PASS' if passed else 'FAIL'}")
    print()


def main() -> None:
    llm = get_llm(temperature=0.0)
    llm_with_tools = llm.bind_tools(TOOLS)

    run_test_case(
        llm_with_tools,
        label="Cancel Test",
        user_message="I don't want to use your software anymore, stop charging john@email.com.",
        expected_tool="cancel_subscription",
    )

    run_test_case(
        llm_with_tools,
        label="Refund Test",
        user_message="My last charge of $50 on ID #TXN991 was a mistake, give it back.",
        expected_tool="refund_order",
    )


if __name__ == "__main__":
    main()
