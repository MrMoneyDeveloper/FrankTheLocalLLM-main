import os
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from .ollama_client import embed_texts

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_DIR", "./lite/data/chroma")
_client = chromadb.PersistentClient(path=CHROMA_DIR, settings=Settings(allow_reset=False))
_collection = _client.get_or_create_collection(name="docs")


def add_documents(docs: list):
    # docs: [{"id": str, "text": str, "meta": dict}]
    if not docs:
        return
    texts = [d["text"] for d in docs]
    ids = [d["id"] for d in docs]
    metas = [d.get("meta", {}) for d in docs]
    embs = embed_texts(texts)
    _collection.add(ids=ids, documents=texts, metadatas=metas, embeddings=embs)


def query(q: str, k: int = 5, note_ids: list | None = None):
    em = embed_texts([q])[0]
    where = None
    if note_ids:
        # Filter by allowed note_ids in metadata
        where = {"note_id": {"$in": note_ids}}
    res = _collection.query(query_embeddings=[em], n_results=k, where=where)
    out = []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        out.append({"text": doc, "meta": meta, "distance": dist})
    return out
