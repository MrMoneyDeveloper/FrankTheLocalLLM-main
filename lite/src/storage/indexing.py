from typing import Dict, List

from ..vectorstore import _collection, embed_texts


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
    return len(chunks)

