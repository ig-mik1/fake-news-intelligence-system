import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from threading import Lock
from typing import Any, Dict, List, Optional

import chromadb
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env before importing local modules that read FNIS_* at import time.
load_dotenv()

from api.schemas import FeedbackRequest, VerifyRequest
from verification.evidence_engine import get_evidence_status, query_evidence
from verification.hybrid_verifier import (
    build_claim_text,
    build_verification_response,
    log_verification_event,
)
from verification.prediction_service import get_model_status, predict_fake_news

LOGGER = logging.getLogger(__name__)
_INGEST_LOCK = Lock()
_VERIFY_LOCK = Lock()
_FEEDBACK_LOCK = Lock()
_VERIFY_RATE_STATE: Dict[str, List[float]] = {}
_FEEDBACK_RATE_STATE: Dict[str, List[float]] = {}
_FEEDBACK_RECENT_HASHES: Dict[str, float] = {}
CHROMA_PATH = "./data/vector_storage"
CHROMA_COLLECTION = "news_evidence"
EVIDENCE_TIMEOUT_SECONDS = float(os.getenv("FNIS_EVIDENCE_TIMEOUT_SECONDS", "8"))
FEEDBACK_PATH = Path(os.getenv("FNIS_FEEDBACK_PATH", "data/feedback/verification_feedback.jsonl"))
VERIFY_RATE_LIMIT_PER_MINUTE = int(os.getenv("FNIS_VERIFY_RATE_LIMIT_PER_MINUTE", "30"))
FEEDBACK_REQUIRE_API_KEY = os.getenv("FNIS_FEEDBACK_REQUIRE_API_KEY", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}
FEEDBACK_API_KEY = os.getenv("FNIS_FEEDBACK_API_KEY", "").strip()
FEEDBACK_RATE_LIMIT_PER_HOUR = int(os.getenv("FNIS_FEEDBACK_RATE_LIMIT_PER_HOUR", "20"))
FEEDBACK_DUPLICATE_COOLDOWN_SECONDS = int(
    os.getenv("FNIS_FEEDBACK_DUPLICATE_COOLDOWN_SECONDS", "21600")
)
TRUST_X_FORWARDED_FOR = os.getenv("FNIS_TRUST_X_FORWARDED_FOR", "false").strip().lower() in {
    "1",
    "true",
    "yes",
}


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


def _normalize_text(value: Optional[str]) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _feedback_signature(payload: FeedbackRequest) -> str:
    base = "||".join(
        [
            _normalize_text(payload.headline),
            _normalize_text(payload.content),
            str(payload.human_label).upper(),
        ]
    )
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "").strip()
    if TRUST_X_FORWARDED_FOR and xff:
        return xff.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _check_verify_rate_limit(client_ip: str) -> None:
    now_ts = time.time()
    cutoff_window = now_ts - 60

    with _VERIFY_LOCK:
        # Prune old entries globally to prevent unbounded map growth.
        stale_ips = []
        for ip, events in _VERIFY_RATE_STATE.items():
            fresh = [ts for ts in events if ts >= cutoff_window]
            if fresh:
                _VERIFY_RATE_STATE[ip] = fresh
            else:
                stale_ips.append(ip)
        for ip in stale_ips:
            _VERIFY_RATE_STATE.pop(ip, None)

        ip_events = _VERIFY_RATE_STATE.get(client_ip, [])
        if len(ip_events) >= VERIFY_RATE_LIMIT_PER_MINUTE:
            retry_after = int(max(1, 60 - (now_ts - min(ip_events))))
            raise HTTPException(
                status_code=429,
                detail=f"Verify rate limit exceeded. Retry after {retry_after} seconds.",
            )

        ip_events.append(now_ts)
        _VERIFY_RATE_STATE[client_ip] = ip_events


