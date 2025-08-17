from __future__ import annotations

from abc import ABC
from functools import lru_cache
from hashlib import sha256
from typing import Any, Callable

from sqlalchemy.orm import Session

from ..llm import LLMClient

class UnitOfWork:
    """Collects database changes and flushes them on teardown."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._new: list[Any] = []
        self._dirty: list[Any] = []

    def add(self, obj: Any) -> None:
        self._new.append(obj)

    def update(self, obj: Any) -> None:
        self._dirty.append(obj)

    def flush(self) -> None:
        if self._new:
            self.db.add_all(self._new)
        for obj in self._dirty:
            self.db.merge(obj)
        if self._new or self._dirty:
            self.db.commit()
        self._new.clear()
        self._dirty.clear()


def get_uow(db: Session) -> UnitOfWork:
    uow = UnitOfWork(db)
    try:
        yield uow
        uow.flush()
    finally:
        pass


class CachedLLMService(ABC):
    """Mixin for services that interact with an LLM with LRU caching."""

    def __init__(self, llm: LLMClient, cache_size: int = 128) -> None:
        self._llm = llm
        self._hit = False

        @lru_cache(maxsize=cache_size)
        def _cached_call(key: str, prompt: str) -> str:
            return self._llm.invoke(prompt)

        self._cached_call: Callable[[str, str], str] = _cached_call

    def llm_invoke(self, prompt: str) -> str:
        key = sha256(prompt.encode()).hexdigest()
        if hasattr(self, "_cached_call"):
            before = self._cached_call.cache_info().hits
            result = self._cached_call(key, prompt)
            self._hit = self._cached_call.cache_info().hits > before
        else:  # pragma: no cover - used in patched tests
            result = self._llm.invoke(prompt)
            self._hit = False
        return result

    def was_cached(self) -> bool:
        return self._hit
