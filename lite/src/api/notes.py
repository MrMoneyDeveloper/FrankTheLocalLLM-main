from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..storage import notes as notes_store


router = APIRouter()


class NoteCreate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = ""


class NoteUpdate(BaseModel):
    id: str
    title: Optional[str] = None
    content: Optional[str] = None
    reindex: bool = True
    reindex_now: bool = False


@router.get("/notes/list")
def notes_list():
    return {"notes": notes_store.list_notes()}


@router.get("/notes/get")
def notes_get(id: str):
    try:
        return notes_store.get_note(id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/notes/create")
def notes_create(body: NoteCreate):
    rec = notes_store.create_note(body.title, body.content or "")
    # indexing handled by caller if desired; legacy app triggers indexing here
    return rec


@router.post("/notes/update")
def notes_update(body: NoteUpdate):
    rec = notes_store.update_note(body.id, body.title, body.content)
    # Debounced reindex or immediate
    if body.reindex or body.reindex_now:
        try:
            from ..scheduler import schedule_reindex

            schedule_reindex(body.id, immediate=bool(body.reindex_now))
        except Exception:
            pass
    return rec


@router.post("/notes/delete")
def notes_delete(id: str):
    try:
        ok = notes_store.delete_note(id)
        # also remove from vectorstore by metadata
        from ..vectorstore import _collection

        try:
            _collection.delete(where={"note_id": id})
        except Exception:
            pass
        return {"ok": ok}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/notes/search")
def notes_search(q: str, note_ids: str | None = None):
    ids: List[str] = [x for x in (note_ids or "").split(",") if x]
    return {"results": notes_store.search_keyword(q, ids or None)}
