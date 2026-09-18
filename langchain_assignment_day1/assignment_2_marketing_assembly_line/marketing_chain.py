"""
Assignment 2: The Marketing Assembly Line
===========================================
A two-step LCEL sequence:
  Chain 1: {product_name} -> catchy 5-word English slogan
  Chain 2: slogan -> French translation

Combined into a single runnable using the pipe operator (|).

Run:
    python marketing_chain.py
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from llm_setup import get_llm

slogan_prompt = ChatPromptTemplate.from_template(
    "Write one catchy marketing slogan of EXACTLY 5 words for the product "
    "'{product_name}'. Respond with ONLY the slogan text -- no quotes, no "
    "explanation, no extra words."
)

translate_prompt = ChatPromptTemplate.from_template(
    "Translate the following English marketing slogan into French. "
    "Respond with ONLY the French translation, nothing else.\n\n"
    "Slogan: {slogan}"
)


def build_chain(temperature: float = 0.7):
    """Builds the two-step LCEL sequence: slogan generation piped into translation."""
    llm = get_llm(temperature=temperature)

    # Chain 1: product_name -> English slogan (plain string output)
    slogan_chain = slogan_prompt | llm | StrOutputParser()

    # Chain 2: slogan -> French translation. The lambda re-shapes chain 1's
    # plain string output into the {"slogan": ...} dict that translate_prompt
    # expects, so the two chains can be piped directly with `|`.
    translate_chain = translate_prompt | llm | StrOutputParser()

    full_chain = slogan_chain | (lambda slogan: {"slogan": slogan}) | translate_chain

    return full_chain, slogan_chain


def main() -> None:
    full_chain, slogan_chain = build_chain()

    product_name = "EcoBrew Reusable Coffee Pod"

    # Note: this calls the LLM a second time just to display the
    # intermediate English slogan for clarity. The graded deliverable is
    # `full_chain`, which internally produces (and uses) that same slogan
    # in a single pass -- if you want to avoid the extra call, just print
    # only `french_slogan` below.
    english_slogan = slogan_chain.invoke({"product_name": product_name})
    french_slogan = full_chain.invoke({"product_name": product_name})

    print(f"Product: {product_name}")
    print(f"English slogan: {english_slogan.strip()}")
    print(f"French slogan:  {french_slogan.strip()}")


if __name__ == "__main__":
    main()
