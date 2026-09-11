# Article Analysis System

Sends article text to a company-hosted LLM API and returns a structured,
validated JSON analysis: a summary, important points, key themes, and a
target-audience description.

## Files

- `article_analyzer.py` — the whole system (prompting, API client, JSON
  validation/retry, CLI).
- `requirements.txt` — the one dependency (`requests`).

## Important assumption

No concrete API contract was specified, so this targets the most common
shape for internal LLM gateways: an **OpenAI-compatible `/chat/completions`
endpoint** (what vLLM, LiteLLM, Azure OpenAI proxies, etc. typically expose).

If your gateway uses a different contract, you only need to change
`LLMClient.call()` — the prompt design, JSON validation, retry logic, and
CLI are all written to be API-shape agnostic.

## Setup

```bash
pip install -r requirements.txt

export LLM_API_BASE_URL="https://llm.internal.yourcompany.com/v1"
export LLM_API_KEY="your-token-here"
export LLM_MODEL="your-model-name"   # optional, defaults to "company-llm"
```

## Usage

```bash
# From a file
python article_analyzer.py --file article.txt

# With a title (helps the model)
python article_analyzer.py --file article.txt --title "Battery Storage Breakthroughs"

# Via stdin
cat article.txt | python article_analyzer.py

# Save output to a file
python article_analyzer.py --file article.txt --output analysis.json

# Test the plumbing without a real API / credentials
python article_analyzer.py --file article.txt --mock
```

Exit code is `0` on success (JSON printed to stdout) and `1` on failure
(an `{"success": false, "error": "..."}` object printed instead).

## How correctness is enforced

1. **Prompt design** (`SYSTEM_PROMPT`) tells the model the exact schema,
   field types, and count/length constraints, and instructs it to return
   *only* JSON with no fences or commentary.
2. **Extraction** (`extract_json_object`) strips markdown fences or
   surrounding prose if the model adds any anyway, before parsing.
3. **Validation** (`validate_analysis`) checks, in one pass:
   - all four required fields are present and no extra fields exist
   - `summary` is a non-empty string of ≤150 words
   - `important_points` is a list of 5–10 non-empty strings
   - `key_themes` is a list of 3–5 non-empty strings, each a short phrase
     rather than a full sentence (heuristic: no terminal punctuation, ≤6
     words)
   - `target_audience` is a non-empty string
4. **Self-correction retries**: if parsing or validation fails, the
   specific problem list is sent back to the model as a follow-up message
   asking it to fix that exact issue (`max_correction_attempts`, default 2
   extra tries).
5. **Network resilience**: transient failures (timeouts, connection
   errors, 5xx responses) are retried with exponential backoff
   (`max_network_retries`, default 3). 4xx errors (bad auth, bad request)
   fail fast since retrying won't help.
6. **Graceful failure**: if all retries are exhausted, `ArticleAnalyzer.analyze()`
   returns an `AnalysisResult(success=False, error=...)` instead of raising
   — callers (like the CLI) can handle this however fits their context
   rather than crashing.

## Using it as a library

```python
from article_analyzer import ArticleAnalyzer, LLMConfig

analyzer = ArticleAnalyzer(LLMConfig())
result = analyzer.analyze(article_text, title="Optional Title")

if result.success:
    print(result.data["summary"])
    print(result.data["important_points"])
else:
    print("Failed:", result.error)
```

## Testing without a real endpoint

Pass `--mock` on the CLI, or in code:

```python
from article_analyzer import ArticleAnalyzer, LLMConfig, MockLLMClient

config = LLMConfig()
analyzer = ArticleAnalyzer(config=config, client=MockLLMClient(config))
result = analyzer.analyze("any article text")
```

This returns a canned, schema-conforming response so you can test the CLI,
validation, and downstream integration without real credentials.
