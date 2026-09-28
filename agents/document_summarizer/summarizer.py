"""
summarizer.py
=============
Core summarization logic.

Strategy:
- If the document is short enough to fit comfortably in one LLM call,
  summarize it directly (DIRECT_SUMMARY_PROMPT) -- one call, fast.
- If it's longer, split it into overlapping chunks (so a fact sitting
  right at a chunk boundary isn't lost), summarize each chunk
  independently (the "map" step), then combine all the chunk summaries
  into one final summary (the "reduce" step). This is the standard
  map-reduce summarization pattern, and it's what lets this agent handle
  documents far longer than a single LLM context call could summarize
  faithfully in one shot.

The chunk-vs-direct threshold and chunk size are both configurable so
the same code works whether the underlying model has an 8K or 128K
context window.
"""

from typing import Callable, List, Optional

from langchain_core.messages import HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

from llm_setup import get_llm
from prompts import COMBINE_SUMMARIES_PROMPT, DIRECT_SUMMARY_PROMPT, MAP_CHUNK_PROMPT

# Character counts, not tokens -- a simple, model-agnostic proxy. ~4
# chars/token means this defaults to roughly a 3-4K token document
# before switching to map-reduce, which is comfortably inside even a
# small model's context window alongside the prompt and the response.
DEFAULT_DIRECT_CHAR_LIMIT = 12_000
DEFAULT_CHUNK_SIZE = 4_000
DEFAULT_CHUNK_OVERLAP = 400


def _invoke(llm, prompt: str) -> str:
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


def summarize_text(
    text: str,
    direct_char_limit: int = DEFAULT_DIRECT_CHAR_LIMIT,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    llm=None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Summarizes `text` and returns a dict describing what happened:
        {
            "strategy": "direct" | "map_reduce",
            "num_chunks": int,          # 1 for "direct"
            "summary": str,             # final bullet-point summary
            "chunk_summaries": List[str],  # empty for "direct"
        }

    `llm` can be injected (used by the test suite to swap in a fake
    model); if omitted, get_llm() is used.
    """
    text = text.strip()
    if not text:
        raise ValueError("Cannot summarize empty document text.")

    llm = llm or get_llm()
    log = on_progress or (lambda msg: None)

    if len(text) <= direct_char_limit:
        log(f"Document is {len(text)} chars (<= {direct_char_limit}); summarizing directly.")
        prompt = DIRECT_SUMMARY_PROMPT.format(document_text=text)
        summary = _invoke(llm, prompt)
        return {
            "strategy": "direct",
            "num_chunks": 1,
            "summary": summary,
            "chunk_summaries": [],
        }

    log(f"Document is {len(text)} chars (> {direct_char_limit}); using map-reduce summarization.")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_text(text)
    log(f"Split into {len(chunks)} chunks.")

    chunk_summaries: List[str] = []
    for i, chunk in enumerate(chunks, start=1):
        log(f"Summarizing chunk {i}/{len(chunks)}...")
        prompt = MAP_CHUNK_PROMPT.format(chunk_text=chunk)
        chunk_summaries.append(_invoke(llm, prompt))

    log("Combining chunk summaries into final summary...")
    combined_input = "\n\n".join(
        f"--- Section {i} ---\n{s}" for i, s in enumerate(chunk_summaries, start=1)
    )
    final_prompt = COMBINE_SUMMARIES_PROMPT.format(section_summaries=combined_input)
    final_summary = _invoke(llm, final_prompt)

    return {
        "strategy": "map_reduce",
        "num_chunks": len(chunks),
        "summary": final_summary,
        "chunk_summaries": chunk_summaries,
    }
