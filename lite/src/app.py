import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from .bootstrap import bootstrap, find_available_port
from .vectorstore import add_documents, query
from .ollama_client import chat
from .storage.parquet_util import read_parquet_safe, table_path
from .api.notes import router as notes_router
from .api.groups import router as groups_router
from .api.tabs import router as tabs_router
from .api.settings import router as settings_router
from .scheduler import start_scheduler

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

# Routers (notes, groups, tabs, settings)
app.include_router(notes_router)
app.include_router(groups_router)
app.include_router(tabs_router)
app.include_router(settings_router)


class ChatIn(BaseModel):
    prompt: str
    note_ids: str | None = None  # comma-separated
    group_ids: str | None = None  # comma-separated
    date_start: int | None = None
    date_end: int | None = None
    k: int = 6


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat")
def chat_endpoint(body: ChatIn):
    # Resolve allowed note ids from request
    allowed: list[str] | None = None
    if body.group_ids:
        gm = read_parquet_safe(table_path("group_notes"))
        if not gm.empty:
            gids = [g for g in body.group_ids.split(",") if g]
            allowed = gm[gm["group_id"].isin(gids)]["note_id"].dropna().unique().tolist()
        else:
            allowed = []
    if body.note_ids:
        ids = [x for x in body.note_ids.split(",") if x]
        allowed = ids if allowed is None else [n for n in allowed if n in ids]
    # Date filter on notes
    note_filter: list[str] | None = None
    if body.date_start or body.date_end:
        df = read_parquet_safe(table_path("notes_index"))
        if not df.empty:
            if body.date_start:
                df = df[df["updated_at"] >= int(body.date_start)]
            if body.date_end:
                df = df[df["updated_at"] <= int(body.date_end)]
            note_filter = df["note_id"].tolist()
    if note_filter is not None:
        if allowed is None:
            allowed = note_filter
        else:
            allowed = [n for n in allowed if n in note_filter]

    # RAG using embeddings.parquet + MMR
    from .ollama_client import embed_texts
    import math
    import pandas as pd

    embs = read_parquet_safe(table_path("embeddings"))
    if embs.empty:
        # fallback: direct chat without context
        msgs = [
            {"role": "system", "content": "Use ONLY provided context; if not found, reply 'Not found in allowed scope'."},
            {"role": "user", "content": body.prompt},
        ]
        answer = chat(msgs)
        return {"answer": answer, "citations": []}

    if allowed:
        embs = embs[embs["note_id"].isin(allowed)]
    if body.date_start or body.date_end:
        embs = embs[(~embs["updated_at"].isna())]
        if body.date_start:
            embs = embs[embs["updated_at"] >= int(body.date_start)]
        if body.date_end:
            embs = embs[embs["updated_at"] <= int(body.date_end)]
    if embs.empty:
        return {"answer": "Not found in allowed scope", "citations": []}

    qv = embed_texts([body.prompt])[0]

    def norm(v):
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    qn = norm(qv)

    def cos(a, b):
        return sum(x * y for x, y in zip(a, b))

    # Build candidate list
    cand = []
    for _, r in embs.iterrows():
        try:
            ev = r["embedding"]
            if isinstance(ev, list):
                en = norm(ev)
                s = cos(qn, en)
                cand.append((s, r["note_id"], int(r["chunk_index"]), r["text"]))
        except Exception:
            continue
    cand.sort(key=lambda x: x[0], reverse=True)

    # MMR diversification
    K = max(1, int(body.k))
    lambda_ = 0.7
    selected: list[tuple] = []
    selected_vecs: list[list[float]] = []
    for score, nid, cidx, text in cand:
        if len(selected) >= K:
            break
        # compute marginal relevance
        # similarity to already selected chunks
        if not selected:
            selected.append((score, nid, cidx, text))
            # store embedding vec for this text (re-read from embs)
            try:
                ev = embs[(embs["note_id"] == nid) & (embs["chunk_index"] == cidx)]["embedding"].iloc[0]
                selected_vecs.append(norm(ev))
            except Exception:
                selected_vecs.append([])
            continue
        ev = embs[(embs["note_id"] == nid) & (embs["chunk_index"] == cidx)]["embedding"].iloc[0]
        en = norm(ev) if isinstance(ev, list) else []
        redundancy = max((cos(en, sv) for sv in selected_vecs if sv), default=0.0)
        mmr = lambda_ * score - (1.0 - lambda_) * redundancy
        # keep a running list of candidates with a threshold
        # simple greedy: if mmr positive, accept
        if mmr >= 0 or len(selected) < K:
            selected.append((score, nid, cidx, text))
            selected_vecs.append(en)

    # Build system prompt with context
    # Fetch titles
    idx = read_parquet_safe(table_path("notes_index"))
    titles = {}
    if not idx.empty:
        for _, r in idx.iterrows():
            titles[r["note_id"]] = r.get("title", "")
    context_lines = []
    citations = []
    for s, nid, cidx, text in selected[:K]:
        title = titles.get(nid, "")
        context_lines.append(f"[note_id={nid}] {title}\n{text}\n")
        citations.append({"note_id": nid, "title": title, "chunk_index": cidx, "score": s})
    sys = "Use ONLY provided context; if not found, reply 'Not found in allowed scope'.\n\nContext:\n" + "\n---\n".join(context_lines)
    msgs = [
        {"role": "system", "content": sys},
        {"role": "user", "content": body.prompt},
    ]
    answer = chat(msgs)
    return {"answer": answer, "citations": citations}


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
def search(q: str, k: int = 5, note_ids: str | None = None, group_ids: str | None = None,
           date_start: int | None = None, date_end: int | None = None):
    # resolve allowed note ids from groups/date filters
    allowed: list[str] | None = None
    if group_ids:
        gm = read_parquet_safe(table_path("group_notes"))
        if not gm.empty:
            gids = [g for g in group_ids.split(",") if g]
            allowed = gm[gm["group_id"].isin(gids)]["note_id"].dropna().unique().tolist()
        else:
            allowed = []
    if note_ids:
        ids = [x for x in note_ids.split(",") if x]
        allowed = ids if allowed is None else [n for n in allowed if n in ids]
    if date_start or date_end:
        df = read_parquet_safe(table_path("notes_index"))
        if not df.empty:
            if date_start:
                df = df[df["updated_at"] >= int(date_start)]
            if date_end:
                df = df[df["updated_at"] <= int(date_end)]
            ids = df["note_id"].tolist()
            allowed = ids if allowed is None else [n for n in allowed if n in ids]
        else:
            allowed = []
    return {"results": query(q, k, allowed)}


def run_api(auto_port: bool = True) -> int:
    """Bootstrap and run the API, returning the port used."""
    bootstrap()
    try:
        start_scheduler()
    except Exception:
        pass
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
