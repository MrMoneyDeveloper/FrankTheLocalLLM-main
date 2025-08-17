from typing import Protocol

class LLMClient(Protocol):
    """Interface for language model clients."""

    def invoke(self, prompt: str) -> str:
        ...


class OllamaLLM:
    """Ollama-based implementation of :class:`LLMClient`."""

    def __init__(self, model: str = "llama3"):
        from langchain_ollama import OllamaLLM as LangchainOllama

        self._client = LangchainOllama(model=model)

    def invoke(self, prompt: str) -> str:  # pragma: no cover - runtime call
        return self._client.invoke(prompt)
