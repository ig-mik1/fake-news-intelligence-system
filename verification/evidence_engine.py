import os
import re
from functools import lru_cache
from threading import Lock
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = os.getenv("FNIS_CHROMA_PATH", "./data/vector_storage")
CHROMA_COLLECTION = os.getenv("FNIS_CHROMA_COLLECTION", "news_evidence")
EMBEDDING_MODEL = os.getenv("FNIS_EMBED_MODEL", "all-MiniLM-L6-v2")
EMBED_CACHE_SIZE = int(os.getenv("FNIS_EMBED_CACHE_SIZE", "2048"))
FALLBACK_SCAN_LIMIT = int(os.getenv("FNIS_EVIDENCE_FALLBACK_SCAN_LIMIT", "2000"))
MIN_TOKEN_LEN = 3
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "has",
    "was",
    "are",
    "were",
    "will",
    "would",
    "about",
    "into",
    "after",
    "before",
    "your",
    "their",
    "there",
    "they",
    "them",
    "then",
    "than",
    "what",
    "when",
    "where",
    "which",
}

HIGH_CRED_DOMAINS = {
    "bbc.com",
    "reuters.com",
    "apnews.com",
    "nytimes.com",
    "thehindu.com",
    "aljazeera.com",
    "wsj.com",
    "ft.com",
    "who.int",
    "un.org",
    "nasa.gov",
    "cnn.com",
    "washingtonpost.com",
    "theguardian.com",
    "economist.com",
    "bloomberg.com",
    "forbes.com",
    "time.com",
    "newsweek.com",
    "usatoday.com",
}
MEDIUM_CRED_DOMAINS = {
    "cnn.com",
    "ndtv.com",
    "hindustantimes.com",
    "indiatimes.com",
    "news18.com",
    "indianexpress.com",
    "thetimesofindia.com",
    "scroll.in",
    "thewire.in",
    "outlookindia.com",
    "firstpost.com",
    "livemint.com",
    "business-standard.com",
    "deccanherald.com",
    "thehindubusinessline.com",
}
LOW_CRED_DOMAINS = {
    "breitbart.com",
    "infowars.com",
    "naturalnews.com",
    "dailymail.co.uk",
    "foxnews.com",
    "oann.com",
    "newsmax.com",
    "theblaze.com",
    "pjmedia.com",
    "townhall.com",
}
LOW_CRED_HINTS = {"blog", "wordpress", "blogspot", "substack", "telegram", "t.me"}

_INIT_LOCK = Lock()
_CLIENT = None
_COLLECTION = None
_EMBEDDING_FN = None
_INIT_ATTEMPTED = False
_INIT_ERROR: Optional[str] = None
_EMBEDDING_AVAILABLE = False


def _normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _to_similarity(distance: Any) -> float:
    """Convert Chroma distance metric to similarity score [0, 1]."""
    try:
        distance_value = float(distance)
    except (TypeError, ValueError):
        return 0.0
    # Chroma distances vary by metric. This maps distance to [0, 1].
    return max(0.0, min(1.0, 1.0 / (1.0 + distance_value)))


def _domain_from_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    netloc = parsed.netloc.lower().strip()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _score_source_simple(source: str, url: str) -> float:
    source_key = str(source or "").lower().strip()
    domain = _domain_from_url(url)
    source_domain_hint = source_key.replace(" ", "")

    if any(domain.endswith(high) for high in HIGH_CRED_DOMAINS) or any(
        high.split(".")[0] in source_domain_hint for high in HIGH_CRED_DOMAINS
    ):
        return 0.9

    if any(domain.endswith(med) for med in MEDIUM_CRED_DOMAINS) or any(
        med.split(".")[0] in source_domain_hint for med in MEDIUM_CRED_DOMAINS
    ):
        return 0.7

    if any(domain.endswith(low) for low in LOW_CRED_DOMAINS) or any(
        low.split(".")[0] in source_domain_hint for low in LOW_CRED_DOMAINS
    ):
        return 0.2

    if any(hint in domain for hint in LOW_CRED_HINTS) or any(hint in source_key for hint in LOW_CRED_HINTS):
        return 0.3

    if source_key in {"unknown", ""}:
        return 0.45

    return 0.55


def _to_snippet(text: str, max_len: int = 280) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 3]}..."


def _claim_terms(text: str) -> set:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", str(text or "").lower())
    return {word for word in words if len(word) >= MIN_TOKEN_LEN and word not in STOPWORDS}


def _lexical_similarity(query_text: str, doc_text: str) -> float:
    query_terms = _claim_terms(query_text)
    doc_terms = _claim_terms(doc_text)
    if not query_terms or not doc_terms:
        return 0.0

    overlap = len(query_terms & doc_terms)
    if overlap == 0:
        return 0.0

    precision = overlap / len(doc_terms)
    recall = overlap / len(query_terms)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0
    return max(0.0, min(1.0, f1))


