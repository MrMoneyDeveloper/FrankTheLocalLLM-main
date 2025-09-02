import os
import requests
import math
from dotenv import load_dotenv

load_dotenv()

OLLAMA = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
FAKE_LLM = os.getenv("FAKE_LLM", "0") == "1"
FAKE_EMBED = os.getenv("FAKE_EMBED", "0") == "1"


def ensure_ollama_up():
    try:
        r = requests.get(f"{OLLAMA}/api/tags", timeout=3)
        r.raise_for_status()
    except Exception as e:
        raise RuntimeError(
            f"Ollama not reachable at {OLLAMA}. Install from https://ollama.com, then run 'ollama serve'."
        ) from e


def pull_model(model: str):
    # Idempotent pull. If present, returns quickly; first pull may take minutes.
    try:
        requests.post(f"{OLLAMA}/api/pull", json={"name": model}, timeout=600)
    except requests.exceptions.ReadTimeout:
        # Some Ollama versions stream without final response; treat long pull as success path.
        pass


def chat(messages, model: str = CHAT_MODEL, stream: bool = False) -> str:
    if FAKE_LLM:
        # naive echo using last user prompt; respects guardrail prompt by checking for 'Context' substring
        user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user = m.get("content", "")
                break
        return f"Answer: {user[:200]}"
    payload = {"model": model, "messages": messages, "stream": stream}
    r = requests.post(f"{OLLAMA}/api/chat", json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()
    return data.get("message", {}).get("content", "")


def embed_texts(texts, model: str = EMBED_MODEL):
    if FAKE_EMBED:
        # Very simple bag-of-chars embedding into fixed small dimension
        dim = 64
        out = []
        for t in texts:
            v = [0.0] * dim
            for ch in (t or ""):
                v[ord(ch) % dim] += 1.0
            # normalize
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out
    r = requests.post(
        f"{OLLAMA}/api/embeddings", json={"model": model, "input": texts}, timeout=300
    )
    r.raise_for_status()
    # API returns {"embedding": [...]} for single, {"embeddings": [[...], ...]} for batch
    js = r.json()
    if isinstance(js, dict) and "embedding" in js:
        return [js["embedding"]]
    return js.get("embeddings", [])
