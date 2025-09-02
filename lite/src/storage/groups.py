import time
import uuid
from typing import Dict, List

import pandas as pd

from .parquet_util import atomic_replace, read_parquet_safe, table_path


GROUPS_TABLE = table_path("groups")
GROUP_NOTES_TABLE = table_path("group_notes")


def _now() -> int:
    return int(time.time() * 1000)


def list_groups() -> List[Dict]:
    df = read_parquet_safe(GROUPS_TABLE)
    if df.empty:
        return []
    # Support both new and legacy schemas
    cols = list(df.columns)
    if "group_id" in cols:
        df = df.sort_values(["position", "name"]) if "position" in cols else df.sort_values("name")
        return [{"id": r["group_id"], "name": r["name"]} for _, r in df.iterrows()]
    # legacy
    return df.sort_values("name").to_dict(orient="records")


def create_group(name: str) -> Dict:
    name = name.strip()
    if not name:
        raise ValueError("Group name required")
    df = read_parquet_safe(GROUPS_TABLE)
    # prevent duplicates by case-insensitive name
    if not df.empty:
        name_lower = df["name"].astype(str).str.lower()
        if any(name_lower == name.lower()):
            row = df[name_lower == name.lower()].iloc[0]
            if "group_id" in df.columns:
                return {"id": row["group_id"], "name": row["name"]}
            return row.to_dict()
    gid = str(uuid.uuid4())
    ts = _now()
    if df.empty:
        df = pd.DataFrame(columns=["group_id", "name", "created_at", "updated_at", "position"])
    pos = int(df["position"].max()) + 1 if ("position" in df.columns and not df.empty) else 0
    rec = {"group_id": gid, "name": name, "created_at": ts, "updated_at": ts, "position": pos}
    df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
    atomic_replace(GROUPS_TABLE, df)
    return {"id": gid, "name": name}


def rename_group(group_id: str, new_name: str) -> Dict:
    df = read_parquet_safe(GROUPS_TABLE)
    if df.empty:
        raise ValueError("No groups")
    if "id" in df.columns:  # legacy
        idx = df.index[df["id"] == group_id]
        if len(idx) == 0:
            raise ValueError("Group not found")
        df.loc[idx, ["name"]] = [new_name]
    else:
        idx = df.index[df["group_id"] == group_id]
        if len(idx) == 0:
            raise ValueError("Group not found")
        df.loc[idx, ["name", "updated_at"]] = [new_name, _now()]
    atomic_replace(GROUPS_TABLE, df)
    return {"id": group_id, "name": new_name}


def delete_group(group_id: str) -> bool:
    df = read_parquet_safe(GROUPS_TABLE)
    if not df.empty:
        if "id" in df.columns:
            df = df[df["id"] != group_id]
        else:
            df = df[df["group_id"] != group_id]
        atomic_replace(GROUPS_TABLE, df)
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if not gm.empty:
        gm = gm[gm["group_id"] != group_id]
        atomic_replace(GROUP_NOTES_TABLE, gm)
    return True


def list_group_members(group_id: str) -> List[str]:
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if gm.empty:
        return []
    return gm[gm["group_id"] == group_id]["note_id"].tolist()


def add_note_to_group(group_id: str, note_id: str) -> bool:
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if gm.empty:
        gm = pd.DataFrame(columns=["group_id", "note_id", "position", "added_at"])
    # avoid duplicates
    exists = not gm[(gm["group_id"] == group_id) & (gm["note_id"] == note_id)].empty
    if exists:
        return True
    pos = int(gm[gm["group_id"] == group_id]["position"].max()) + 1 if ("position" in gm.columns and not gm.empty and not gm[gm["group_id"] == group_id].empty) else 0
    rec = {"group_id": group_id, "note_id": note_id, "position": pos, "added_at": _now()}
    gm = pd.concat([gm, pd.DataFrame([rec])], ignore_index=True)
    atomic_replace(GROUP_NOTES_TABLE, gm)
    return True


def remove_note_from_group(group_id: str, note_id: str) -> bool:
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if gm.empty:
        return True
    gm = gm[~((gm["group_id"] == group_id) & (gm["note_id"] == note_id))]
    atomic_replace(GROUP_NOTES_TABLE, gm)
    return True


def groups_for_note(note_id: str) -> List[str]:
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if gm.empty:
        return []
    return gm[gm["note_id"] == note_id]["group_id"].tolist()


def reorder_groups(ordered_ids: List[str]) -> bool:
    df = read_parquet_safe(GROUPS_TABLE)
    if df.empty:
        return True
    # Normalize schema columns
    id_col = "group_id" if "group_id" in df.columns else "id"
    if "position" not in df.columns:
        df["position"] = 0
    pos_map = {gid: i for i, gid in enumerate(ordered_ids)}
    for idx, row in df.iterrows():
        gid = row[id_col]
        if gid in pos_map:
            df.at[idx, "position"] = pos_map[gid]
            if "updated_at" in df.columns:
                df.at[idx, "updated_at"] = _now()
    atomic_replace(GROUPS_TABLE, df)
    return True


def reorder_group_notes(group_id: str, ordered_note_ids: List[str]) -> bool:
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if gm.empty:
        return True
    if "position" not in gm.columns:
        gm["position"] = 0
    pos_map = {nid: i for i, nid in enumerate(ordered_note_ids)}
    sel = gm["group_id"] == group_id
    for idx, row in gm[sel].iterrows():
        nid = row["note_id"]
        if nid in pos_map:
            gm.at[idx, "position"] = pos_map[nid]
    atomic_replace(GROUP_NOTES_TABLE, gm)
    return True
