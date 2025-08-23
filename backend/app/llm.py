from typing import Protocol

from .config import Settings


class LLMClient(Protocol):
    """Interface for language model clients."""

    def invoke(self, prompt: str) -> str:  # pragma: no cover - interface
        ...


class DummyLLM:
    """Fallback LLM implementation used when no backend is available."""

    def invoke(self, prompt: str) -> str:  # pragma: no cover - runtime call
        return "LLM backend not configured"


def get_llm(model: str | None = None, backend: str | None = None) -> LLMClient:
    """Return an LLM client for the configured backend."""
    settings = Settings()
    backend = backend or settings.model_backend
    model_name = model or settings.model

    if backend == "ollama":
        from langchain_ollama import OllamaLLM as LangchainOllama

        return LangchainOllama(model=model_name)
    return DummyLLM()
