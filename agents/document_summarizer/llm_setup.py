"""
llm_setup.py
============
Shared LLM loader. Per the established convention in this series of
assignments, the default provider is a locally served Ollama model (to
work around corporate IT blocks on external SaaS API keys). OpenAI and
Google (Gemini) are also supported via LLM_PROVIDER for environments
where those keys ARE available.

All configuration comes from environment variables loaded via
python-dotenv -- no keys are hardcoded anywhere in this file.

.env variables used:
    LLM_PROVIDER        "ollama" (default), "openai", or "google"

    OLLAMA_MODEL          (default: "llama3.1")
    OLLAMA_BASE_URL       (default: "http://localhost:11434")

    OPENAI_API_KEY
    OPENAI_MODEL          (default: "gpt-4o-mini")

    GOOGLE_API_KEY
    GOOGLE_MODEL          (default: "gemini-1.5-flash")
"""

import os

from dotenv import load_dotenv

load_dotenv()


def get_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "ollama").lower()


def get_llm(temperature: float = 0.2):
    """Returns a chat model instance for whichever provider is configured."""
    provider = get_provider()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. Add it to your .env file."
            )
        return ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=temperature,
            api_key=api_key,
        )

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER=google but GOOGLE_API_KEY is not set. Add it to your .env file."
            )
        return ChatGoogleGenerativeAI(
            model=os.environ.get("GOOGLE_MODEL", "gemini-1.5-flash"),
            temperature=temperature,
            google_api_key=api_key,
        )

    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use 'ollama', 'openai', or 'google'.")
