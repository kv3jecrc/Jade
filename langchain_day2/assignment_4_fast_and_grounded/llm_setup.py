"""
llm_setup.py
============
Shared LLM/embeddings loader used across all four assignments.

Per the assignment note: corporate IT blocks external SaaS API keys, so
the default provider is a locally-served Ollama model. OpenAI and Google
(Gemini) are also supported via LLM_PROVIDER for environments where those
keys ARE available -- switching providers requires no code changes
elsewhere, only a .env edit.

All configuration comes from environment variables loaded via
python-dotenv -- no keys are hardcoded anywhere in this file or in any
assignment script.

.env variables used:
    LLM_PROVIDER        "ollama" (default), "openai", or "google"

    # Ollama (local, no key required)
    OLLAMA_MODEL         e.g. "llama3.2" or "mistral"          (default: "llama3.2")
    OLLAMA_BASE_URL       e.g. "http://localhost:11434"         (default: that value)
    OLLAMA_EMBED_MODEL    e.g. "nomic-embed-text"               (default: that value)

    # OpenAI (only needed if LLM_PROVIDER=openai)
    OPENAI_API_KEY
    OPENAI_MODEL          (default: "gpt-4o-mini")
    OPENAI_EMBED_MODEL    (default: "text-embedding-3-small")

    # Google / Gemini (only needed if LLM_PROVIDER=google)
    GOOGLE_API_KEY
    GOOGLE_MODEL          (default: "gemini-1.5-flash")
    GOOGLE_EMBED_MODEL    (default: "models/embedding-001")
"""

import os

from dotenv import load_dotenv

load_dotenv()


def get_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "ollama").lower()


def get_llm(temperature: float = 0.3):
    """Returns a chat model instance for whichever provider is configured."""
    provider = get_provider()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
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


def get_embeddings():
    """Returns an embeddings model instance for whichever provider is configured."""
    provider = get_provider()

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. Add it to your .env file."
            )
        return OpenAIEmbeddings(
            model=os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
            api_key=api_key,
        )

    if provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER=google but GOOGLE_API_KEY is not set. Add it to your .env file."
            )
        return GoogleGenerativeAIEmbeddings(
            model=os.environ.get("GOOGLE_EMBED_MODEL", "models/embedding-001"),
            google_api_key=api_key,
        )

    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use 'ollama', 'openai', or 'google'.")
