import uuid
from typing import Dict, List

import pandas as pd

from .parquet_util import _atomic_replace, read_parquet_safe, table_path


GROUPS_TABLE = table_path("groups")
GROUP_NOTES_TABLE = table_path("group_notes")


def list_groups() -> List[Dict]:
    df = read_parquet_safe(GROUPS_TABLE)
    if df.empty:
        return []
    return df.sort_values("name").to_dict(orient="records")


def create_group(name: str) -> Dict:
    name = name.strip()
    if not name:
        raise ValueError("Group name required")
    df = read_parquet_safe(GROUPS_TABLE)
    # prevent duplicates by case-insensitive name
    if not df.empty and any(df["name"].str.lower() == name.lower()):
        # return existing
        row = df[df["name"].str.lower() == name.lower()].iloc[0]
        return row.to_dict()
    gid = str(uuid.uuid4())
    rec = {"id": gid, "name": name}
    df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
    _atomic_replace(GROUPS_TABLE, df)
    return rec


def delete_group(group_id: str) -> bool:
    df = read_parquet_safe(GROUPS_TABLE)
    if not df.empty:
        df = df[df["id"] != group_id]
        _atomic_replace(GROUPS_TABLE, df)
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if not gm.empty:
        gm = gm[gm["group_id"] != group_id]
        _atomic_replace(GROUP_NOTES_TABLE, gm)
    return True


def list_group_members(group_id: str) -> List[str]:
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if gm.empty:
        return []
    return gm[gm["group_id"] == group_id]["note_id"].tolist()


def add_note_to_group(group_id: str, note_id: str) -> bool:
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if gm.empty:
        gm = pd.DataFrame(columns=["group_id", "note_id"])
    # avoid duplicates
    exists = not gm[(gm["group_id"] == group_id) & (gm["note_id"] == note_id)].empty
    if exists:
        return True
    gm = pd.concat([gm, pd.DataFrame([[group_id, note_id]], columns=["group_id", "note_id"])], ignore_index=True)
    _atomic_replace(GROUP_NOTES_TABLE, gm)
    return True


def remove_note_from_group(group_id: str, note_id: str) -> bool:
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if gm.empty:
        return True
    gm = gm[~((gm["group_id"] == group_id) & (gm["note_id"] == note_id))]
    _atomic_replace(GROUP_NOTES_TABLE, gm)
    return True


def groups_for_note(note_id: str) -> List[str]:
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if gm.empty:
        return []
    return gm[gm["note_id"] == note_id]["group_id"].tolist()

