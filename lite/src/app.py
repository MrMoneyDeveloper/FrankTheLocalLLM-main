import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from .bootstrap import bootstrap, find_available_port
from .vectorstore import add_documents, query
from .ollama_client import chat

load_dotenv()

HOST = os.getenv("APP_HOST", "127.0.0.1")
PORT = int(os.getenv("APP_PORT", "8001"))
ALLOWED = os.getenv("ALLOWED_ORIGINS", "*")

app = FastAPI(title="Frank Local LLM (Lite)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED] if ALLOWED != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatIn(BaseModel):
    prompt: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat")
def chat_endpoint(body: ChatIn):
    msgs = [{"role": "user", "content": body.prompt}]
    answer = chat(msgs)
    return {"answer": answer}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...), chunk: int = Form(800), overlap: int = Form(100)):
    raw = (await file.read()).decode("utf-8", errors="ignore")
    chunks = []
    i = 0
    while i < len(raw):
        j = min(len(raw), i + chunk)
        text = raw[i:j]
        cid = f"{file.filename}#{i}-{j}"
        chunks.append({"id": cid, "text": text, "meta": {"source": file.filename}})
        i = j - overlap if (j - overlap) > i else j
    if chunks:
        add_documents(chunks)
    return {"added": len(chunks)}


@app.get("/search")
def search(q: str, k: int = 5):
    return {"results": query(q, k)}


def run_api(auto_port: bool = True) -> int:
    """Bootstrap and run the API, returning the port used."""
    bootstrap()
    port = PORT
    if auto_port:
        try:
            # Try to free requested port first
            # If still not available, auto-increment to a free port
            from .bootstrap import free_port

            free_port(port)
            port = find_available_port(port)
        except Exception:
            port = find_available_port(port)
    uvicorn.run("lite.src.app:app", host=HOST, port=port, reload=False)
    return port


if __name__ == "__main__":
    run_api(auto_port=True)

