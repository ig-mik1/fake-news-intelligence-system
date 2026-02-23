from fastapi import FastAPI
from pydantic import BaseModel
import pickle
import os

from verification.trust_engine import compute_trust
from verification.evidence_engine import find_evidence

from verification.claim_extractor import extract_claim
from verification.trust_engine import compute_trust
from verification.live_fact_checker import search_live_news

from analytics.monitoring import load_recent_news, compute_monitoring_stats
from reports.report_generator import generate_daily_report

app = FastAPI(title="Fake News Intelligence API")


# -------------------------------
# Load Latest Model Automatically
# -------------------------------

MODEL_PATH = "models/model.pkl"
VECTORIZER_PATH = "models/vectorizer.pkl"

model = pickle.load(open(MODEL_PATH, "rb"))
vectorizer = pickle.load(open(VECTORIZER_PATH, "rb"))


# -------------------------------
# Request Schema
# -------------------------------

class NewsInput(BaseModel):
    title: str
    content: str
    source: str | None = None


# -------------------------------
# Prediction Endpoint
# -------------------------------

@app.post("/predict")
def predict(news: NewsInput):

    text = news.title + " " + news.content

    X = vectorizer.transform([text])

    prediction = model.predict(X)[0]

    if hasattr(model, "predict_proba"):
        confidence = model.predict_proba(X)[0].max()
    else:
        confidence = 0.75

    label = "REAL" if prediction == 0 else "FAKE"

    # -------------------------------
    # Trust Intelligence Layer
    # -------------------------------

    trust = compute_trust(
        prediction=label,
        confidence=confidence,
        text=text,
        source=news.source
    )

    evidence = find_evidence(text)

    return {
        "prediction": label,
        "confidence": round(confidence * 100, 2),
        "trust_analysis": trust,
        "evidence": evidence
    }

# -------------------------------
# Claim Verification Endpoint
# -------------------------------
@app.post("/verify_claim")
def verify_claim(data: dict):

    raw_text = data.get("text", "")

    claim = extract_claim(raw_text)

    X = vectorizer.transform([claim])

    pred = model.predict(X)[0]

    if hasattr(model, "predict_proba"):
        confidence = model.predict_proba(X)[0].max()
    else:
        confidence = 0.75

    label = "REAL" if pred == 0 else "FAKE"

    trust = compute_trust(
        prediction=label,
        confidence=confidence,
        text=claim,
        source=None
    )

    evidence = find_evidence(claim)
    live_evidence = search_live_news(claim)

    return {
        "extracted_claim": claim,
        "prediction": label,
        "confidence": round(confidence * 100, 2),
        "trust_analysis": trust,
        "evidence": evidence,
        "live_evidence": live_evidence
    }

# -------------------------------
# Monitoring Endpoint
# -------------------------------

@app.get("/monitoring")
def monitoring():

    df = load_recent_news()

    stats = compute_monitoring_stats(df)

    return stats

# -------------------------------
# Report Generation Endpoint        
# -------------------------------
@app.get("/generate_report")
def generate_report():

    file_path = generate_daily_report()

    return {
        "message": "Report generated",
        "file": file_path
    }
# -------------------------------
# Home Endpoint
# -------------------------------

@app.get("/")
def home():
    return {"message": "Fake News Intelligence System Running"}