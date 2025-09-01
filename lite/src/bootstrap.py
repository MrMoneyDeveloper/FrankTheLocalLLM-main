import os
import socket
import subprocess
import sys
import shutil
from dotenv import load_dotenv
from .ollama_client import ensure_ollama_up, pull_model
from .storage.config import ensure_storage_dirs

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
