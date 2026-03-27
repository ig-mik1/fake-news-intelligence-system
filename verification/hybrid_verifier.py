import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

LOGGER = logging.getLogger(__name__)

TRUST_THRESHOLD = float(os.getenv("FNIS_TRUST_THRESHOLD", "0.6"))
WEIGHT_ML = 0.4
WEIGHT_EVIDENCE = 0.3
WEIGHT_SOURCE = 0.3
EVENT_LOG_PATH = Path(os.getenv("FNIS_VERIFICATION_LOG_PATH", "logs/verification_events.jsonl"))
_LOG_LOCK = Lock()

SUPPORT_CUES = {
    "confirmed",
    "official",
    "according to",
    "reported",
    "announced",
    "statement",
}
CONTRADICT_CUES = {
    "false",
    "fake",
    "hoax",
    "debunk",
    "misleading",
    "not true",
    "no evidence",
    "fact check",
}

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
HIGH_RISK_CLAIM_CUES = {
    "go dark",
    "cure",
    "miracle",
    "hoax",
    "conspiracy",
    "100 percent",
    "100%",
    "shocking",
    "secret",
    "breaking",
    "exposed",
    "banned",
    "they dont want you to know",
    "5g",
    "microchip",
    "mind control",
    "free money",
    "every citizen",
    "lifetime",
    "all loan",
    "moon is made",
    "alien",
    "internet shutdown",
    "bans sunlight",
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def build_claim_text(headline: str, content: Optional[str] = None) -> str:
    head = str(headline or "").strip()
    body = str(content or "").strip()
    return f"{head}\n{body}".strip()


def _claim_terms(text: str) -> set:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", text.lower())
    return {word for word in words if word not in STOPWORDS}


def _contains_any(text: str, phrases: set) -> bool:
    return any(phrase in text for phrase in phrases)


def compute_evidence_consensus_score(claim_text: str, evidence_articles: List[Dict[str, Any]]) -> float:
    if not evidence_articles:
        return 0.5

    claim_terms = _claim_terms(claim_text)
    avg_similarity = 0.0
    weighted_stance_sum = 0.0
    weight_sum = 0.0

    for article in evidence_articles:
        similarity = _clamp01(float(article.get("similarity_score", 0.0)))
        text = f"{article.get('title', '')} {article.get('snippet', '')}".lower()
        evidence_terms = _claim_terms(text)

        if claim_terms:
            overlap = len(claim_terms & evidence_terms) / len(claim_terms)
        else:
            overlap = 0.0

        supports = _contains_any(text, SUPPORT_CUES)
        contradicts = _contains_any(text, CONTRADICT_CUES)
        if contradicts and not supports:
            stance = -1.0
        elif supports and not contradicts:
            stance = 1.0
        else:
            stance = 0.0

        weight = max(0.05, 0.7 * similarity + 0.3 * overlap)
        avg_similarity += similarity
        weighted_stance_sum += stance * weight
        weight_sum += weight

    avg_similarity /= max(1, len(evidence_articles))
    stance_component = (weighted_stance_sum / weight_sum) if weight_sum else 0.0
    stance_score = (stance_component + 1.0) / 2.0
    consensus = 0.7 * avg_similarity + 0.3 * stance_score
    return round(_clamp01(consensus), 6)


def _domain_from_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    netloc = parsed.netloc.lower().strip()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _score_source(source: str, url: str) -> float:
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


def compute_source_score(evidence_articles: List[Dict[str, Any]]) -> float:
    if not evidence_articles:
        return 0.5
    scores = [_score_source(article.get("source", ""), article.get("url", "")) for article in evidence_articles]
    avg = sum(scores) / len(scores)
    return round(_clamp01(avg), 6)


def _format_percent(value_0_to_1: float) -> str:
    return f"{round(_clamp01(value_0_to_1) * 100, 2)}%"


def _claim_risk_score(claim_text: str) -> float:
    """Calculate risk score based on sensational/conspiracy language."""
    text = str(claim_text or "").lower()
    if not text:
        return 0.0
    hits = sum(1 for cue in HIGH_RISK_CLAIM_CUES if cue in text)
    # Saturating risk score to avoid over-penalizing.
    return _clamp01(hits / 3.0)


def extract_claims(text: str) -> List[str]:
    """
    Extract potential claims from text using simple heuristics.
    Splits into sentences and filters those containing claim cues.
    """
    import re
    sentences = re.split(r'[.!?]+', text)
    claims = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        # Check if sentence contains claim cues
        if any(cue in sentence.lower() for cue in HIGH_RISK_CLAIM_CUES) or any(cue in sentence.lower() for cue in SUPPORT_CUES | CONTRADICT_CUES):
            claims.append(sentence)
    return claims[:5]  # Limit to top 5 claims


def build_verification_response(
    headline: str,
    content: Optional[str],
    ml_result: Dict[str, Any],
    evidence_articles: List[Dict[str, Any]],
    evidence_error: Optional[str] = None,
) -> Dict[str, Any]:
    claim_text = build_claim_text(headline, content)
    extracted_claims = extract_claims(claim_text)
    ml_fake_probability = _clamp01(float(ml_result.get("ml_fake_probability", 0.5)))
    evidence_score = compute_evidence_consensus_score(
        claim_text=claim_text,
        evidence_articles=evidence_articles,
    )
    source_score = compute_source_score(evidence_articles)
    claim_risk = _claim_risk_score(claim_text)

    warnings: List[str] = []
    verification_mode = "hybrid"
    system_confidence = "high"
    if evidence_error:
        warnings.append("Evidence retrieval unavailable. Returning ML-biased fallback result.")
        verification_mode = "ml_fallback"
        system_confidence = "low"
        # Penalize confidence when evidence service is unavailable.
        evidence_score = 0.4
        source_score = 0.4
    elif not evidence_articles:
        warnings.append("No supporting evidence retrieved. Trust score is less certain.")
        system_confidence = "medium"
        # Lack of corroboration should be mildly negative, not neutral.
        evidence_score = 0.35
        source_score = 0.5

    # Source credibility should matter only when retrieved evidence is relevant.
    source_alignment = _clamp01(evidence_score * 1.25)
    source_score_effective = 0.5 + (source_score - 0.5) * source_alignment

    trust_score = (
        WEIGHT_ML * (1.0 - ml_fake_probability)
        + WEIGHT_EVIDENCE * evidence_score
        + WEIGHT_SOURCE * source_score_effective
    )

    # Guardrail: if claim looks sensational and external evidence is weak/unavailable,
    # reduce trust to avoid overconfident "REAL" outputs from text-only bias.
    weak_evidence = bool(evidence_error) or evidence_score < 0.5 or not evidence_articles
    if weak_evidence and claim_risk > 0:
        penalty = 0.06 + (0.24 * claim_risk)
        trust_score -= penalty
        trust_score = min(trust_score, 0.59)
        warnings.append("High-risk claim cues detected with weak evidence; trust score penalized.")

    trust_score = _clamp01(trust_score)

    decision = "REAL" if trust_score > TRUST_THRESHOLD else "FAKE"
    ml_confidence = max(ml_fake_probability, 1.0 - ml_fake_probability)

    response = {
        "headline": headline,
        "content_used": bool(str(content or "").strip()),
        "trust_score": round(trust_score, 6),
        "trust_score_percent": _format_percent(trust_score),
        "trust_score_value": round(trust_score, 6),
        "ml_confidence": round(ml_confidence, 6),
        "ml_confidence_percent": _format_percent(ml_confidence),
        "ml_fake_probability": round(ml_fake_probability, 6),
        "evidence_score": round(evidence_score, 6),
        "source_score": round(source_score, 6),
        "source_score_effective": round(source_score_effective, 6),
        "decision": decision,
        "prediction": decision,  # Backward-compatible key
        "evidence_articles": evidence_articles,
        "supporting_evidence": evidence_articles,  # Backward-compatible key
        "extracted_claims": extracted_claims,
        "warnings": warnings,
        "verification_mode": verification_mode,
        "system_confidence": system_confidence,
    }
    return response


def log_verification_event(result: Dict[str, Any]) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "headline": str(result.get("headline", ""))[:500],
        "decision": result.get("decision"),
        "trust_score_value": result.get("trust_score_value"),
        "ml_fake_probability": result.get("ml_fake_probability"),
        "evidence_score": result.get("evidence_score"),
        "source_score": result.get("source_score"),
        "evidence_count": len(result.get("evidence_articles", []) or []),
        "verification_mode": result.get("verification_mode"),
        "system_confidence": result.get("system_confidence"),
    }
    try:
        EVENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=True)
        with _LOG_LOCK:
            with EVENT_LOG_PATH.open("a", encoding="utf-8") as file:
                file.write(line + "\n")
    except Exception as exc:
        LOGGER.exception("Failed to write verification event log: %s", exc)
