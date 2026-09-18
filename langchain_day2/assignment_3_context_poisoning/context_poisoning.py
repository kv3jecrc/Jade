"""
Assignment 3: Solving "Context Poisoning"
============================================
Two contradictory WFH-policy documents are embedded into the same FAISS
vector store, tagged with different `year` metadata. A custom retrieval
function accepts a `filter_year` and uses FAISS's metadata filter to
retrieve ONLY that year's document -- so the LLM's context never contains
the outdated, contradictory policy, and can't get "poisoned" by it.

Run:
    python context_poisoning.py
"""

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from llm_setup import get_embeddings, get_llm

POLICY_DOCS = [
    Document(
        page_content="Company WFH Policy: Work from home is strictly banned.",
        metadata={"year": 2022},
    ),
    Document(
        page_content="Company WFH Policy: Work from home is allowed 3 days a week.",
        metadata={"year": 2024},
    ),
]

ANSWER_PROMPT = ChatPromptTemplate.from_template(
    "Answer the question using ONLY the context below.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n"
    "Answer:"
)


def build_vector_store():
    embeddings = get_embeddings()
    return FAISS.from_documents(POLICY_DOCS, embeddings)


def retrieve_with_year_filter(vector_store: FAISS, user_query: str, filter_year: int, k: int = 3):
    """
    Custom retrieval function that does NOT do a plain, unfiltered semantic
    search. It applies a metadata filter so the vector store only considers
    documents tagged with `filter_year`, completely excluding any other
    year's (contradictory) policy from being retrieved -- this is what
    prevents context poisoning.
    """
    return vector_store.similarity_search(user_query, k=k, filter={"year": filter_year})


def answer_with_filtered_context(user_query: str, filter_year: int) -> None:
    vector_store = build_vector_store()

    print(f'User Query: "{user_query}"')
    print(f"Active Filter: Year: {filter_year}")

    retrieved_docs = retrieve_with_year_filter(vector_store, user_query, filter_year)

    print("Retrieved Context:")
    for doc in retrieved_docs:
        print(f"  [year={doc.metadata['year']}] {doc.page_content}")

    context = "\n".join(doc.page_content for doc in retrieved_docs)
    llm = get_llm(temperature=0.0)
    chain = ANSWER_PROMPT | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": user_query})

    print(f"LLM Final Answer: {answer.strip()}")


def main() -> None:
    answer_with_filtered_context(
        user_query="What is the WFH policy?",
        filter_year=2024,
    )


if __name__ == "__main__":
    main()
