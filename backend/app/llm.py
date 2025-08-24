import time
import logging
import requests
from langchain_ollama import OllamaLLM as LangchainOllama

class OllamaLLM:
    def __init__(self, model: str = "llama3", retries: int = 3, backoff: float = 2.0):
        self.model = model
        last_err = None
        for i in range(retries):
            try:
                r = requests.get("http://localhost:11434", timeout=5)
                r.raise_for_status()
                self._client = LangchainOllama(model=self.model)
                logging.info("Ollama connected on attempt %d", i+1)
                return
            except Exception as e:  # pragma: no cover - network errors
                last_err = e
                logging.warning("Ollama connect failed (attempt %d/%d): %s", i+1, retries, e)
                time.sleep(backoff)
        logging.error("Ollama unavailable after %d attempts: %s", retries, last_err)
        raise RuntimeError(f"Ollama unavailable: {last_err}")

    def invoke(self, prompt: str) -> str:
        return self._client.invoke(prompt)
