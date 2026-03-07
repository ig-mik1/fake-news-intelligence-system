import logging
import os
from datetime import datetime, timezone
from threading import Lock
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import chromadb
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import VerifyRequest
from verification.prediction_service import get_model_status, predict_fake_news

LOGGER = logging.getLogger(__name__)
_EVIDENCE_FN = None
_EVIDENCE_INIT_ATTEMPTED = False
_INGEST_LOCK = Lock()
CHROMA_PATH = "./data/vector_storage"
CHROMA_COLLECTION = "news_evidence"


def scheduled_task():
    if not _INGEST_LOCK.acquire(blocking=False):
        LOGGER.warning("Skipping ingestion run because a previous run is still active.")
        return

    try:
        LOGGER.info("Background ingestion triggered.")
        from ingestion.run_ingestion_layer import run_master_ingestion

        run_master_ingestion(query="latest news")
    except Exception as exc:
        LOGGER.exception("Background ingestion failed: %s", exc)
    finally:
        _INGEST_LOCK.release()


def _get_evidence_fn():
    global _EVIDENCE_FN
    global _EVIDENCE_INIT_ATTEMPTED

    if _EVIDENCE_INIT_ATTEMPTED:
        return _EVIDENCE_FN
    if _EVIDENCE_FN is not None:
        return _EVIDENCE_FN
    try:
        from verification.evidence_engine import find_evidence
    except Exception as exc:
        LOGGER.exception("Failed to initialize evidence engine: %s", exc)
        _EVIDENCE_INIT_ATTEMPTED = True
        _EVIDENCE_FN = None
        return None
    _EVIDENCE_INIT_ATTEMPTED = True
    _EVIDENCE_FN = find_evidence
    return _EVIDENCE_FN


def _get_chromadb_status():
    status = {
        "path": CHROMA_PATH,
        "collection": CHROMA_COLLECTION,
        "ready": False,
    }
    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_or_create_collection(name=CHROMA_COLLECTION)
        status["ready"] = True
        status["count"] = collection.count()
    except Exception as exc:
        status["error"] = str(exc)
    return status


def _get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name=CHROMA_COLLECTION)


def _extract_title(document: str, metadata: Dict[str, Any]) -> str:
    title = str((metadata or {}).get("title", "")).strip()
    if title:
        return title

    text = str(document or "").strip()
    if not text:
        return "Untitled"
    if len(text) > 120:
        return f"{text[:117]}..."
    return text


def _normalize_timestamp(raw_value: Any) -> str:
    value = str(raw_value or "").strip()
    if value:
        return value
    # Keep missing timestamps old so they don't dominate "latest" sorting.
    return datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat()


def _parse_timestamp(raw_value: Any) -> datetime:
    normalized = _normalize_timestamp(raw_value)
    iso_value = normalized.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_value)
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _safe_chroma_get(limit: int, include: List[str]) -> Dict[str, Any]:
    collection = _get_chroma_collection()
    try:
        return collection.get(limit=limit, include=include)
    except TypeError:
        # Backward compatibility for clients that don't support `limit`.
        return collection.get(include=include)


def _get_cors_origins() -> List[str]:
    env_value = os.getenv("FNIS_CORS_ORIGINS", "").strip()
    if env_value:
        return [origin.strip() for origin in env_value.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_task, "interval", hours=1)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan, title="FNIS Intelligence API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/verify")
