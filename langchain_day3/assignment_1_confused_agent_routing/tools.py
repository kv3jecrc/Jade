"""
tools.py
========
Two custom tools for a SaaS billing agent. The Docstrings below are the
SOLE mechanism the Agent uses to decide which tool to call -- there is no
keyword matching or if/else routing logic anywhere in this project. The
Agent sees these docstrings (via LangChain's @tool decorator, which turns
them into the tool's schema description sent to the model) and must infer
the right choice purely from how precisely and unambiguously they're
written.
"""

from langchain_core.tools import tool


@tool
def refund_order(transaction_id: str) -> str:
    """Reverses a SINGLE, already-completed PAST transaction and returns
    that one specific payment back to the customer.

    Use this ONLY when the user is asking for money back for something
    they were ALREADY charged for in the past -- a one-time reversal of a
    specific past charge. This does NOT stop or affect any future or
    recurring billing; the customer's subscription (if any) remains
    active and will continue to be billed normally going forward.

    Typical user language that means THIS tool: "refund", "give my money
    back", "that charge was a mistake", "I want a refund for my last
    payment", mentioning a specific past charge, amount, date, or
    transaction ID.

    Args:
        transaction_id: The ID of the specific past transaction to
            reverse (e.g. "TXN991"). If the user did not give an exact
            ID but clearly refers to one specific recent charge (by
            amount, date, or description), use the best identifying
            string they provided as the transaction_id.
    """
    return f"Refund processed for transaction {transaction_id}."


@tool
def cancel_subscription(email: str) -> str:
    """Stops ALL future recurring/subscription payments for a customer's
    account going forward, permanently ending their subscription.

    Use this ONLY when the user wants to stop being charged in the
    FUTURE, end their subscription, or stop ongoing/recurring billing --
    NOT when they are asking for money back for a charge that has
    already happened. This tool does NOT reverse or refund any past
    charge; it only prevents new ones from occurring.

    Typical user language that means THIS tool: "cancel my subscription",
    "stop charging me", "stop taking money from my account", "I don't
    want to use your software anymore", "stop billing me", "end my
    membership".

    Args:
        email: The email address associated with the customer's account
            whose subscription should be canceled.
    """
    return f"Subscription canceled for {email}. No further recurring charges will be made."


# Dispatch table used to invoke whichever tool the model decides to call,
# keyed by tool name. This is a lookup, not conditional branching -- the
# actual routing DECISION is made entirely by the LLM based on the
# docstrings above; this dict only maps "the model chose X" to "call X".
TOOLS = [refund_order, cancel_subscription]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
