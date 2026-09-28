#!/usr/bin/env python3
"""
main.py
=======
CLI entry point for the Document Summarizer agent.

Usage:
    python main.py --file report.pdf
    python main.py --file notes.docx --output summary.txt
    python main.py --text "paste raw text here"
    echo "some text" | python main.py --stdin
"""

import argparse
import sys

from document_loader import load_text
from summarizer import summarize_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a document into short, easy-to-understand bullet points.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=str, help="Path to a .txt, .md, .pdf, or .docx file.")
    source.add_argument("--text", type=str, help="Raw text to summarize, passed directly on the command line.")
    source.add_argument("--stdin", action="store_true", help="Read the document text from stdin.")
    parser.add_argument("--output", type=str, default=None, help="Optional path to write the summary to (also prints to stdout).")
    args = parser.parse_args()

    if args.file:
        document_text = load_text(args.file)
    elif args.text:
        document_text = args.text
    else:
        document_text = sys.stdin.read()

    def log(msg: str) -> None:
        print(f"[Document Summarizer] {msg}", file=sys.stderr)

    result = summarize_text(document_text, on_progress=log)

    print(f"\nStrategy used: {result['strategy']} ({result['num_chunks']} chunk(s))\n")
    print(result["summary"])

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result["summary"])
        print(f"\nSummary written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
