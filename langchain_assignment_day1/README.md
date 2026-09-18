# LangChain Assignment (Day-1)

Four self-contained mini-projects, each in its own folder, covering
PromptTemplates/parsers, multi-step LCEL chains, a mini-RAG pipeline, and
token-usage callback tracking.

```
langchain_assignment_day1/
├── requirements.txt
├── .env.example
├── assignment_1_messy_data_cleaner/
│   ├── llm_setup.py
│   └── messy_data_cleaner.py
├── assignment_2_marketing_assembly_line/
│   ├── llm_setup.py
│   └── marketing_chain.py
├── assignment_3_mini_rag/
│   ├── llm_setup.py
│   ├── game_rules.txt
│   └── mini_rag.py
└── assignment_4_watchful_eye/
    ├── llm_setup.py
    └── token_tracking.py
```

Each assignment folder has its own copy of `llm_setup.py` so every folder
can be run independently (as asked — "separate folders for each
assignment") without needing anything from a sibling folder.

## Using a local model (per the assignment's corporate-IT note)

The assignment note says: if OpenAI/Google AI Studio keys are blocked by
corporate IT, install Ollama, pull a small (3B–7B) model, serve it
locally, and use that instead. This is the **default** configuration
here — `llm_setup.py` defaults to `LLM_PROVIDER=ollama`, so nothing extra
needs to be flipped on to use it.

Setup:

```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Pull a small model (pick one; llama3.2 is ~3B and runs on modest hardware)
ollama pull llama3.2
# (Assignment 3 also needs an embedding model)
ollama pull nomic-embed-text
# 3. Start the server (often already running as a background service after install)
ollama serve
```

Then in each assignment folder:

```bash
cp ../.env.example .env
# .env already defaults to LLM_PROVIDER=ollama -- no key needed
pip install -r ../requirements.txt
python <script_name>.py
```

If your organization's restrictions ever lift, or you're running this
somewhere OpenAI/Google keys **are** available, just change
`LLM_PROVIDER` in `.env` to `openai` or `google` and set the matching API
key — no code changes needed anywhere, since every script goes through
the shared `get_llm()` / `get_embeddings()` functions in `llm_setup.py`.

**No API key is hardcoded anywhere in these scripts** — `python-dotenv`
loads everything from `.env`, which is git-ignored and never committed.

## Assignment 1 — The "Messy Data" Cleaner

`assignment_1_messy_data_cleaner/messy_data_cleaner.py`

A `PromptTemplate` takes `{messy_review}`, instructs the LLM to extract
sentiment and the core issue as one comma-separated string, and pipes
through the LLM and a `StrOutputParser`:

```python
chain = review_cleaner_prompt | llm | StrOutputParser()
```

Run: `python messy_data_cleaner.py` — tests with the blender review from
the assignment and prints the extracted `Sentiment: ..., Core Issue: ...`
line.

## Assignment 2 — The Marketing Assembly Line

`assignment_2_marketing_assembly_line/marketing_chain.py`

Two LCEL chains combined with the pipe operator:

```python
slogan_chain    = slogan_prompt    | llm | StrOutputParser()
translate_chain = translate_prompt | llm | StrOutputParser()
full_chain = slogan_chain | (lambda slogan: {"slogan": slogan}) | translate_chain
```

Chain 1 turns `{product_name}` into a 5-word English slogan; the lambda
reshapes that plain string into the `{"slogan": ...}` dict Chain 2's
prompt expects; Chain 2 translates it to French. Run:
`python marketing_chain.py` — prints both the English and French slogans
for the sample product `"EcoBrew Reusable Coffee Pod"`.

## Assignment 3 — Mini-RAG

`assignment_3_mini_rag/mini_rag.py` + `game_rules.txt`

`game_rules.txt` holds 5 made-up board-game rules the model has never
seen. The pipeline:

1. `TextLoader` reads `game_rules.txt`.
2. `RecursiveCharacterTextSplitter` chunks it (`chunk_size=200`,
   `chunk_overlap=20`).
3. Chunks are embedded and stored in an in-memory **FAISS** vector store.
4. A retriever (`k=2`) pulls the most relevant chunks for a question, and
   an LCEL chain (`retriever | format_docs` feeding a context-grounded
   prompt) generates the answer:

```python
rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | RAG_PROMPT | llm | StrOutputParser()
)
```

Run: `python mini_rag.py` — asks *"How many points is the golden token
worth?"* and prints the retrieved-and-grounded answer (50 points, per
`game_rules.txt`).

## Assignment 4 — The Watchful Eye

`assignment_4_watchful_eye/token_tracking.py`

Re-runs Assignment 1's chain wrapped in a token-usage callback, then
prints a formatted receipt (Prompt Tokens / Completion Tokens / Total
Tokens / Total Cost).

- **If `LLM_PROVIDER=openai`**: uses LangChain's built-in
  `get_openai_callback()`, which reports real dollar cost from OpenAI's
  pricing table.
- **Otherwise (default: Ollama)**: `get_openai_callback` only works for
  OpenAI models, so a custom `LocalTokenUsageCallbackHandler`
  (`BaseCallbackHandler` subclass) reads the `usage_metadata` LangChain
  attaches to each `AIMessage` and sums it across calls. Cost is reported
  as `$0.00` since a self-hosted model has no per-token API charge.

**Version note**: whether Ollama's token counts show up in
`usage_metadata` depends on your installed `langchain-ollama` version. If
your version doesn't populate it, the receipt will honestly show 0s with
an explanatory note rather than a fabricated number — check
`ollama_response.get("eval_count")` / `prompt_eval_count` directly (which
Ollama's raw API always returns) if you need a guaranteed-populated
number and want to extend the handler further.

Run: `python token_tracking.py`.

## How the code here was actually verified

I don't have a running Ollama server or OpenAI/Google credentials in the
environment I built this in, so the real LLM calls couldn't be executed
end-to-end here. What I *did* verify, using LangChain's fake-model
test utilities in place of a real Ollama call:

- Assignment 1's prompt → LLM → parser chain produces the expected string
  shape.
- Assignment 2's two-chain pipe sequence genuinely threads the first
  chain's output into the second chain's input (verified with 3 distinct
  fake responses to rule out a false-positive from reused placeholder
  text).
- Assignment 3's full loader → splitter → FAISS → retriever → prompt →
  LLM → parser pipeline runs without error and returns a grounded answer
  containing the retrieved fact.
- Assignment 4's callback handler correctly sums tokens when
  `usage_metadata` is present, and honestly reports (and explains) zeros
  rather than fabricating numbers when it isn't.

You'll still want to run each script for real against your local Ollama
instance to confirm actual model output quality and real token counts —
this testing confirms the *plumbing* is correct, not what a real 3B/7B
model will actually say.
