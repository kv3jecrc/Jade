"""
Assignment 1: The "Messy Data" Cleaner
========================================
Extracts a structured sentiment + core-issue summary from a rambling,
emotional product review, using a PromptTemplate -> LLM -> StrOutputParser
chain built with LangChain Expression Language (LCEL).

Run:
    python messy_data_cleaner.py

Requires a .env file (see ../.env.example) configuring LLM_PROVIDER and
that provider's settings. Defaults to a local Ollama model, per the
assignment's corporate-IT-restriction note -- no API key required in that
case, just a running `ollama serve` with the model pulled.
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from llm_setup import get_llm

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
    """Builds the PromptTemplate -> LLM -> StrOutputParser chain."""
    llm = get_llm(temperature=temperature)
    return review_cleaner_prompt | llm | StrOutputParser()


def main() -> None:
    chain = build_chain()

    test_review = (
        "I bought this blender yesterday and it's absolutely terrible! The lid flew off "
        "while I was making a smoothie and my whole kitchen is covered in spinach. "
        "I want a refund!"
    )

    result = chain.invoke({"messy_review": test_review})

    print("Input (messy review):")
    print(f"  {test_review}\n")
    print("Extracted output:")
    print(f"  {result.strip()}")


if __name__ == "__main__":
    main()
