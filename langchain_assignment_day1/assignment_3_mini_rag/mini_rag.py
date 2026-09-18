"""
Assignment 3: Mini-RAG (Retrieval-Augmented Generation)
=========================================================
Loads game_rules.txt, splits it into chunks, embeds the chunks into an
in-memory FAISS vector store, retrieves the chunks relevant to a question,
and asks the LLM to answer using ONLY that retrieved context -- so the
model is not relying on rules it was never actually told about.

Run:
    python mini_rag.py
"""

from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

from llm_setup import get_embeddings, get_llm

RULES_FILE = Path(__file__).parent / "game_rules.txt"

RAG_PROMPT = ChatPromptTemplate.from_template(
    "Answer the question using ONLY the context below. If the answer is not "
    "contained in the context, say you don't know -- do not use outside "
    "knowledge.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n"
    "Answer:"
)


def format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def build_vector_store():
    """Loads game_rules.txt, chunks it, and embeds the chunks into FAISS."""
    loader = TextLoader(str(RULES_FILE))
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    chunks = splitter.split_documents(documents)

    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(chunks, embeddings)
    return vector_store, chunks


def build_rag_chain(vector_store, k: int = 2):
    """Builds the retriever -> prompt -> LLM -> parser RAG chain."""
    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    llm = get_llm(temperature=0.0)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )
    return rag_chain


def main() -> None:
    vector_store, chunks = build_vector_store()
    print(f"Loaded and embedded {len(chunks)} chunk(s) from {RULES_FILE.name}\n")

    rag_chain = build_rag_chain(vector_store)

    question = "How many points is the golden token worth?"
    answer = rag_chain.invoke(question)

    print(f"Question: {question}")
    print(f"Answer:   {answer.strip()}")


if __name__ == "__main__":
    main()
