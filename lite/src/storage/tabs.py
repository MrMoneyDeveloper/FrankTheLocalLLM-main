import time
import uuid
from typing import Dict, List, Optional

import pandas as pd

from .parquet_util import atomic_replace, read_parquet_safe, table_path


TABS_TABLE = table_path("tabs")


def _now() -> int:
    return int(time.time() * 1000)


def save_session(session_id: str, tabs: List[Dict]) -> Dict:
    """Persist a tab session.

    Each tab dict may include: { tab_id?, note_id, stack_id?, position? }.
    """
    df = read_parquet_safe(TABS_TABLE)
    if df.empty:
        df = pd.DataFrame(columns=["session_id", "tab_id", "note_id", "stack_id", "position", "created_at"])
    # Drop previous rows for this session
    df = df[df["session_id"] != session_id]
    rows = []
    pos = 0
    for t in tabs:
        rows.append({
            "session_id": session_id,
            "tab_id": t.get("tab_id") or str(uuid.uuid4()),
            "note_id": t["note_id"],
            "stack_id": t.get("stack_id") or None,
            "position": t.get("position") if t.get("position") is not None else pos,
            "created_at": _now(),
        })
        pos += 1
    if rows:
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    atomic_replace(TABS_TABLE, df)
    return {"ok": True, "count": len(rows)}


def load_session(session_id: str) -> Dict:
    df = read_parquet_safe(TABS_TABLE)
    if df.empty:
        return {"tabs": []}
    cur = df[df["session_id"] == session_id]
    if cur.empty:
        return {"tabs": []}
    cur = cur.sort_values("position")
    tabs = cur.to_dict(orient="records")
    return {"tabs": tabs}

