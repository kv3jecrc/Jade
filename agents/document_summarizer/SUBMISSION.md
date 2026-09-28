# Agent Submission — Document Summarizer

## 1. Agent File / Export

This agent was built as source code rather than in a no-code builder, so
there is no project-export JSON/workflow file to attach. The equivalent
"export" is this entire folder — every file needed to run the agent is
here:

- `llm_setup.py` — LLM provider configuration (Ollama/OpenAI/Google)
- `prompts.py` — the 3 prompt templates (also reproduced in `SYSTEM_PROMPT.md`)
- `document_loader.py` — reads `.txt` / `.md` / `.pdf` / `.docx` input
- `summarizer.py` — the direct-vs-map-reduce summarization logic
- `main.py` — CLI entry point
- `requirements.txt` — exact dependency versions
- `sample_short.txt`, `sample_long.txt` — sample inputs used to verify both code paths

To run it: `pip install -r requirements.txt` then `python main.py --file <your file>`
(see `README.md` for full usage and configuration).

## 2. System Prompt / Agent Instructions

See `SYSTEM_PROMPT.md` for the complete, verbatim instruction text (all
three prompts the agent sends to the LLM, exactly as implemented in
`prompts.py`).

## 3. Use Case Summary

This agent turns long or dense documents — reports, meeting notes,
policies, contracts — into short, plain-language bullet-point summaries
that preserve every concrete fact, number, decision, and action item. It
is built for anyone who needs to quickly extract the substance of a
document without reading it end to end: managers skimming reports,
analysts triaging documents, or teams that need a consistent first-pass
summary before a deeper review. The primary value is time saved and
consistency — the same summarization standard is applied to every
document, and documents too long for a single LLM call are handled via
map-reduce chunking so summary quality doesn't degrade with length.

## 4. Platform Used

Custom-built agent (Python + LangChain), not a no-code builder platform.
LLM backend is pluggable: Ollama (default, for local/offline use),
OpenAI, or Google Gemini, selected via a `.env` variable with no code
changes.

## 5. Additional Technologies / Frameworks Used

- **LangChain** (`langchain`, `langchain-core`) — prompt orchestration and LLM invocation
- **langchain-text-splitters** (`RecursiveCharacterTextSplitter`) — chunking for the map-reduce path
- **Ollama** / **OpenAI API** / **Google Gemini API** — pluggable LLM backends
- **pypdf**, **python-docx** — document text extraction
- **python-dotenv** — credential-free configuration (no hardcoded API keys)

No RAG, vector database, MCP, or external API/database integration was
needed for this use case — it's a pure text-in, text-out LLM
transformation, which is exactly why it was the fastest of the catalog's
agents to build.

## Submission Checklist

- [x] Agent export file (project/workflow/configuration) — this folder / source code
- [x] Complete system prompt or instruction set — `SYSTEM_PROMPT.md`
- [x] 2–3 line use case description — Section 3 above
- [x] Platform name — Section 4 above
- [x] Additional technologies/frameworks used — Section 5 above
