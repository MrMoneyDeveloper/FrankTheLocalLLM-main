from typing import List, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from ..storage import tabs as tabs_store


router = APIRouter()


class Tab(BaseModel):
    tab_id: str | None = None
    note_id: str
    stack_id: str | None = None
    position: int | None = None


class SaveSession(BaseModel):
    session_id: str
    tabs: List[Tab]


@router.post("/tabs/save_session")
def save_session(body: SaveSession):
    rows: List[Dict] = [t.model_dump() for t in body.tabs]
    return tabs_store.save_session(body.session_id, rows)


@router.get("/tabs/load_session")
def load_session(session_id: str):
    return tabs_store.load_session(session_id)

