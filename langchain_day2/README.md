# LangChain Assignment (Day-2)

Four self-contained mini-projects, each in its own folder: a self-correcting
ReAct agent, a text-splitting overlap proof, a metadata-filtered RAG
retriever that resolves "context poisoning," and a grounded + cached
generation function.

```
langchain_day2/
├── requirements.txt
├── .env.example
├── assignment_1_self_correcting_agent/
│   ├── llm_setup.py
│   ├── tools.py
│   └── agent.py
├── assignment_2_smart_splitter_proof/
│   ├── sample_document.txt
│   └── splitter_proof.py
├── assignment_3_context_poisoning/
│   ├── llm_setup.py
│   └── context_poisoning.py
└── assignment_4_fast_and_grounded/
    ├── llm_setup.py
    └── fast_and_grounded.py
```

## ⚠️ Version pin (read this before running Assignment 1 or 3/4)

`requirements.txt` pins `langchain`/`langchain-core`/`langchain-community`
to the **0.3.x line** deliberately. LangChain 1.x (released after this
assignment was likely written) removed the classic
`langchain.agents.create_react_agent` + `AgentExecutor` API that
Assignment 1's Thought/Action/Observation trace is built on, replacing it
with a LangGraph-based `create_agent` that has a different, message-based
output shape. If you `pip install langchain` fresh today you'll get 1.x
and Assignment 1's imports will fail — install from `requirements.txt`,
not a bare `pip install langchain`.

## Using a local model (per the assignment's corporate-IT note)

Default provider is Ollama, no API key needed:

```bash
ollama pull llama3.2          # the LLM
ollama pull nomic-embed-text  # embeddings (needed for Assignment 3)
ollama serve                  # usually already running as a service after install
```

Then per assignment folder:

```bash
cp ../.env.example .env   # already defaults to LLM_PROVIDER=ollama
pip install -r ../requirements.txt
python <script_name>.py
```

Flip `LLM_PROVIDER` to `openai` or `google` in `.env` (with the matching
API key) if those are available in your environment — no code changes
needed, since every script goes through the shared `get_llm()` /
`get_embeddings()` in each folder's `llm_setup.py`. **No API key is
hardcoded anywhere** — everything loads via `python-dotenv`.

Assignment 1's Search tool uses the public Wikipedia API directly (no key
required) — that's a public website, not one of the paid SaaS LLM APIs
the assignment's IT-restriction note is about, so it should be reachable
even where OpenAI/Google keys are blocked.

## Assignment 1 — Self-Correcting Agent

`assignment_1_self_correcting_agent/`

A classic ReAct agent (`create_react_agent` + `AgentExecutor`) with two
tools:

- **CalculatorTool** (`tools.py`): arithmetic only, via a restricted
  AST-based evaluator (not Python's `eval`) — no access to any external
  data.
- **SearchTool** (`tools.py`): Wikipedia lookup — can't do math.

Run: `python agent.py`, which asks *"Multiply the birth year of Albert
Einstein by 5"* and prints the exact required trace:

```
Thought 1: [reasoning that it doesn't know the birth year yet]
Action 1: [SearchTool: "Albert Einstein birth year"]
Observation 1: ["1879"]
Thought 2: [reasoning incorporating the observation]
Action 2: [CalculatorTool: "1879 * 5"]
Observation 2: ["9395"]
Final Answer: [9395]
```

This trace is built from the agent's **real** `intermediate_steps`
(`agent.py::run_and_trace`), not hardcoded — see the "How this was
verified" section below for how the tool-routing logic (search-then-
calculate, not calculate-first) was confirmed correct.

## Assignment 2 — Smart Splitter Proof

`assignment_2_smart_splitter_proof/`

`sample_document.txt` (3 dense paragraphs on AI history) is split with
`RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)`. A
custom `find_overlap(chunk_a, chunk_b)` function then finds the longest
string that is simultaneously a suffix of chunk A and a prefix of chunk
B — the actual overlapping text — rather than just trusting that the
library did what it was told.

