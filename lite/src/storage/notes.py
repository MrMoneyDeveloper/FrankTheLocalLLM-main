import os
import time
import uuid
from typing import Dict, List, Optional

import pandas as pd

from .config import NOTES_DIR, load_settings
from .parquet_util import _atomic_replace, read_parquet_safe, table_path


NOTES_TABLE = table_path("notes")
GROUPS_TABLE = table_path("groups")
GROUP_NOTES_TABLE = table_path("group_notes")


def _normalize_title(title: Optional[str], content: str) -> str:
    if title and title.strip():
        return title.strip()
    # derive from first non-empty line
    for line in content.splitlines():
        t = line.strip()
        if t:
            return t[:120]
    return "Untitled"


def _now() -> int:
    return int(time.time() * 1000)


def list_notes() -> List[Dict]:
    df = read_parquet_safe(NOTES_TABLE)
    if df.empty:
        return []
    return df.sort_values("updated_at", ascending=False).to_dict(orient="records")


def get_note(note_id: str) -> Dict:
    df = read_parquet_safe(NOTES_TABLE)
    row = df[df["id"] == note_id]
    if row.empty:
        raise FileNotFoundError(f"Note not found: {note_id}")
    path = os.path.join(NOTES_DIR, f"{note_id}.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    r = row.iloc[0].to_dict()
    r["content"] = content
    return r


def create_note(title: Optional[str] = None, content: str = "") -> Dict:
    os.makedirs(NOTES_DIR, exist_ok=True)
    note_id = str(uuid.uuid4())
    title = _normalize_title(title, content)
    ts = _now()
    # write content
    with open(os.path.join(NOTES_DIR, f"{note_id}.txt"), "w", encoding="utf-8") as f:
        f.write(content)
    # update parquet
    df = read_parquet_safe(NOTES_TABLE)
    rec = {
        "id": note_id,
        "title": title,
        "created_at": ts,
        "updated_at": ts,
    }
    df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
    _atomic_replace(NOTES_TABLE, df)
    return rec


def update_note(note_id: str, title: Optional[str], content: Optional[str]) -> Dict:
    df = read_parquet_safe(NOTES_TABLE)
    idx = df.index[df["id"] == note_id]
    if len(idx) == 0:
        raise FileNotFoundError(f"Note not found: {note_id}")
    path = os.path.join(NOTES_DIR, f"{note_id}.txt")
    existing_content = None
    if content is not None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        existing_content = content
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing_content = f.read()
        except FileNotFoundError:
            existing_content = ""
    # update metadata
    if title is not None:
        df.loc[idx, "title"] = title
    else:
        # auto-title if empty
        df.loc[idx, "title"] = _normalize_title(df.loc[idx, "title"].iloc[0], existing_content or "")
    df.loc[idx, "updated_at"] = _now()
    _atomic_replace(NOTES_TABLE, df)
    return df.loc[idx].iloc[0].to_dict()


def delete_note(note_id: str) -> bool:
    # delete file
    try:
        os.remove(os.path.join(NOTES_DIR, f"{note_id}.txt"))
    except FileNotFoundError:
        pass
    # remove from parquet
    df = read_parquet_safe(NOTES_TABLE)
    if not df.empty:
        df = df[df["id"] != note_id]
        _atomic_replace(NOTES_TABLE, df)
    # remove group mapping
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if not gm.empty:
        gm = gm[gm["note_id"] != note_id]
        _atomic_replace(GROUP_NOTES_TABLE, gm)
    return True


def list_groups() -> List[Dict]:
    df = read_parquet_safe(GROUPS_TABLE)
    if df.empty:
        return []
    return df.sort_values("name").to_dict(orient="records")


def search_keyword(q: str, note_ids: Optional[List[str]] = None) -> List[Dict]:
    # naive search across selected notes
    ql = q.lower().strip()
    if not ql:
        return []
    df = read_parquet_safe(NOTES_TABLE)
    if df.empty:
        return []
    if note_ids:
        df = df[df["id"].isin(note_ids)]
    out: List[Dict] = []
    for _, row in df.iterrows():
        nid = row["id"]
        title = row["title"]
        path = os.path.join(NOTES_DIR, f"{nid}.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = ""
        idx = content.lower().find(ql)
        if idx >= 0 or ql in (title or "").lower():
            start = max(0, idx - 40)
            end = min(len(content), idx + 160)
            snippet = content[start:end].replace("\n", " ")
            out.append({"id": nid, "title": title, "snippet": snippet})
    return out

