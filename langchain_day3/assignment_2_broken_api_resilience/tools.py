"""
tools.py
========
A deliberately-failing primary tool (simulating a database outage) and a
functioning backup tool, for testing whether the agent can autonomously
recover by switching tools after a failure.
"""

from langchain_core.tools import Tool


def get_internal_stock_price_func(ticker: str) -> str:
    """Simulates the internal stock price database being down. Always
    fails, regardless of input, so the agent is forced to recover."""
    return "Error: Database Timeout"


# A tiny mock "web search index" so the backup tool's answer isn't
# hardcoded to one specific ticker.
_MOCK_SEARCH_RESULTS = {
    "apple": "Apple stock is at $170",
    "aapl": "Apple stock is at $170",
    "google": "Google (Alphabet) stock is at $142",
    "googl": "Google (Alphabet) stock is at $142",
}


def search_public_web_func(query: str) -> str:
    """Mock public web search -- returns a canned result if the query
    mentions a company we have mock data for, else a generic fallback."""
    query_lower = query.lower()
    for key, result in _MOCK_SEARCH_RESULTS.items():
        if key in query_lower:
            return result
    return f"Mock search result: no specific data found for query '{query}'."


get_internal_stock_price = Tool(
    name="get_internal_stock_price",
    func=get_internal_stock_price_func,
    description=(
        "Looks up a stock's current price from the company's internal, "
        "authoritative price database, given a ticker symbol (e.g. 'AAPL'). "
        "This is the preferred, primary source when it is working."
    ),
)

search_public_web = Tool(
    name="search_public_web",
    func=search_public_web_func,
    description=(
        "Searches the public web for information, including stock prices, "
        "when other sources are unavailable. Use this as a fallback if the "
        "internal database fails or returns an error."
    ),
)

TOOLS = [get_internal_stock_price, search_public_web]
