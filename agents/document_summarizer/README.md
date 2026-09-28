# Document Summarizer Agent

An LLM-powered agent that turns a long or dense document into a short,
plain-language, bullet-point summary — while preserving every concrete
fact, number, decision, and action item.

## Why this use case is easy to stand up

Unlike most of the agents in the source catalog this was picked from,
this one has a single-component tech stack — an LLM and nothing else.
No enterprise system integration (no HRMS/LMS/ITSM API), no vector
database, no scheduler, no training data or ML model to fit. Feed it
text, get a summary back.

## How it works

- **Short documents** (under a configurable character threshold, default
  ~12,000 chars) are summarized in a single LLM call
  (`DIRECT_SUMMARY_PROMPT`).
- **Long documents** use a map-reduce strategy so quality doesn't
  degrade as length grows past what fits in one call:
  1. Split the text into overlapping chunks (`RecursiveCharacterTextSplitter`,
     overlap so a fact sitting at a chunk boundary isn't lost).
  2. **Map**: summarize each chunk independently (`MAP_CHUNK_PROMPT`).
  3. **Reduce**: combine all the chunk summaries into one coherent final
     summary (`COMBINE_SUMMARIES_PROMPT`), merging duplicates from
     adjacent, overlapping chunks.
- Supports `.txt`, `.md`, `.pdf`, and `.docx` input via `document_loader.py`,
  plus raw text or stdin.

## Project structure

```
llm_setup.py          Ollama-default, multi-provider LLM loader (see below)
prompts.py             The 3 prompts (direct / map / combine) -- also the
                        literal contents of SYSTEM_PROMPT.md
document_loader.py      .txt / .md / .pdf / .docx text extraction
summarizer.py           Core direct-vs-map-reduce summarization logic
main.py                 CLI entry point
sample_short.txt        Sample input for the direct path
sample_long.txt         Sample input (~7.4K chars) for testing map-reduce
                         with a lowered threshold
```

## Setup

```bash
pip install -r requirements.txt --break-system-packages
```

Default provider is a local Ollama model (per the standing constraint in
this assignment series: corporate IT blocks external SaaS API keys).
Configure via `.env` to override or switch provider — see
`llm_setup.py`'s docstring (`LLM_PROVIDER`, `OLLAMA_MODEL`,
`OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.). No API
keys are hardcoded anywhere.

## Running

```bash
python main.py --file report.pdf
python main.py --file notes.docx --output summary.txt
python main.py --text "paste text directly"
echo "some text" | python main.py --stdin
```

## Testing / verification honesty note

No Ollama server, GPU, or external LLM API is reachable in this sandbox,
so real model output could not be verified here. What **was** verified,
using a fake LLM swapped in via `summarize_text(..., llm=fake)`:

- A short document (`sample_short.txt`) takes the **direct** path: exactly
  one LLM call, using `DIRECT_SUMMARY_PROMPT`.
- A long document (`sample_long.txt`, forced below the direct-path
  threshold to exercise chunking) takes the **map_reduce** path: the
  number of chunks matches `RecursiveCharacterTextSplitter`'s own
  output, one map call happens per chunk, exactly one combine call
  happens afterward, and the combine call's prompt genuinely contains
  every chunk's summary (proving the reduce step isn't silently
  dropping sections).
- `document_loader.py` correctly extracts text from real `.txt`, `.docx`
  (built with `python-docx`), and `.pdf` (built with `reportlab`) files.
- An unsupported file extension raises `ValueError` rather than failing
  silently or crashing unhelpfully.
- The CLI (`main.py`) was smoke-tested against `sample_short.txt`: it
  correctly loads the file, picks the direct strategy, and reaches the
  point of calling the LLM (confirmed by the connection error being a
  network failure to `localhost:11434`, not a code error).

What was **not** verified: actual summary quality/faithfulness against a
real model, and behavior on very large documents (hundreds of chunks) --
the map-reduce logic is verified structurally (right number of calls,
right data flow) but was not run at that scale.
