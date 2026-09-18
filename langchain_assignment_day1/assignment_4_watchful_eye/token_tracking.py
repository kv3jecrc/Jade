"""
Assignment 4: The Watchful Eye (Callbacks & Logging)
=======================================================
Re-runs Assignment 1's "messy review cleaner" chain, wrapped with a
callback that tracks token usage, and prints a formatted receipt showing
Total Tokens, Prompt Tokens, Completion Tokens, and Total Cost.

- If LLM_PROVIDER=openai: uses LangChain's built-in get_openai_callback,
  which reports real dollar cost from OpenAI's published pricing table.
- Otherwise (default: local Ollama): uses a custom callback handler below,
  since get_openai_callback only works for OpenAI models. Local models
  have no per-token API cost, so cost is reported as $0.00. Token counts
  come from the usage_metadata LangChain attaches to each AIMessage; if
  your installed langchain-ollama version doesn't populate that field for
  a given model, the receipt will show 0s and the script prints a note
  explaining why (rather than fabricating numbers).

Run:
    python token_tracking.py
"""

from typing import Any, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from llm_setup import get_llm, get_provider

# --- Reused from Assignment 1 (see assignment_1_messy_data_cleaner) ---

REVIEW_CLEANER_TEMPLATE = """You are a customer support assistant. Read the following product review, \
which may be emotional or rambling, and extract only the core information.

Review:
\"\"\"
{messy_review}
\"\"\"

Respond with ONLY a single comma-separated string in EXACTLY this format, \
with no extra words, labels, preamble, or explanation:
Sentiment: [Positive/Negative], Core Issue: [Brief summary of the problem]
"""

review_cleaner_prompt = PromptTemplate(
    input_variables=["messy_review"],
    template=REVIEW_CLEANER_TEMPLATE,
)


def build_chain(temperature: float = 0.0):
    llm = get_llm(temperature=temperature)
    return review_cleaner_prompt | llm | StrOutputParser()


# --- Custom token-usage callback for non-OpenAI (e.g. local Ollama) models ---


class LocalTokenUsageCallbackHandler(BaseCallbackHandler):
    """
    Tracks token usage across LLM calls for providers that don't have a
    built-in LangChain cost-tracking callback (get_openai_callback is
    OpenAI-specific). Reads the `usage_metadata` LangChain attaches to
    AIMessage objects when the underlying provider reports it, falling
    back to the legacy `llm_output["token_usage"]` shape some providers
    use instead.
    """

    def __init__(self) -> None:
        self.successful_requests = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.usage_reported = False  # tracks whether we ever found real numbers

    def on_llm_end(self, response, **kwargs: Any) -> None:
        self.successful_requests += 1

        for generation_list in response.generations:
            for generation in generation_list:
                usage = self._extract_usage(generation, response)
                if usage:
                    self.usage_reported = True
                    self.prompt_tokens += usage.get("prompt_tokens", 0)
                    self.completion_tokens += usage.get("completion_tokens", 0)
                    self.total_tokens += usage.get("total_tokens", 0)

    @staticmethod
    def _extract_usage(generation, response) -> Optional[dict]:
        # Preferred path: modern LangChain chat models set usage_metadata
        # directly on the AIMessage.
        message = getattr(generation, "message", None)
        usage_metadata = getattr(message, "usage_metadata", None) if message else None
        if usage_metadata:
            return {
                "prompt_tokens": usage_metadata.get("input_tokens", 0),
                "completion_tokens": usage_metadata.get("output_tokens", 0),
                "total_tokens": usage_metadata.get("total_tokens", 0),
            }

        # Fallback: some providers report usage on llm_output instead.
        llm_output = getattr(response, "llm_output", None) or {}
        token_usage = llm_output.get("token_usage") or llm_output.get("usage")
        if token_usage:
            return {
                "prompt_tokens": token_usage.get("prompt_tokens", 0),
                "completion_tokens": token_usage.get("completion_tokens", 0),
                "total_tokens": token_usage.get("total_tokens", 0),
            }

        return None

    def print_receipt(self) -> None:
        print("=" * 44)
        print("            TOKEN USAGE RECEIPT")
        print("=" * 44)
        print(f"Successful Requests : {self.successful_requests}")
        print(f"Prompt Tokens       : {self.prompt_tokens}")
        print(f"Completion Tokens   : {self.completion_tokens}")
        print(f"Total Tokens        : {self.total_tokens}")
        print(f"Total Cost          : $0.00 (self-hosted local model)")
        print("=" * 44)
        if not self.usage_reported:
            print(
                "Note: this model backend did not report token usage metadata, "
                "so the counts above are 0. This is version/backend-dependent -- "
                "see the assignment README for details."
            )


def run_with_openai_callback(chain, test_review: str) -> None:
    from langchain_community.callbacks import get_openai_callback

    with get_openai_callback() as cb:
        result = chain.invoke({"messy_review": test_review})

    print("Extracted output:")
    print(f"  {result.strip()}\n")

    print("=" * 44)
    print("            TOKEN USAGE RECEIPT")
    print("=" * 44)
    print(f"Successful Requests : {cb.successful_requests}")
    print(f"Prompt Tokens       : {cb.prompt_tokens}")
    print(f"Completion Tokens   : {cb.completion_tokens}")
    print(f"Total Tokens        : {cb.total_tokens}")
    print(f"Total Cost          : ${cb.total_cost:.6f}")
    print("=" * 44)


def run_with_local_callback(chain, test_review: str) -> None:
    handler = LocalTokenUsageCallbackHandler()
    result = chain.invoke({"messy_review": test_review}, config={"callbacks": [handler]})

    print("Extracted output:")
    print(f"  {result.strip()}\n")

    handler.print_receipt()


def main() -> None:
    chain = build_chain()

    test_review = (
        "I bought this blender yesterday and it's absolutely terrible! The lid flew off "
        "while I was making a smoothie and my whole kitchen is covered in spinach. "
        "I want a refund!"
    )

    print("Input (messy review):")
    print(f"  {test_review}\n")

    if get_provider() == "openai":
        run_with_openai_callback(chain, test_review)
    else:
        run_with_local_callback(chain, test_review)


if __name__ == "__main__":
    main()
