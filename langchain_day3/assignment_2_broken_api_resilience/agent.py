"""
Assignment 2: Agent Resilience - The Broken API Challenge
=============================================================
A ReAct agent with a primary tool (get_internal_stock_price) that always
fails, and a backup tool (search_public_web) that works. Demonstrates
that the agent can recognize the failure from the Observation and
autonomously pivot to the backup tool, rather than giving up or
hallucinating an answer.

Run:
    python agent.py

Requires langchain<0.4 (this uses the classic create_react_agent +
AgentExecutor API -- see ../requirements.txt).
"""

import re

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

from llm_setup import get_llm
from tools import TOOLS

REACT_PROMPT_TEMPLATE = """Answer the following question as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

If a tool returns an error or failure message, do NOT give up or guess --
try a different available tool that might be able to answer the question
instead.

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

react_prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)


def build_agent_executor() -> AgentExecutor:
    llm = get_llm(temperature=0.0)
    agent = create_react_agent(llm, TOOLS, react_prompt)
    return AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=False,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        max_iterations=6,
    )


def _extract_thought(action_log: str) -> str:
    return re.split(r"\nAction:", action_log, maxsplit=1)[0].strip()


def run_and_trace(question: str) -> dict:
    executor = build_agent_executor()
    result = executor.invoke({"input": question})

    tools_used = []
    for i, (action, observation) in enumerate(result["intermediate_steps"], start=1):
        thought = _extract_thought(action.log)
        print(f"Thought {i}: {thought}")
        print(f'Action {i}: [{action.tool}: "{action.tool_input}"]')
        print(f'Observation {i}: ["{observation}"]')
        tools_used.append(action.tool)

    print(f"Final Answer: [{result['output']}]")

    return {"output": result["output"], "tools_used": tools_used}


def main() -> None:
    question = "What is the current stock price of Apple?"
    print(f"Question: {question}\n")

    result = run_and_trace(question)

    print()
    used_primary = "get_internal_stock_price" in result["tools_used"]
    used_backup = "search_public_web" in result["tools_used"]
    recovered = used_primary and used_backup
    print(f"Attempted primary tool: {used_primary}")
    print(f"Recovered via backup tool: {used_backup}")
    print(f"Demonstrates autonomous recovery: {recovered}")


if __name__ == "__main__":
    main()
