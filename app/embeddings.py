from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.config import get_settings


@lru_cache()
def get_embedder():
    return SentenceTransformer(get_settings().EMBEDDING_MODEL)


def embed(texts):
    vecs = get_embedder().encode(list(texts), normalize_embeddings=True)
    return [v.tolist() for v in vecs]
