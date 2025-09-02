import time
from typing import Dict, List

import pandas as pd

from ..vectorstore import _collection, embed_texts
from .parquet_util import atomic_replace, table_path, read_parquet_safe


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    if chunk_size <= 0:
        return [text]
    out: List[str] = []
    i = 0
    L = len(text)
    while i < L:
        j = min(L, i + chunk_size)
        out.append(text[i:j])
        # advance with overlap
        ni = j - overlap
        if ni <= i:
            ni = j
        i = ni
    return out


def reindex_note(note_id: str, title: str, text: str, chunk_size: int, overlap: int) -> int:
    # Delete old chunks by metadata filter
    try:
        _collection.delete(where={"note_id": note_id})
    except Exception:
        pass
    if not text:
        return 0
    chunks = chunk_text(text, chunk_size, overlap)
    embs = embed_texts(chunks)
    ids = [f"note:{note_id}:{i}" for i in range(len(chunks))]
    metas: List[Dict] = [{"note_id": note_id, "title": title}] * len(chunks)
    _collection.add(ids=ids, documents=chunks, metadatas=metas, embeddings=embs)
    # also persist to parquet
    df = read_parquet_safe(table_path("embeddings"))
    if df.empty:
        df = pd.DataFrame(columns=["note_id", "chunk_index", "text", "embedding", "updated_at"])
    ts = int(time.time() * 1000)
    rows = [
        {"note_id": note_id, "chunk_index": i, "text": chunks[i], "embedding": list(embs[i]), "updated_at": ts}
        for i in range(len(chunks))
    ]
    # drop old rows for this note_id
    if not df.empty:
        df = df[df["note_id"] != note_id]
    df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    atomic_replace(table_path("embeddings"), df)
    return len(chunks)
