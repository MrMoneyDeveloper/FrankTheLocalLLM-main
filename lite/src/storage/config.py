import json
import os
from typing import Any, Dict


DATA_DIR = os.getenv("DATA_DIR", "./lite/data")
DOCS_DIR = os.getenv("DOCS_DIR", os.path.join(DATA_DIR, "docs"))
NOTES_DIR = os.path.join(DATA_DIR, "notes")
META_DIR = os.path.join(DATA_DIR, "meta")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")


DEFAULT_SETTINGS: Dict[str, Any] = {
    "CHAT_MODEL": os.getenv("CHAT_MODEL", "llama3.1"),
    "EMBED_MODEL": os.getenv("EMBED_MODEL", "nomic-embed-text"),
    "CHUNK_SIZE": 800,
    "CHUNK_OVERLAP": 100,
    "REINDEX_DEBOUNCE_MS": 500,
    "SEARCH_THROTTLE_MS": 200,
    "MAX_CHUNKS_PER_QUERY": 64,
    "SIMPLE_MODE": True,
}


def ensure_storage_dirs() -> None:
    for d in (DATA_DIR, DOCS_DIR, NOTES_DIR, META_DIR):
        os.makedirs(d, exist_ok=True)


def load_settings() -> Dict[str, Any]:
    ensure_storage_dirs()
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # merge defaults with existing
            out = DEFAULT_SETTINGS.copy()
            out.update(data or {})
            return out
    except Exception:
        return DEFAULT_SETTINGS.copy()


def _fsync_file(p: str) -> None:
    try:
        fd = os.open(p, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        pass


def _fsync_dir(p: str) -> None:
    try:
        dfd = os.open(os.path.dirname(p) or ".", os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except Exception:
        pass


def _atomic_write(path: str, content: str) -> None:
    tmp = path + ".tmp"
    bak = path + ".bak"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    # backup previous if exists
    if os.path.exists(path):
        try:
            if os.path.exists(bak):
                os.remove(bak)
        except Exception:
            pass
        try:
            os.replace(path, bak)
        except Exception:
            pass
    os.replace(tmp, path)
    _fsync_file(path)
    _fsync_dir(path)


def save_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    ensure_storage_dirs()
    merged = DEFAULT_SETTINGS.copy()
    merged.update(data or {})
    _atomic_write(SETTINGS_PATH, json.dumps(merged, ensure_ascii=False, indent=2))
    return merged