def _init_artifacts() -> None:
    global _CLIENT, _COLLECTION, _EMBEDDING_FN, _INIT_ATTEMPTED, _INIT_ERROR, _EMBEDDING_AVAILABLE
    if _CLIENT is not None and _COLLECTION is not None:
        return
    if _INIT_ATTEMPTED and _INIT_ERROR:
        raise RuntimeError(_INIT_ERROR)

    with _INIT_LOCK:
        if _CLIENT is not None and _COLLECTION is not None:
            return
        if _INIT_ATTEMPTED and _INIT_ERROR:
            raise RuntimeError(_INIT_ERROR)

        try:
            _CLIENT = chromadb.PersistentClient(path=CHROMA_PATH)
            _COLLECTION = _CLIENT.get_or_create_collection(name=CHROMA_COLLECTION)
            _EMBEDDING_FN = None
            _EMBEDDING_AVAILABLE = False
            try:
                _EMBEDDING_FN = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=EMBEDDING_MODEL
                )
                _EMBEDDING_AVAILABLE = True
            except Exception:
                _EMBEDDING_FN = None
                _EMBEDDING_AVAILABLE = False
            _INIT_ATTEMPTED = True
            _INIT_ERROR = None
        except Exception as exc:
            _INIT_ATTEMPTED = True
            _INIT_ERROR = f"Evidence engine initialization failed: {exc}"
            raise RuntimeError(_INIT_ERROR) from exc


def _get_collection():
    _init_artifacts()
    return _COLLECTION


def _get_embedding_fn():
    _init_artifacts()
    if _EMBEDDING_FN is None:
        raise RuntimeError("Embedding model unavailable; using lexical fallback.")
    return _EMBEDDING_FN


@lru_cache(maxsize=EMBED_CACHE_SIZE)
def _embed_query_cached(normalized_query: str) -> tuple:
    embedding_fn = _get_embedding_fn()
    embedding = embedding_fn([normalized_query])[0]
    return tuple(float(x) for x in embedding)


def _query_evidence_semantic(collection, normalized_query: str, top_k: int) -> List[Dict[str, Any]]:
    query_embedding = list(_embed_query_cached(normalized_query))
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(1, top_k),
        include=["documents", "metadatas", "distances"],
    )

    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    evidence: List[Dict[str, Any]] = []
    for idx, document in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
        distance = distances[idx] if idx < len(distances) else 1.0
        similarity = _to_similarity(distance)

        title = str(metadata.get("title", "")).strip()
        if not title:
            title = _to_snippet(str(document), max_len=120) or "Untitled"

        source = str(metadata.get("source", "unknown")).strip() or "unknown"
        url = str(metadata.get("url", "")).strip()
        snippet = _to_snippet(str(document))

        evidence.append(
            {
                "title": title,
                "snippet": snippet,
                "source": source,
                "url": url,
                "distance": round(float(distance), 6) if distance is not None else None,
                "similarity_score": round(similarity, 4),
                "relevance": round(similarity * 100, 2),
            }
        )
    return evidence


def _query_evidence_lexical(collection, normalized_query: str, top_k: int) -> List[Dict[str, Any]]:
    payload = collection.get(limit=max(50, FALLBACK_SCAN_LIMIT), include=["documents", "metadatas"])
    documents = payload.get("documents", []) or []
    metadatas = payload.get("metadatas", []) or []

    scored: List[Dict[str, Any]] = []
    for idx, document in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
        text = str(document or "")
        title = str(metadata.get("title", "")).strip()
        combined = f"{title} {text}".strip()
        similarity = _lexical_similarity(normalized_query, combined)
        if similarity <= 0:
            continue

        final_title = title or (_to_snippet(text, max_len=120) or "Untitled")
        source = str(metadata.get("source", "unknown")).strip() or "unknown"
        url = str(metadata.get("url", "")).strip()
        snippet = _to_snippet(text)
        scored.append(
            {
                "title": final_title,
                "snippet": snippet,
                "source": source,
                "url": url,
                "distance": round(float(1.0 - similarity), 6),
                "similarity_score": round(float(similarity), 4),
                "relevance": round(float(similarity) * 100, 2),
            }
        )

    scored.sort(key=lambda row: row["similarity_score"], reverse=True)
    return scored[: max(1, top_k)]


def query_evidence(query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
    normalized_query = _normalize_query(query_text)
    if not normalized_query:
        return []

    collection = _get_collection()
    if _EMBEDDING_AVAILABLE:
        try:
            evidence = _query_evidence_semantic(collection, normalized_query, top_k * 2)  # Get more for reranking
        except Exception:
            evidence = _query_evidence_lexical(collection, normalized_query, top_k * 2)
    else:
        evidence = _query_evidence_lexical(collection, normalized_query, top_k * 2)

    # Rerank based on combined similarity and source credibility
    for item in evidence:
        source_score = _score_source_simple(item["source"], item["url"])
        item["combined_score"] = item["similarity_score"] * 0.7 + source_score * 0.3

    evidence.sort(key=lambda x: x["combined_score"], reverse=True)
    return evidence[:top_k]


def get_evidence_status() -> Dict[str, Any]:
    status: Dict[str, Any] = {
        "path": CHROMA_PATH,
        "collection": CHROMA_COLLECTION,
        "embedding_model": EMBEDDING_MODEL,
        "ready": False,
    }
    try:
        collection = _get_collection()
        status["ready"] = True
        status["count"] = int(collection.count())
        status["embedding_available"] = bool(_EMBEDDING_AVAILABLE)
        status["retrieval_mode"] = "semantic" if _EMBEDDING_AVAILABLE else "lexical_fallback"
    except Exception as exc:
        status["error"] = str(exc)
    return status
