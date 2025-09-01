import os
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from .bootstrap import bootstrap, find_available_port
from .vectorstore import add_documents, query
from .ollama_client import chat
from .storage.config import load_settings, save_settings
from .storage import notes as notes_store
from .storage import groups as groups_store
from .storage.indexing import reindex_note
from .storage.parquet_util import read_parquet_safe, table_path

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
        df = read_parquet_safe(table_path("notes"))
        if not df.empty:
            if date_start:
                df = df[df["updated_at"] >= int(date_start)]
            if date_end:
                df = df[df["updated_at"] <= int(date_end)]
            ids = df["id"].tolist()
            allowed = ids if allowed is None else [n for n in allowed if n in ids]
        else:
            allowed = []
    return {"results": query(q, k, allowed)}


# Notes API
class NoteCreate(BaseModel):
    title: str | None = None
    content: str | None = ""


class NoteUpdate(BaseModel):
    id: str
    title: str | None = None
    content: str | None = None
    reindex: bool = True


@app.get("/notes/list")
def notes_list():
    return {"notes": notes_store.list_notes()}


@app.get("/notes/get")
def notes_get(id: str):
    try:
        return notes_store.get_note(id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/notes/create")
def notes_create(body: NoteCreate):
    rec = notes_store.create_note(body.title, body.content or "")
    # index on create
    settings = load_settings()
    try:
        reindex_note(rec["id"], rec["title"], body.content or "", settings["CHUNK_SIZE"], settings["CHUNK_OVERLAP"])
    except Exception:
        pass
    return rec


@app.post("/notes/update")
def notes_update(body: NoteUpdate):
    rec = notes_store.update_note(body.id, body.title, body.content)
    if body.reindex:
        # read latest content to index
        try:
            cur = notes_store.get_note(body.id)
            settings = load_settings()
            reindex_note(body.id, rec["title"], cur.get("content", ""), settings["CHUNK_SIZE"], settings["CHUNK_OVERLAP"])
        except Exception:
            pass
    return rec


@app.post("/notes/delete")
def notes_delete(id: str):
    try:
        ok = notes_store.delete_note(id)
        # also remove from vectorstore by metadata
        from .vectorstore import _collection

        try:
            _collection.delete(where={"note_id": id})
        except Exception:
            pass
        return {"ok": ok}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/notes/search")
def notes_search(q: str, note_ids: str | None = None):
    ids = [x for x in (note_ids or "").split(",") if x]
    return {"results": notes_store.search_keyword(q, ids or None)}


# Groups API
class GroupCreate(BaseModel):
    name: str


@app.get("/groups/list")
def groups_list():
    return {"groups": groups_store.list_groups()}


@app.post("/groups/create")
def groups_create(body: GroupCreate):
    try:
        return groups_store.create_group(body.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/groups/delete")
def groups_delete(id: str):
    return {"ok": groups_store.delete_group(id)}


@app.post("/groups/add_note")
def groups_add_note(group_id: str, note_id: str):
    return {"ok": groups_store.add_note_to_group(group_id, note_id)}


@app.post("/groups/remove_note")
def groups_remove_note(group_id: str, note_id: str):
    return {"ok": groups_store.remove_note_from_group(group_id, note_id)}


# Settings API
@app.get("/settings/get")
def settings_get():
    return load_settings()


class SettingsUpdate(BaseModel):
    CHAT_MODEL: str | None = None
    EMBED_MODEL: str | None = None
    CHUNK_SIZE: int | None = None
    CHUNK_OVERLAP: int | None = None
    REINDEX_DEBOUNCE_MS: int | None = None
    SEARCH_THROTTLE_MS: int | None = None
    MAX_CHUNKS_PER_QUERY: int | None = None


@app.post("/settings/update")
def settings_update(body: SettingsUpdate):
    cur = load_settings()
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    return save_settings({**cur, **upd})


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