def _enforce_feedback_api_key(x_feedback_key: Optional[str]) -> None:
    if not FEEDBACK_REQUIRE_API_KEY:
        return
    if not FEEDBACK_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Feedback authentication is enabled but server key is missing.",
        )
    if not x_feedback_key or not hmac.compare_digest(x_feedback_key, FEEDBACK_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid feedback API key.")


def _check_feedback_rate_and_dedup(payload: FeedbackRequest, client_ip: str) -> Dict[str, Any]:
    now_ts = time.time()
    signature = _feedback_signature(payload)
    cutoff_window = now_ts - 3600
    dedup_cutoff = now_ts - FEEDBACK_DUPLICATE_COOLDOWN_SECONDS

    with _FEEDBACK_LOCK:
        # Prune old per-IP entries globally to prevent unbounded map growth.
        stale_ips = []
        for ip, events in _FEEDBACK_RATE_STATE.items():
            fresh = [ts for ts in events if ts >= cutoff_window]
            if fresh:
                _FEEDBACK_RATE_STATE[ip] = fresh
            else:
                stale_ips.append(ip)
        for ip in stale_ips:
            _FEEDBACK_RATE_STATE.pop(ip, None)

        # Prune old per-IP entries.
        ip_events = _FEEDBACK_RATE_STATE.get(client_ip, [])
        if len(ip_events) >= FEEDBACK_RATE_LIMIT_PER_HOUR:
            retry_after = int(max(1, 3600 - (now_ts - min(ip_events))))
            raise HTTPException(
                status_code=429,
                detail=f"Feedback rate limit exceeded. Retry after {retry_after} seconds.",
            )

        # Prune stale dedup signatures.
        stale_keys = [key for key, ts in _FEEDBACK_RECENT_HASHES.items() if ts < dedup_cutoff]
        for key in stale_keys:
            _FEEDBACK_RECENT_HASHES.pop(key, None)

        last_seen = _FEEDBACK_RECENT_HASHES.get(signature)
        if last_seen is not None and (now_ts - last_seen) < FEEDBACK_DUPLICATE_COOLDOWN_SECONDS:
            remaining = int(FEEDBACK_DUPLICATE_COOLDOWN_SECONDS - (now_ts - last_seen))
            return {
                "duplicate": True,
                "duplicate_retry_after_seconds": max(1, remaining),
                "signature": signature,
            }

        ip_events.append(now_ts)
        _FEEDBACK_RATE_STATE[client_ip] = ip_events
        _FEEDBACK_RECENT_HASHES[signature] = now_ts

    return {"duplicate": False, "signature": signature}


def _append_feedback_event_secure(
    payload: FeedbackRequest,
    client_ip: str,
    user_agent: str,
    feedback_signature: str,
) -> str:
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "headline": payload.headline,
        "content": payload.content,
        "model_decision": payload.model_decision,
        "human_label": payload.human_label,
        "notes": payload.notes,
        "review_status": "pending",
        "approved_for_training": False,
        "feedback_signature": feedback_signature,
        "client_ip_hash": hashlib.sha1(client_ip.encode("utf-8")).hexdigest(),
        "user_agent": (user_agent or "")[:300],
    }
    line = json.dumps(event, ensure_ascii=True)
    with _FEEDBACK_LOCK:
        with FEEDBACK_PATH.open("a", encoding="utf-8") as file:
            file.write(line + "\n")
    return str(FEEDBACK_PATH)


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
async def verify_news(
    payload: VerifyRequest,
    request: Request,
):
    _check_verify_rate_limit(_get_client_ip(request))

    headline = payload.headline
    content = payload.content
    claim_text = build_claim_text(headline, content)

    ml_future = asyncio.create_task(
        asyncio.to_thread(predict_fake_news, headline, content)
    )
    evidence_future = asyncio.create_task(
        asyncio.to_thread(query_evidence, claim_text, 5)
    )

    try:
        ml_result = await ml_future
    except ValueError as exc:
        evidence_future.cancel()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        evidence_future.cancel()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        evidence_future.cancel()
        raise HTTPException(status_code=500, detail="Prediction failed.") from exc

    evidence_articles = []
    evidence_error = None
    try:
        evidence_articles = await asyncio.wait_for(
            evidence_future,
            timeout=EVIDENCE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        evidence_future.cancel()
        evidence_error = "Evidence lookup timed out."
        LOGGER.warning("Evidence lookup timed out after %s seconds.", EVIDENCE_TIMEOUT_SECONDS)
    except Exception as exc:
        evidence_error = str(exc)
        LOGGER.warning("Evidence lookup failed: %s", exc)

    result = build_verification_response(
        headline=headline,
        content=content,
        ml_result=ml_result,
        evidence_articles=evidence_articles,
        evidence_error=evidence_error,
    )
    log_verification_event(result)
    return result


@app.post("/api/feedback")
async def submit_feedback(
    payload: FeedbackRequest,
    request: Request,
    x_feedback_key: Optional[str] = Header(default=None, alias="X-Feedback-Key"),
):
    try:
        _enforce_feedback_api_key(x_feedback_key)
        client_ip = _get_client_ip(request)
        guard_result = _check_feedback_rate_and_dedup(payload, client_ip=client_ip)
        if guard_result["duplicate"]:
            return {
                "status": "ignored",
                "message": "Duplicate feedback ignored for cooldown window.",
                "retry_after_seconds": guard_result["duplicate_retry_after_seconds"],
            }

        path = _append_feedback_event_secure(
            payload=payload,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent", ""),
            feedback_signature=guard_result["signature"],
        )
        return {
            "status": "ok",
            "message": "Feedback recorded for retraining.",
            "storage_path": path,
            "review_status": "pending",
        }
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.exception("Failed to store feedback event: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to store feedback.") from exc


@app.get("/healthz")
async def healthz():
    model_status = get_model_status()
    chromadb_status = _get_chromadb_status()
    evidence_status = get_evidence_status()
    ready = (
        bool(model_status.get("loaded"))
        and bool(chromadb_status.get("ready"))
        and bool(evidence_status.get("ready"))
    )
    return {
        "status": "ok" if ready else "degraded",
        "model": model_status,
        "chromadb": chromadb_status,
        "evidence": evidence_status,
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