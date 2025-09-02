import os
import socket
import subprocess
import sys
import shutil
from dotenv import load_dotenv
from .ollama_client import ensure_ollama_up, pull_model
from .storage.config import ensure_storage_dirs, NOTES_DIR
from .storage.parquet_util import (
    repair_parquet_if_needed,
    table_path,
    read_parquet_safe,
    atomic_replace,
)
import pandas as pd
import time
import os

load_dotenv()


def ensure_dirs():
    for p in [
        os.getenv("DATA_DIR", "./lite/data"),
        os.getenv("DOCS_DIR", "./lite/data/docs"),
        os.getenv("CHROMA_DIR", "./lite/data/chroma"),
    ]:
        os.makedirs(p, exist_ok=True)
    # Ensure note/meta dirs as well
    try:
        ensure_storage_dirs()
    except Exception:
        pass


def ensure_ollama_models():
    if os.getenv("SKIP_OLLAMA", "0") == "1":
        return
    ensure_ollama_up()
    pull_model(os.getenv("CHAT_MODEL", "llama3.1"))
    pull_model(os.getenv("EMBED_MODEL", "nomic-embed-text"))


def free_port(port: int):
    # Best-effort; may require privileges on some systems
    try:
        if sys.platform.startswith("win"):
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    (
                        f"$p=(Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue).OwningProcess;"
                        f"if($p){{ Stop-Process -Id $p -Force }}"
                    ),
                ],
                check=False,
                capture_output=True,
            )
        else:
            subprocess.run(["bash", "-lc", f"fuser -k {port}/tcp || true"], check=False)
    except Exception:
        pass


def find_available_port(start: int, host: str = "127.0.0.1", max_tries: int = 50) -> int:
    p = start
    for _ in range(max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, p))
                return p
            except OSError:
                p += 1
    raise RuntimeError(f"No free port found starting at {start}")


def bootstrap():
    ensure_dirs()
    ensure_ollama_models()
    try:
        validate_and_repair_metadata()
    except Exception:
        pass
    try:
        seed_first_run_note()
    except Exception:
        pass


def _now() -> int:
    return int(time.time() * 1000)


def validate_and_repair_metadata() -> None:
    # Repair tables if corrupt
    for name, cols in [
        ("notes_index", ["note_id", "title", "path", "updated_at", "size", "sha256"]),
        ("groups", None),
        ("group_notes", ["group_id", "note_id"]),
        ("tabs", ["session_id", "tab_id", "note_id", "position"]),
        ("embeddings", ["note_id", "chunk_index", "embedding"]),
    ]:
        repair_parquet_if_needed(table_path(name), cols)

    # Migrate legacy notes -> notes_index if needed
    notes_path = table_path("notes")
    notes_index_path = table_path("notes_index")
    if (not os.path.exists(notes_index_path)) and os.path.exists(notes_path):
        try:
            df = read_parquet_safe(notes_path)
            if not df.empty and "id" in df.columns:
                rows = []
                for _, r in df.iterrows():
                    nid = r["id"]
                    title = r.get("title")
                    # prefer .md, fallback .txt
                    md = os.path.join(NOTES_DIR, f"{nid}.md")
                    tx = os.path.join(NOTES_DIR, f"{nid}.txt")
                    p = md if os.path.exists(md) else tx
                    size = os.path.getsize(p) if os.path.exists(p) else 0
                    # sha is optional; skip heavy compute here
                    rows.append({
                        "note_id": nid,
                        "title": title,
                        "path": p,
                        "updated_at": r.get("updated_at") or _now(),
                        "size": int(size),
                        "sha256": "",
                    })
                if rows:
                    atomic_replace(notes_index_path, pd.DataFrame(rows))
        except Exception:
            pass


def seed_first_run_note() -> None:
    # If no notes exist, create a seed note to onboard users
    from .storage.parquet_util import read_parquet_safe, table_path
    import pandas as pd
    import os
    from .storage import notes as notes_store

    path = table_path("notes_index")
    df = read_parquet_safe(path)
    if df.empty or df.shape[0] == 0:
        title = "Welcome to Local Notes"
        content = (
            "# Welcome\n\n"
            "- Press Ctrl/Cmd+K for global search (All/Group/Note)\n"
            "- Use the right mini-hub for LLM search (This Note / Groups / All)\n"
            "- Settings: models and performance (chunk size/overlap, debounce)\n\n"
            "Tips:\n\n"
            "- Drag tabs to reorder; Ctrl/Cmd-select then right-click to Merge\n"
            "- Drag notes onto groups to add them; a note can be in multiple groups\n"
            "- Autosave every ~500ms; snapshots enable crash recovery\n"
        )
        try:
            notes_store.create_note(title, content)
        except Exception:
            pass
