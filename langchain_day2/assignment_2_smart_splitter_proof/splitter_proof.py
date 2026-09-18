"""
Assignment 2: The "Smart Splitter" Proof
===========================================
Splits sample_document.txt with RecursiveCharacterTextSplitter
(chunk_size=200, chunk_overlap=50), then PROVES the overlap actually
exists by programmatically extracting the exact intersecting text between
each pair of consecutive chunks -- rather than just trusting the library.

Run:
    python splitter_proof.py
"""

from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

DOCUMENT_PATH = Path(__file__).parent / "sample_document.txt"
CHUNK_SIZE = 200
CHUNK_OVERLAP = 50


def find_overlap(chunk_a: str, chunk_b: str) -> str:
    """
    Finds the longest string that is simultaneously a SUFFIX of chunk_a and
    a PREFIX of chunk_b -- i.e. the exact overlapping text between them.

    This checks progressively shorter candidate lengths (starting from the
    theoretical maximum) rather than assuming the overlap is exactly
    CHUNK_OVERLAP characters, because RecursiveCharacterTextSplitter tries
    to break on natural boundaries (paragraphs, sentences, words) rather
    than at a fixed character offset -- so the real overlap for any given
    pair is usually close to, but not always exactly, chunk_overlap.
    """
    max_possible = min(len(chunk_a), len(chunk_b))
    for length in range(max_possible, 0, -1):
        if chunk_a[-length:] == chunk_b[:length]:
            return chunk_a[-length:]
    return ""


def load_and_split():
    loader = TextLoader(str(DOCUMENT_PATH))
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)
    return chunks


def main() -> None:
    chunks = load_and_split()
    print(f"Loaded '{DOCUMENT_PATH.name}' and split it into {len(chunks)} chunks "
          f"(chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP}).\n")

    # Required output: the first two chunks and their extracted overlap.
    chunk_1 = chunks[0].page_content
    chunk_2 = chunks[1].page_content
    overlap = find_overlap(chunk_1, chunk_2)

    print(f"Chunk 1: {chunk_1!r}\n")
    print(f"Chunk 2: {chunk_2!r}\n")
    print(f"Extracted Overlap: {overlap!r} ({len(overlap)} characters)\n")

    # Extended proof: validate overlap across EVERY consecutive pair, not
    # just the first one, and report how close each is to the configured
    # 50-character target.
    print("--- Overlap check across all consecutive chunk pairs ---")
    zero_overlap_count = 0
    for i in range(len(chunks) - 1):
        pair_overlap = find_overlap(chunks[i].page_content, chunks[i + 1].page_content)
        status = "OK" if pair_overlap else "NONE (paragraph/document boundary -- see note below)"
        if not pair_overlap:
            zero_overlap_count += 1
        print(f"  Chunk {i+1} -> Chunk {i+2}: {len(pair_overlap)} chars overlap [{status}]")

    print()
    if zero_overlap_count:
        print(
            f"Note: {zero_overlap_count} pair(s) show 0 overlap. This happens where the "
            "splitter breaks across a paragraph boundary (a stronger separator than "
            "sentences/words) and starts the next chunk fresh -- expected behavior, "
            "not a bug in the overlap-detection function."
        )


if __name__ == "__main__":
    main()
