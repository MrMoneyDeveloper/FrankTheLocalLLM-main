from fastapi import APIRouter
from pydantic import BaseModel

from ..storage.config import load_settings, save_settings


router = APIRouter()


@router.get("/settings/get")
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
    SIMPLE_MODE: bool | None = None


@router.post("/settings/update")
def settings_update(body: SettingsUpdate):
    cur = load_settings()
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    return save_settings({**cur, **upd})
