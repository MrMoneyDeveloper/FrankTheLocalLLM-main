import os
import time
import uuid
import hashlib
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .config import NOTES_DIR, load_settings, _atomic_write
from .parquet_util import atomic_replace, read_parquet_safe, table_path


NOTES_INDEX_TABLE = table_path("notes_index")
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


def _note_path(note_id: str) -> str:
    return os.path.join(NOTES_DIR, f"{note_id}.md")


def _note_path_legacy(note_id: str) -> str:
    return os.path.join(NOTES_DIR, f"{note_id}.txt")


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _split_frontmatter(raw: str) -> Tuple[Dict, str]:
    if raw.startswith("---\n"):
        end = raw.find("\n---\n", 4)
        if end != -1:
            header = raw[4:end].strip()
            body = raw[end + 5 :]
            meta: Dict[str, str] = {}
            for line in header.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            return meta, body
    return {}, raw


def _render_frontmatter(meta: Dict[str, str]) -> str:
    lines = ["---"] + [f"{k}: {v}" for k, v in meta.items()] + ["---", ""]
    return "\n".join(lines)


def list_notes() -> List[Dict]:
    df = read_parquet_safe(NOTES_INDEX_TABLE)
    if df.empty:
        return []
    # Map storage columns to API shape
    df = df.sort_values("updated_at", ascending=False)
    out = []
    for _, row in df.iterrows():
        out.append({
            "id": row["note_id"],
            "title": row.get("title", "Untitled"),
            "updated_at": row.get("updated_at"),
        })
    return out


def get_note(note_id: str) -> Dict:
    df = read_parquet_safe(NOTES_INDEX_TABLE)
    row = df[df["note_id"] == note_id]
    if row.empty:
        # try legacy
        path = _note_path_legacy(note_id)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Note not found: {note_id}")
        # synthesize
        title = _normalize_title(None, raw)
        return {"id": note_id, "title": title, "content": raw, "updated_at": _now()}
    path = row.iloc[0]["path"]
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        raw = ""
    meta, body = _split_frontmatter(raw)
    title = row.iloc[0].get("title") or meta.get("title") or _normalize_title(None, body)
    return {"id": note_id, "title": title, "content": body, "updated_at": int(row.iloc[0].get("updated_at") or _now())}


def create_note(title: Optional[str] = None, content: str = "") -> Dict:
    os.makedirs(NOTES_DIR, exist_ok=True)
    note_id = str(uuid.uuid4())
    title = _normalize_title(title, content)
    ts = _now()
    meta = {"id": note_id, "title": title}
    raw = _render_frontmatter(meta) + content
    path = _note_path(note_id)
    _atomic_write(path, raw)
    size = os.path.getsize(path)
    sha = _sha256(content)
    # update parquet index
    df = read_parquet_safe(NOTES_INDEX_TABLE)
    if df.empty:
        df = pd.DataFrame(columns=["note_id", "title", "path", "updated_at", "size", "sha256"])
    rec = {
        "note_id": note_id,
        "title": title,
        "path": path,
        "updated_at": ts,
        "size": int(size),
        "sha256": sha,
    }
    df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
    atomic_replace(NOTES_INDEX_TABLE, df)
    return {"id": note_id, "title": title, "updated_at": ts}


def update_note(note_id: str, title: Optional[str], content: Optional[str]) -> Dict:
    df = read_parquet_safe(NOTES_INDEX_TABLE)
    idx = df.index[df["note_id"] == note_id]
    if len(idx) == 0:
        # allow legacy file fallback
        path = _note_path(note_id)
    else:
        path = df.loc[idx, "path"].iloc[0]
    # read existing
    raw = ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        # attempt legacy .txt
        try:
            with open(_note_path_legacy(note_id), "r", encoding="utf-8") as f:
                raw = f.read()
        except FileNotFoundError:
            raw = ""
    meta, body = _split_frontmatter(raw)
    cur_title = meta.get("title") or (df.loc[idx, "title"].iloc[0] if len(idx) else None) or _normalize_title(None, body)
    new_title = title if title is not None else cur_title
    new_body = content if content is not None else body
    new_meta = {"id": note_id, "title": new_title}
    new_raw = _render_frontmatter(new_meta) + (new_body or "")
    # write
    _atomic_write(_note_path(note_id), new_raw)
    ts = _now()
    size = os.path.getsize(_note_path(note_id))
    sha = _sha256(new_body or "")
    # update index parquet
    dfi = read_parquet_safe(NOTES_INDEX_TABLE)
    if dfi.empty:
        dfi = pd.DataFrame(columns=["note_id", "title", "path", "updated_at", "size", "sha256"])
    if len(idx) == 0:
        # add
        dfi = pd.concat([
            dfi,
            pd.DataFrame([
                {
                    "note_id": note_id,
                    "title": new_title,
                    "path": _note_path(note_id),
                    "updated_at": ts,
                    "size": int(size),
                    "sha256": sha,
                }
            ])
        ], ignore_index=True)
    else:
        dfi.loc[idx, ["title", "path", "updated_at", "size", "sha256"]] = [new_title, _note_path(note_id), ts, int(size), sha]
    atomic_replace(NOTES_INDEX_TABLE, dfi)
    return {"id": note_id, "title": new_title, "updated_at": ts}


def delete_note(note_id: str) -> bool:
    # delete files
    for p in (_note_path(note_id), _note_path_legacy(note_id)):
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
    # remove from parquet
    df = read_parquet_safe(NOTES_INDEX_TABLE)
    if not df.empty:
        df = df[df["note_id"] != note_id]
        atomic_replace(NOTES_INDEX_TABLE, df)
    # remove group mapping
    gm = read_parquet_safe(GROUP_NOTES_TABLE)
    if not gm.empty:
        gm = gm[gm["note_id"] != note_id]
        atomic_replace(GROUP_NOTES_TABLE, gm)
    return True


def list_groups() -> List[Dict]:
    df = read_parquet_safe(GROUPS_TABLE)
    if df.empty:
        return []
    # pass-through for compatibility if using old schema
    cols = list(df.columns)
    if "id" in cols and "name" in cols:
        return df.sort_values("name").to_dict(orient="records")
    if "group_id" in cols and "name" in cols:
        out = []
        for _, r in df.sort_values("name").iterrows():
            out.append({"id": r["group_id"], "name": r["name"]})
        return out
    return []


def search_keyword(q: str, note_ids: Optional[List[str]] = None) -> List[Dict]:
    # naive search across selected notes
    ql = q.lower().strip()
    if not ql:
        return []
    df = read_parquet_safe(NOTES_INDEX_TABLE)
    if df.empty:
        return []
    if note_ids:
        df = df[df["note_id"].isin(note_ids)]
    out: List[Dict] = []
    for _, row in df.iterrows():
        nid = row["note_id"]
        title = row.get("title")
        path = row.get("path") or _note_path(nid)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except FileNotFoundError:
            # try legacy
            try:
                with open(_note_path_legacy(nid), "r", encoding="utf-8") as f:
                    raw = f.read()
            except FileNotFoundError:
                raw = ""
        _, content = _split_frontmatter(raw)
        idx = content.lower().find(ql)
        if idx >= 0 or ql in (title or "").lower():
            start = max(0, idx - 40)
            end = min(len(content), idx + 160)
            snippet = content[start:end].replace("\n", " ")
            out.append({"id": nid, "title": title, "snippet": snippet})
    return out
