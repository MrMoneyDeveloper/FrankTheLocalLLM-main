from __future__ import annotations

from pathlib import Path
import json

from fastapi import APIRouter, Body, HTTPException
from langchain_community.llms import Ollama

router = APIRouter(tags=["chat"], prefix="/chat")

_CACHE_FILE = Path(__file__).resolve().parents[1] / "data" / "chat_cache.json"


class ChatService:
    _llm: Ollama | None = None
    _cache: dict[str, str] | None = None

    def __init__(self) -> None:
        if self._llm is None:
            self._llm = Ollama(model="llama3")
        if self._cache is None:
            self._cache = _load_cache()

    def chat(self, message: str) -> dict:
        cached = (
            self._cache.get(message) if hasattr(self._cache, "get") else None
        )
        if cached is not None:
            return {"response": cached, "cached": True}
        try:
            response = self._llm.invoke(message)
        except Exception as exc:  # pragma: no cover - runtime failure
            raise HTTPException(status_code=500, detail=str(exc))
        if hasattr(self._cache, "set"):
            self._cache.set(message, response)
        else:
            self._cache[message] = response
            _save_cache(self._cache)
        return {"response": response, "cached": False}


def _load_cache() -> dict[str, str]:
    if _CACHE_FILE.exists():
        try:
            return json.loads(_CACHE_FILE.read_text())
        except json.JSONDecodeError:  # pragma: no cover - corrupted file
            return {}
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    _CACHE_FILE.write_text(json.dumps(cache))


@router.post("")
def chat(message: str = Body(..., embed=True)):
    service = ChatService()
    return service.chat(message)
