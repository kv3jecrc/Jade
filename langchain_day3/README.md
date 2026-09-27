# LangChain Assignment (Day-3)

Three self-contained mini-projects: docstring-only tool routing, agent
resilience via autonomous fallback after a tool failure, and a solved
"context fragmentation" RAG puzzle with an empirically-justified chunking
configuration.

```
langchain_day3/
├── requirements.txt
├── .env.example
├── assignment_1_confused_agent_routing/
│   ├── llm_setup.py
│   ├── tools.py
│   └── agent.py
├── assignment_2_broken_api_resilience/
│   ├── llm_setup.py
│   ├── tools.py
│   └── agent.py
└── assignment_3_lost_context_detective/
    ├── llm_setup.py
    └── rag_pipeline.py
```

## ⚠️ Version pin

Same note as prior assignments: `requirements.txt` pins `langchain` /
`langchain-core` / `langchain-community` to **0.3.x** deliberately, since
Assignment 2's classic `create_react_agent` + `AgentExecutor` API was
removed in LangChain 1.x. Install from `requirements.txt`, not a bare
`pip install langchain`.

## Using a local model (per the corporate-IT note)

```bash
ollama pull llama3.1          # tool-calling-capable model (needed for Assignment 1)
ollama pull nomic-embed-text  # embeddings (needed for Assignment 3)
ollama serve
```

Then per folder: `cp ../.env.example .env`, `pip install -r ../requirements.txt`, `python <script>.py`.

**Assignment 1 needs a tool/function-calling-capable Ollama model** —
not every model supports this. `llama3.1`, `llama3.2`, and `qwen2.5` do;
check Ollama's model page for a "tools" capability tag if using a
different one.

## Assignment 1 — The "Confused Agent" Routing Challenge

`assignment_1_confused_agent_routing/`

Two `@tool`-decorated functions, `refund_order(transaction_id)` and
`cancel_subscription(email)`, whose **docstrings are the only routing
mechanism** — `agent.py` contains no if/else or keyword matching on the
user's text anywhere. The flow:

```python
llm_with_tools = llm.bind_tools([refund_order, cancel_subscription])
response = llm_with_tools.invoke([...])
tool_name = response.tool_calls[0]["name"]      # the model's own choice
result = TOOLS_BY_NAME[tool_name].invoke(args)   # dict lookup, not branching
```

Run: `python agent.py` — runs both required test cases (the "stop
charging me" cancel test and the "$50 on TXN991" refund test) and prints
which tool got selected, its arguments, its output, and a PASS/FAIL
against the expected tool.

**What I verified vs. what needs a real model**: I don't have a running
Ollama instance, so I can't verify the LLM's *actual semantic reading* of
the docstrings picks correctly — that's the real test this assignment is
about, and it can only be judged with genuine model inference. What I did
verify is the dispatch plumbing: given a scripted tool_call response, the
code correctly extracts the tool name/args and invokes the matching
Python function with them.

## Assignment 2 — Agent Resilience: The Broken API Challenge

`assignment_2_broken_api_resilience/`

A classic ReAct agent with `get_internal_stock_price` (hardcoded to
always return `"Error: Database Timeout"`) and `search_public_web` (a
working mock search). Run: `python agent.py` — asks *"What is the current
stock price of Apple?"* and prints the required trace:

```
Thought 1: [attempts the internal DB first]
Action 1: [get_internal_stock_price: "AAPL"]
Observation 1: ["Error: Database Timeout"]
Thought 2: [recognizes the failure, decides to try the backup]
Action 2: [search_public_web: "Apple stock price"]
Observation 2: ["Apple stock is at $170"]
Final Answer: [$170]
```
followed by an explicit `Attempted primary tool / Recovered via backup
tool / Demonstrates autonomous recovery` summary line.

**Verified** with a scripted fake LLM reproducing exactly this
failure-then-pivot sequence, confirmed against the real (non-fake) tool
functions — `get_internal_stock_price` genuinely always fails,
`search_public_web` genuinely returns the mock price.

## Assignment 3 — The "Lost Context" Detective Puzzle

`assignment_3_lost_context_detective/rag_pipeline.py`

Splits `tricky_document` (embedded directly in the script, verbatim as
given) with `RecursiveCharacterTextSplitter`, stores chunks in an
in-memory FAISS store, and asks: *"What is the deadline and budget for
Project Phoenix?"* — a question that requires connecting Section 1 (which
names "Project Phoenix") with Section 9 (which has the deadline/budget
but only calls it "the cloud restructure initiative mentioned earlier").

**Chosen parameters: `chunk_size=200`, `chunk_overlap=50`, retrieved with
`k=3`.** These were not guessed — I measured the document first (every
section is 137–217 characters) and empirically tested a bad config before
settling on this one. The full reasoning, including exactly what the bad
config breaks and why, is in the **mandatory multi-line comment at the
bottom of `rag_pipeline.py`** (required by the assignment) — short
version:

- **Bad config** (`chunk_size=100, chunk_overlap=0`): verified this
  actually splits Section 9 into three fragments, with the connecting
  phrase `"cloud restructure initiative"` landing in a *different chunk*
  than the deadline/budget numbers — I confirmed this directly by
  printing the resulting chunks, not just reasoning about it abstractly.
- **Chosen config**: `chunk_size=200` is large enough to keep Section 1
  and Section 9 each intact as one unbroken chunk (verified the same
  way), and `k=3` retrieval brings back both chunks together for this
  query, since each one strongly matches different keywords in the
  question ("Project Phoenix" vs. "deadline"/"budget"). The LLM then sees
  both intact excerpts side by side and can infer the connection itself.

**What I verified vs. what needs real infrastructure**: I have no running
Ollama instance in the environment I built this in, so `get_embeddings()`
and `get_llm()` couldn't be exercised for real here. I verified the
chunking behavior directly (real `RecursiveCharacterTextSplitter`, real
document, no mocking needed) and verified the full retrieval→prompt→LLM
pipeline wiring using a content-sensitive word-overlap embedding stand-in
(not random noise) confirming both target chunks land in the top-3
results, plus a scripted fake LLM confirming the final answer flows
through correctly end to end. You'll want to run it for real against
Ollama + `nomic-embed-text` to confirm actual embedding quality retrieves
both chunks reliably — if it doesn't, try raising `RETRIEVAL_K` to 4 or 5
first before changing chunk size.