async def verify_news(payload: VerifyRequest):
    headline = payload.headline
    content = payload.content

    try:
        ml_result = predict_fake_news(headline, content=content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Prediction failed.") from exc

    evidence_fn = _get_evidence_fn()
    evidence = []
    warnings = []
    evidence_available = evidence_fn is not None
    if evidence_fn:
        try:
            evidence = evidence_fn(headline) or []
        except Exception as exc:
            LOGGER.exception("Evidence lookup failed: %s", exc)
            warnings.append("Evidence service unavailable. Returned ML-only prediction.")
            evidence_available = False
            evidence = []
    else:
        warnings.append("Evidence service unavailable. Returned ML-only prediction.")
        evidence_available = False

    if len(evidence) > 0:
        evidence_weight = 1.2
    elif evidence_available:
        evidence_weight = 0.8
    else:
        evidence_weight = 1.0
    final_score = min(ml_result["confidence"] * evidence_weight, 100.0)

    return {
        "headline": headline,
        "trust_score": f"{final_score:.2f}%",
        "ml_confidence": f"{ml_result['confidence']}%",
        "prediction": ml_result["label"],
        "supporting_evidence": evidence,
        "warnings": warnings,
    }


@app.get("/healthz")
async def healthz():
    model_status = get_model_status()
    chromadb_status = _get_chromadb_status()
    ready = bool(model_status.get("loaded")) and bool(chromadb_status.get("ready"))
    return {
        "status": "ok" if ready else "degraded",
        "model": model_status,
        "chromadb": chromadb_status,
    }


@app.get("/api/monitoring")
async def get_monitoring_stats():
    return {"status": "Monitoring active", "ingestion_interval": "1 hour"}


@app.get("/api/monitoring/latest")
async def get_monitoring_latest(limit: int = Query(default=20, ge=1, le=100)):
    try:
        sample_size = min(max(limit * 20, 200), 2000)
        payload = _safe_chroma_get(limit=sample_size, include=["documents", "metadatas"])
        ids = payload.get("ids", []) or []
        documents = payload.get("documents", []) or []
        metadatas = payload.get("metadatas", []) or []

        all_items: List[Dict[str, Any]] = []
        for idx, item_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
            document = documents[idx] if idx < len(documents) else ""
            all_items.append(
                {
                    "id": item_id,
                    "title": _extract_title(document, metadata),
                    "source": str(metadata.get("source", "unknown")),
                    "platform": str(metadata.get("platform", "unknown")),
                    "url": str(metadata.get("url", "")),
                    "ingested_at": _normalize_timestamp(metadata.get("ingested_at")),
                    "_parsed_ingested_at": _parse_timestamp(metadata.get("ingested_at")),
                }
            )

        # Newest first globally, then interleave by source to prevent a single-source stream.
        all_items.sort(key=lambda item: item["_parsed_ingested_at"], reverse=True)
        by_source: Dict[str, List[Dict[str, Any]]] = {}
        for item in all_items:
            key = item["source"]
            by_source.setdefault(key, []).append(item)

        interleaved: List[Dict[str, Any]] = []
        source_order = sorted(
            by_source.keys(),
            key=lambda src: by_source[src][0]["_parsed_ingested_at"],
            reverse=True,
        )
        while len(interleaved) < limit:
            added_in_round = False
            for src in source_order:
                if by_source[src]:
                    interleaved.append(by_source[src].pop(0))
                    added_in_round = True
                    if len(interleaved) >= limit:
                        break
            if not added_in_round:
                break

        items = []
        for item in interleaved:
            item.pop("_parsed_ingested_at", None)
            items.append(item)

        return {
            "status": "ok",
            "count": len(items),
            "active_sources": len({item["source"] for item in items}),
            "items": items,
            "source": CHROMA_COLLECTION,
        }
    except Exception as exc:
        LOGGER.exception("Monitoring latest endpoint failed: %s", exc)
        return {
            "status": "degraded",
            "count": 0,
            "items": [],
            "error": "Unable to fetch latest monitoring items.",
        }


@app.get("/api/dashboard/summary")
async def get_dashboard_summary(sample_size: int = Query(default=50, ge=10, le=200)):
    summary = {
        "status": "ok",
        "total_articles": 0,
        "fake_count": 0,
        "real_count": 0,
        "unknown_count": 0,
        "source_distribution": {},
        "estimated_from_sample": False,
        "sample_size": sample_size,
    }
    try:
        collection = _get_chroma_collection()
        total = int(collection.count())
        summary["total_articles"] = total
        if total == 0:
            return summary

        # Pull a bounded slice for quick dashboard analytics.
        max_rows = min(max(total, sample_size), 2000)
        payload = _safe_chroma_get(limit=max_rows, include=["documents", "metadatas"])
        documents = payload.get("documents", []) or []
        metadatas = payload.get("metadatas", []) or []

        source_distribution: Dict[str, int] = {}
        fake_count = 0
        real_count = 0
        unknown_count = 0

        for idx in range(max(len(documents), len(metadatas))):
            metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
            source = str(metadata.get("source", "unknown")).strip() or "unknown"
            source_distribution[source] = source_distribution.get(source, 0) + 1

            raw_label = str(metadata.get("label") or metadata.get("prediction") or "").upper()
            if raw_label in {"FAKE", "LABEL_1"}:
                fake_count += 1
            elif raw_label in {"REAL", "LABEL_0"}:
                real_count += 1
            else:
                unknown_count += 1

        # If labels are not present in metadata, estimate from sample headlines.
        if fake_count == 0 and real_count == 0 and documents:
            summary["estimated_from_sample"] = True
            fake_count = 0
            real_count = 0
            unknown_count = 0
            for idx, document in enumerate(documents[:sample_size]):
                metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
                headline = _extract_title(document, metadata)
                try:
                    prediction = predict_fake_news(headline).get("label", "").upper()
                except Exception:
                    prediction = ""
                if prediction == "FAKE":
                    fake_count += 1
                elif prediction == "REAL":
                    real_count += 1
                else:
                    unknown_count += 1

        summary["fake_count"] = fake_count
        summary["real_count"] = real_count
        summary["unknown_count"] = unknown_count
        summary["source_distribution"] = source_distribution
        return summary
    except Exception as exc:
        LOGGER.exception("Dashboard summary endpoint failed: %s", exc)
        summary["status"] = "degraded"
        return summary
