from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..storage import groups as groups_store


router = APIRouter()


class GroupCreate(BaseModel):
    name: str


class GroupRename(BaseModel):
    id: str
    name: str


@router.get("/groups/list")
def groups_list():
    return {"groups": groups_store.list_groups()}


@router.post("/groups/create")
def groups_create(body: GroupCreate):
    try:
        return groups_store.create_group(body.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/rename")
def groups_rename(body: GroupRename):
    try:
        return groups_store.rename_group(body.id, body.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/delete")
def groups_delete(id: str):
    return {"ok": groups_store.delete_group(id)}


@router.post("/groups/add_note")
def groups_add_note(group_id: str, note_id: str):
    return {"ok": groups_store.add_note_to_group(group_id, note_id)}


@router.post("/groups/remove_note")
def groups_remove_note(group_id: str, note_id: str):
    return {"ok": groups_store.remove_note_from_group(group_id, note_id)}


@router.get("/groups/notes")
def groups_notes(group_id: str):
    return {"note_ids": groups_store.list_group_members(group_id)}


class GroupsReorder(BaseModel):
    ordered_ids: list[str]


@router.post("/groups/reorder")
def groups_reorder(body: GroupsReorder):
    return {"ok": groups_store.reorder_groups(body.ordered_ids)}


class GroupNotesReorder(BaseModel):
    group_id: str
    ordered_note_ids: list[str]


@router.post("/groups/reorder_notes")
def groups_reorder_notes(body: GroupNotesReorder):
    return {"ok": groups_store.reorder_group_notes(body.group_id, body.ordered_note_ids)}
