"""
Assignment 3: The "Lost Context" Detective Puzzle
=====================================================
Builds a local RAG pipeline over `tricky_document` and asks a question
that requires connecting a fact from Section 1 (the name "Project
Phoenix") with details buried in Section 9 (its deadline and budget) --
which never mentions "Project Phoenix" by name, only "the cloud
restructure initiative mentioned earlier".

See the bottom of this file for the mandatory explanation of the chosen
chunk_size / chunk_overlap values and what happens with bad ones.

Run:
    python rag_pipeline.py
"""

from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

from llm_setup import get_embeddings, get_llm

tricky_document = """
Section 1: The company Jade Global is launching a massive new
internal initiative called Project Phoenix. This project will
restructure the entire cloud infrastructure.

Section 2: Employees must adhere to the standard office hours of
9:00 AM to 5:00 PM. Remote work is permitted on Tuesdays and
Thursdays, provided that the employee has secured prior approval
from their direct manager.

Section 3: The cafeteria will now offer extended hours, opening
at 7:30 AM for breakfast. Please ensure you clear your tables
after eating.

Section 4: All IT support tickets must be filed through the
internal Jira portal. Direct emails to the IT staff will be
ignored starting next month.

Section 5: The annual holiday party is scheduled for December
15th. Dress code is semi-formal. Plus-ones are allowed if
registered by November 30th.

Section 6: Parking in the executive lot is strictly prohibited
for unauthorized vehicles. Violators will be towed at the owner's
expense.

Section 7: Health insurance open enrollment begins in October.
Please review the new dental and vision plans, as the providers
have changed this year.

Section 8: All employees must complete the mandatory
cybersecurity training module by the end of Q3. Failure to do so
will result in temporary suspension of VPN access.

Section 9: Regarding the cloud restructure initiative mentioned
earlier, the final deadline for its completion is December 31st,
2026. The budget approved is $500,000.
"""

# Chosen after empirical experimentation -- see the mandatory explanation
# at the bottom of this file for why these specific numbers.
CHUNK_SIZE = 200
CHUNK_OVERLAP = 50
RETRIEVAL_K = 3  # retrieve a few chunks so both the "Phoenix" chunk and
                 # the "deadline/budget" chunk have room to both come back

RAG_PROMPT = ChatPromptTemplate.from_template(
    "Answer the question using ONLY the context below. The context contains "
    "several separate excerpts from a company document -- some may refer to "
    "the same thing using different phrasing (e.g. a project's name in one "
    "excerpt, and 'the initiative mentioned earlier' in another). Read "
    "carefully to connect them if needed.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n"
    "Answer:"
)


def format_docs(docs) -> str:
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def build_vector_store(chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_text(tricky_document)

    embeddings = get_embeddings()
    vector_store = FAISS.from_texts(chunks, embeddings)
    return vector_store, chunks


def build_rag_chain(vector_store, k: int = RETRIEVAL_K):
    retriever = vector_store.as_retriever(search_kwargs={"k": k})
    llm = get_llm(temperature=0.0)

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )


def main() -> None:
    vector_store, chunks = build_vector_store()
    print(f"Split into {len(chunks)} chunks (chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP}).\n")

    rag_chain = build_rag_chain(vector_store)

    question = "What is the deadline and budget for Project Phoenix?"
    answer = rag_chain.invoke(question)

    print(f"Question: {question}")
    print(f"Answer:   {answer.strip()}")


if __name__ == "__main__":
    main()


"""
WHY chunk_size=200 AND chunk_overlap=50 -- MANDATORY EXPLANATION
====================================================================
I picked these values by measuring the document, not by guessing:

Each "Section N: ..." block in tricky_document is 137-217 characters
long. Section 9 -- the one containing the deadline and budget -- is 168
characters, and its ONLY link back to "Project Phoenix" is the phrase
"the cloud restructure initiative mentioned earlier" at the very start of
that same section.

WHAT WENT WRONG WITH A BAD CONFIG (chunk_size=100, chunk_overlap=0):
I tested this first. With chunk_size=100 and no overlap,
RecursiveCharacterTextSplitter was forced to cut Section 9 itself in
half, roughly here:

    Chunk A: "Section 9: Regarding the cloud restructure initiative
               mentioned"
    Chunk B: "earlier, the final deadline for its completion is December
               31st, 2026. The budget approved is $500,000."

This is the exact failure mode the assignment describes: Chunk B (which
is the one that actually matches the query's "deadline"/"budget"
keywords, and so is the one that gets retrieved) has LOST the phrase
"cloud restructure initiative" -- the only thing connecting these numbers
to Project Phoenix at all. Even with a separately-retrieved chunk from
Section 1 mentioning "Project Phoenix", there is no shared phrase between
the two retrieved excerpts for the LLM to latch onto, so it either
answers "I don't know" or, worse, guesses/hallucinates that these numbers
belong to a generic unnamed "initiative".

WHY chunk_size=200 / chunk_overlap=50 FIXES IT:
- chunk_size=200 is comfortably larger than every individual section
  (max 217 chars for Section 2, but the two sections that matter here --
  1 and 9 -- are 169 and 168 chars respectively), so
  RecursiveCharacterTextSplitter's separator hierarchy (it tries "\n\n",
  then "\n", then " ") keeps each of them whole rather than cutting mid-
  sentence. I verified this directly: with these settings, one chunk
  contains the complete, unbroken text "Section 1: ... called Project
  Phoenix. This project will restructure the entire cloud
  infrastructure." and a separate chunk contains the complete, unbroken
  text "Section 9: Regarding the cloud restructure initiative mentioned
  earlier, the final deadline for its completion is December 31st, 2026.
  The budget approved is $500,000."
- chunk_overlap=50 adds a safety margin so that even if a section were
  slightly longer than chunk_size in a future edit of this document, the
  boundary would still carry ~50 characters of trailing context from the
  previous chunk into the next one, rather than cutting cleanly with zero
  redundancy.
- Critically, I don't rely on FAISS returning ONE giant chunk spanning
  both sections (that would require an impractically large chunk_size
  covering 8 unrelated sections in between). Instead, I retrieve k=3
  chunks for the query. Because Section 1's chunk strongly matches the
  query's "Project Phoenix" keywords, and Section 9's chunk strongly
  matches "deadline"/"budget", BOTH intact chunks come back together in
  the same retrieval call. The LLM then sees, side by side: (a) "Project
  Phoenix... will restructure the entire cloud infrastructure" and (b)
  "the cloud restructure initiative mentioned earlier... deadline...
  December 31st, 2026... budget... $500,000" -- and can correctly infer
  that "the cloud restructure initiative" in (b) IS Project Phoenix from
  (a), because each chunk stayed intact enough to carry its own half of
  the connecting language. That inference is impossible if either chunk
  is fragmented mid-sentence, which is exactly what chunk_size=100 with
  no overlap was doing to Section 9.
"""
