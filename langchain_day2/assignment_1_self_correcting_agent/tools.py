"""
tools.py
========
The two tools the agent has access to, each deliberately limited per the
assignment's constraints:

- CalculatorTool: does arithmetic on numbers it's given. Has NO access to
  any external data -- it cannot look anything up.
- SearchTool: looks up factual/historical information from Wikipedia
  (free, no API key required). It CANNOT perform math.

This split is what creates the "logic trap" in Assignment 1: a prompt
that says "multiply X by 5" tempts the agent to reach for the calculator
immediately, even though it doesn't yet know what X is.
"""

import ast
import operator
from typing import Union

from langchain_core.tools import Tool

# ---------------------------------------------------------------------
# Calculator Tool
# ---------------------------------------------------------------------

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> Union[int, float]:
    """Evaluates a parsed arithmetic AST node, allowing only numeric
    constants and +, -, *, / (and unary +/-). Deliberately NOT Python's
    `eval()` -- this cannot execute arbitrary code, only arithmetic."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed.")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported or unsafe expression component: {ast.dump(node)}")


def calculator_tool_func(expression: str) -> str:
    """Evaluates a basic arithmetic expression like '1879 * 5'. Constraint:
    cannot access any external data -- it only computes what it's given."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree.body)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return str(result)
    except Exception as exc:
        return f"Error: could not evaluate '{expression}' ({exc})"


calculator_tool = Tool(
    name="CalculatorTool",
    func=calculator_tool_func,
    description=(
        "Performs basic arithmetic (add, subtract, multiply, divide) on numbers "
        "you already know. Input should be a plain math expression, e.g. "
        "'1879 * 5'. This tool has NO access to external facts or data -- it "
        "can only compute the math expression you give it."
    ),
)

# ---------------------------------------------------------------------
# Search Tool (Wikipedia -- free, no API key required)
# ---------------------------------------------------------------------


def _build_search_tool() -> Tool:
    from langchain_community.tools import WikipediaQueryRun
    from langchain_community.utilities import WikipediaAPIWrapper

    wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=500)
    wiki = WikipediaQueryRun(api_wrapper=wrapper)

    return Tool(
        name="SearchTool",
        func=wiki.run,
        description=(
            "Looks up up-to-date factual or historical information (e.g. birth "
            "years, dates, definitions) from Wikipedia. Constraint: this tool "
            "CANNOT perform math -- it only retrieves text."
        ),
    )


search_tool = _build_search_tool()
