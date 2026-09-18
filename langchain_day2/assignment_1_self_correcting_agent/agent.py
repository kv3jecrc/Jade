"""
Assignment 1: Build a Self-Correcting LangChain Agent
========================================================
A ReAct agent (LLM + CalculatorTool + SearchTool) that must navigate the
"multiply the birth year of Einstein by 5" logic trap: the word "multiply"
tempts an immediate calculator call, but the agent doesn't know the birth
year yet, so it must search first, then calculate.

This prints the exact Thought/Action/Observation/Final Answer trace the
assignment asks for, built from the agent's REAL `intermediate_steps`
(not fabricated) -- see `run_and_trace()`.

Run:
    python agent.py
"""

import re

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

from llm_setup import get_llm
from tools import calculator_tool, search_tool

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

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

react_prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)


def build_agent_executor(verbose: bool = False) -> AgentExecutor:
    llm = get_llm(temperature=0.0)
    tools = [search_tool, calculator_tool]
    agent = create_react_agent(llm, tools, react_prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        max_iterations=6,
    )


def _extract_thought(action_log: str) -> str:
    """The ReAct prompt already supplies the literal 'Thought:' label right
    before the model's completion, so `action.log` starts just after it.
    This pulls out only the reasoning text, stripping the 'Action: ...' /
    'Action Input: ...' lines that the same log string also contains."""
    return re.split(r"\nAction:", action_log, maxsplit=1)[0].strip()


def run_and_trace(question: str) -> str:
    """Runs the agent and prints its REAL intermediate steps (not a
    scripted/fabricated trace) in the assignment's required format."""
    executor = build_agent_executor()
    result = executor.invoke({"input": question})

    for i, (action, observation) in enumerate(result["intermediate_steps"], start=1):
        thought = _extract_thought(action.log)
        print(f"Thought {i}: {thought}")
        print(f'Action {i}: [{action.tool}: "{action.tool_input}"]')
        print(f'Observation {i}: ["{observation}"]')

    print(f"Final Answer: [{result['output']}]")
    return result["output"]


def main() -> None:
    question = "Multiply the birth year of Albert Einstein by 5."
    print(f"Question: {question}\n")
    run_and_trace(question)


if __name__ == "__main__":
    main()
