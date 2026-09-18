"""
Assignment 4: The "Fast & Grounded" System
=============================================
A generation function that is both cheap (a plain dict-based query cache
to avoid repeat API calls) and strictly grounded (a system prompt that
forces an EXACT fallback phrase whenever the answer isn't in the given
context, rather than letting the model guess or hallucinate).

Run:
    python fast_and_grounded.py
"""

from typing import Dict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from llm_setup import get_llm

REQUIRED_FALLBACK_PHRASE = "I do not have enough information"

CONTEXT = """Company Policy Handbook (excerpt):
- Employees are entitled to 20 days of paid vacation per year.
- Remote work is allowed up to 3 days per week, subject to manager approval.
- All expense reports must be submitted within 30 days of purchase.
- The standard workday is 9:00 AM to 5:00 PM, with a one-hour lunch break.
"""

GROUNDED_PROMPT = ChatPromptTemplate.from_template(
    "You are a strictly grounded assistant. Answer the question using ONLY "
    "the context below. Do not use any outside knowledge, and do not guess "
    "or infer beyond what the context states.\n\n"
    f'If, and only if, the answer cannot be found in the context, respond '
    f'with EXACTLY this phrase and nothing else: "{REQUIRED_FALLBACK_PHRASE}"\n\n'
    "Context:\n{context}\n\n"
    "Question: {question}\n"
    "Answer:"
)

# Simple in-memory cache: question text -> answer text.
query_cache: Dict[str, str] = {}


def build_chain(temperature: float = 0.0):
    llm = get_llm(temperature=temperature)
    return GROUNDED_PROMPT | llm | StrOutputParser()


def answer_question(chain, question: str) -> str:
    """
    Checks query_cache BEFORE calling the LLM.
      - Cache hit: prints "Returned from Cache: <answer>" and returns
        immediately, without touching the LLM at all.
      - Cache miss: calls the LLM, stores the (question, answer) pair in
        the cache, and returns the answer.
    """
    if question in query_cache:
        cached_answer = query_cache[question]
        print(f"Returned from Cache: {cached_answer}")
        return cached_answer

    answer = chain.invoke({"context": CONTEXT, "question": question}).strip()
    query_cache[question] = answer
    return answer


def main() -> None:
    chain = build_chain()

    # --- Scenario 1: First ask (valid, in-context question) ---
    q1 = "How many vacation days do employees get per year?"
    print("Scenario 1 (First Ask):")
    print(f"  Question: {q1}")
    answer1 = answer_question(chain, q1)
    print(f"  LLM Response: {answer1}\n")

    # --- Scenario 2: Cache hit (the exact same question again) ---
    print("Scenario 2 (Cache Hit):")
    print(f"  Question: {q1}")
    answer_question(chain, q1)  # prints "Returned from Cache: ..." itself
    print()

    # --- Scenario 3: Grounding test (out-of-context question) ---
    q3 = "What is the recipe for a chocolate cake?"
    print("Scenario 3 (Grounding Test):")
    print(f"  Question: {q3}")
    answer3 = answer_question(chain, q3)
    print(f"  LLM Response: {answer3}")

    matches_required_phrase = answer3 == REQUIRED_FALLBACK_PHRASE
    print(f"  Matches required exact phrase: {matches_required_phrase}")
    if not matches_required_phrase:
        print(
            "  Note: the model did not reproduce the fallback phrase exactly "
            "(e.g. added punctuation or extra words). Tighten the prompt "
            "further, or lower temperature, if strict exact-match is required."
        )


if __name__ == "__main__":
    main()
