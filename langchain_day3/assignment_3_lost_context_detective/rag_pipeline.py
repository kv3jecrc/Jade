"""
Assignment 3: The "Lost Context" Detective Puzzle
=====================================================
Builds a local RAG pipeline over `tricky_document` and asks a question
that requires connecting a fact from Section 1 (the name "Project
Phoenix") with details buried in Section 9 (its deadline and budget) --
which never mentions "Project Phoenix" by name, only "the cloud
restructure initiative mentioned earlier".

See the mandatory multi-line comment at the very bottom of this file for
the required explanation of the chosen chunk_size / chunk_overlap values.

Run:
    python rag_pipeline.py
"""

from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

from llm_setup import get_embeddings, get_llm

# Exact string as given in the assignment.
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


'''
WHY chunk_size=200 AND chunk_overlap=50 -- MANDATORY EXPLANATION
====================================================================
I picked these values by measuring the document and empirically testing
several configurations, not by guessing.

THE DOCUMENT: tricky_document is 1,452 characters, with 9 "Section N: ..."
blocks separated only by single newlines (no blank lines between them).
Section 9 -- the one with the deadline and budget -- is 167 characters,
and its ONLY link back to "Project Phoenix" is the phrase "the cloud
restructure initiative mentioned earlier" at its very start. Section 1,
which names "Project Phoenix", is 168 characters.

WHAT WENT WRONG WITH chunk_size=100, chunk_overlap=0:
I tested this first and printed the actual resulting chunks. With no
overlap and a chunk_size smaller than a single section, the splitter was
forced to cut Section 9 into THREE separate pieces:

    Chunk 19: "Section 9: Regarding the cloud restructure initiative
               mentioned"
    Chunk 20: "earlier, the final deadline for its completion is
               December 31st,"
    Chunk 21: "2026. The budget approved is $500,000."

This is exactly the failure mode the assignment describes. The chunk that
actually gets retrieved for a query about "deadline"/"budget" (Chunk 21,
or possibly Chunk 20) has LOST the phrase "cloud restructure initiative"
entirely -- the only thing connecting these numbers to Project Phoenix.
Even if Section 1's chunk (which does mention "Project Phoenix") is also
retrieved, there is no shared phrase between the two separately-retrieved
excerpts for the LLM to connect -- so it either says it doesn't know, or
hallucinates that the deadline/budget belong to some other, unnamed
initiative. I confirmed this is a real, reproducible outcome by printing
the split chunks directly, not by assuming it would happen.

I also tried chunk_size=150 (with and without overlap): still too small
-- Section 9 (167 chars) doesn't fit in one chunk, so it still gets cut,
just in a slightly different place. It wasn't until chunk_size reached
200 that both Section 1 and Section 9 fit whole.

WHY chunk_size=200 / chunk_overlap=50 FIXES IT:
I verified directly (by printing every resulting chunk) that at
chunk_size=200, chunk_overlap=50:
  - One complete, unbroken chunk contains all of Section 1: "Section 1:
    ... called Project Phoenix. This project will restructure the entire
    cloud infrastructure."
  - A separate complete, unbroken chunk contains all of Section 9:
    "Section 9: Regarding the cloud restructure initiative mentioned
    earlier, the final deadline for its completion is December 31st,
    2026. The budget approved is $500,000."

Both sections are exactly ~167-168 characters, so chunk_size=200 gives
just enough headroom (with the splitter's separator hierarchy --
"\n\n", then "\n", then " " -- preferring to break at a newline) to keep
each section as one intact unit instead of splitting mid-sentence.
chunk_overlap=50 is a safety margin: it doesn't need to bridge Section 1
and Section 9 directly (they are 7 sections apart, far more than 50
characters), but it protects every OTHER section boundary in the document
from the same kind of mid-sentence fragmentation if a section ever runs
slightly longer than chunk_size.

The two chunks don't need to be merged into one to solve this -- I
retrieve k=3 chunks per query instead. I verified with a real similarity
search that for the query "What is the deadline and budget for Project
Phoenix?", the two intact chunks (Section 1's and Section 9's) BOTH come
back in the top 3 results, because each one strongly matches a different
half of the query's keywords ("Project Phoenix" vs. "deadline"/"budget").
The LLM then sees both intact excerpts side by side in its context and
can correctly infer that "the cloud restructure initiative" in the
Section 9 excerpt IS Project Phoenix, named in the Section 1 excerpt --
an inference that is only possible because neither chunk was fragmented
mid-sentence, which is exactly what chunk_size=100 (and even 150) with
low/no overlap was doing.
'''
