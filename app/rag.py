"""RAG store for product docs + policies."""
import os
from pathlib import Path
import chromadb
from app.config import get_settings
from app.embeddings import embed

_client = None


def client():
    global _client
    if _client is None:
        s = get_settings()
        os.makedirs(s.CHROMA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=s.CHROMA_DIR)
    return _client


def collection():
    return client().get_or_create_collection("product_docs",
                                             metadata={"hnsw:space": "cosine"})


def ingest_file(path: str, doc_type: str = "general"):
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")
    chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
    if not chunks:
        return 0
    col = collection()
    ids = [p.name + "::" + str(i) for i in range(len(chunks))]
    metas = [{"source": p.name, "doc_type": doc_type, "chunk": i}
             for i in range(len(chunks))]
    col.upsert(ids=ids, documents=chunks, metadatas=metas, embeddings=embed(chunks))
    return len(chunks)


def search_docs(query: str, k: int = 4):
    col = collection()
    try:
        res = col.query(query_embeddings=embed([query])[0], n_results=k,
                        include=["documents", "metadatas", "distances"])
    except Exception:
        return []
    out = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0],
                               res["distances"][0]):
        out.append({"text": doc, "source": meta.get("source", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "score": round(1 - float(dist), 3)})
    return out