Run: `python splitter_proof.py`. This one needs no LLM at all (pure
text-splitting), so it runs immediately with no setup. Real observed
output: overlaps of 43–49 characters across most consecutive pairs (very
close to the configured 50 — RecursiveCharacterTextSplitter breaks on
natural boundaries like sentences/words rather than a fixed offset, so
exact 50 isn't guaranteed every time), with two pairs showing 0 overlap
where the splitter crosses a paragraph boundary and starts fresh — a
correctly-explained edge case, not a bug in the overlap function.

## Assignment 3 — Solving "Context Poisoning"

`assignment_3_context_poisoning/`

Two contradictory WFH-policy documents (banned as of 2022, allowed 3
days/week as of 2024) are embedded into the same FAISS store, each
tagged with `metadata={"year": ...}`. `retrieve_with_year_filter()` uses
FAISS's metadata `filter` parameter so a query for `filter_year=2024`
**cannot** see the 2022 document at all — it's excluded at the retrieval
level, not just deprioritized.

Run: `python context_poisoning.py` — prints the active filter, the exact
retrieved chunk (confirming only the 2024 policy came back), and the
LLM's answer generated from that chunk alone.

## Assignment 4 — The "Fast & Grounded" System

`assignment_4_fast_and_grounded/`

- **Grounding**: a system prompt instructs the model to answer only from
  a fixed context (a short company policy excerpt) and to respond with
  exactly `"I do not have enough information"` if the answer isn't there.
- **Caching**: a plain `query_cache: dict[str, str]` is checked *before*
  any LLM call — a repeat question returns instantly from the dict and
  prints `"Returned from Cache: <answer>"`, without touching the LLM.

Run: `python fast_and_grounded.py` — executes all three required
scenarios (first ask, cache hit, out-of-context grounding test) in
sequence and prints each.

## How this was verified

I don't have a running Ollama instance, Wikipedia network access, or
any provider credentials in the environment I built this in, so I
couldn't execute real model/Wikipedia calls end-to-end here. What I did
verify, using LangChain's fake-model test utilities in place of real
calls:

- **Assignment 1**: built a scripted fake LLM that mimics exactly the
  "logic trap" scenario (first response reaches for Search, second uses
  the observation to call Calculator, third gives the final answer), ran
  it through the real `create_react_agent`/`AgentExecutor` machinery, and
  confirmed the agent's genuine `intermediate_steps` show
  Search → Calculator in that order with the correct tool inputs, and
  that the printed trace exactly matches the required format. Also
  independently verified the real (non-fake) calculator tool computes
  `1879 * 5 = 9395` correctly.
- **Assignment 2**: fully real, no mocking needed — ran the actual
  splitter on the actual sample document and inspected genuine chunk
  boundaries and overlaps.
- **Assignment 3**: verified with fake (but genuinely distinct-per-text)
  embeddings that FAISS's metadata filter actually excludes the
  non-matching year — confirmed the 2022 document never appears in
  filtered results, only in unfiltered ones.
- **Assignment 4**: verified with a call-counting fake LLM that the
  cache-hit scenario makes **zero** additional LLM calls (only 2 real
  calls total across 3 questions asked, confirming Scenario 2 is a true
  cache bypass, not a coincidence), and that the grounding prompt
  produces the exact required fallback phrase for an out-of-context
  question.

You'll still want to run each script for real against your local Ollama
instance (and live Wikipedia access for Assignment 1) to see actual model
behavior — this testing confirms the *plumbing and logic* are correct,
not what a real 3B/7B model will say in practice.

## A note on LLM non-determinism

Assignments 1 and 4 depend on the LLM actually following instructions
precisely (choosing the right tool order; reproducing an exact fallback
phrase). Real small local models (3B–7B) are less reliable at strict
instruction-following than larger hosted models — if Assignment 1 tries
the calculator first despite the prompt, or Assignment 4's fallback phrase
comes back with extra punctuation, that's a model-following-instructions
issue rather than a bug in this code (both scripts print/report the
actual behavior honestly rather than forcing a "pass" — see
`fast_and_grounded.py`'s `matches_required_phrase` check). Lowering
`temperature` (already set to 0.0 by default) and trying a larger model
(7B rather than 3B) usually improves reliability if you hit this.
