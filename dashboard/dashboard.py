import streamlit as st
import requests

# --------------------------------
# API ENDPOINTS
# --------------------------------
PREDICT_API = "http://127.0.0.1:8000/predict"
CLAIM_API = "http://127.0.0.1:8000/verify_claim"

# --------------------------------
# PAGE CONFIG
# --------------------------------
st.set_page_config(
    page_title="AI News Intelligence Platform",
    layout="wide"
)

st.title("🧠 AI News Intelligence Platform")

st.markdown(
"""
Analyze credibility using:

✅ AI Content Analysis  
✅ Source Credibility  
✅ News Consensus  
✅ Evidence Verification
"""
)

# ==========================================================
# NEWS ANALYSIS MODE
# ==========================================================
st.header("📰 News Article Analysis")

title = st.text_input("News Title")
content = st.text_area("News Content")
source = st.text_input("Source (optional)")

if st.button("Analyze News"):

    if not title or not content:
        st.warning("Please enter title and content.")
    else:

        payload = {
            "title": title,
            "content": content,
            "source": source
        }

        response = requests.post(PREDICT_API, json=payload)

        if response.status_code == 200:

            result = response.json()

            # ---------------- Prediction ----------------
            st.subheader("Prediction Result")

            if result["prediction"] == "REAL":
                st.success(f"Prediction: {result['prediction']}")
            else:
                st.error(f"Prediction: {result['prediction']}")

            st.write(f"Confidence: {result['confidence']}%")

            # ---------------- Trust Analysis ----------------
            trust = result["trust_analysis"]

            st.subheader("🔎 Trust Analysis")

            col1, col2, col3 = st.columns(3)

            col1.metric("Trust Score", f"{trust['trust_score']}%")
            col2.metric("Source Credibility", f"{trust['source_score']}%")
            col3.metric("News Consensus", f"{trust['consensus_score']}%")

            st.write("ML Confidence:", trust["ml_score"])

            # ---------------- Evidence Panel ----------------
            st.subheader("📰 Supporting Evidence")

            evidence = result.get("evidence", [])

            if evidence:
                for ev in evidence:
                    st.markdown(
                        f"""
                        **{ev['title']}**  
                        Source: {ev['source']}  
                        [Read Article]({ev['url']})
                        """
                    )
            else:
                st.info("No supporting articles found yet.")

        else:
            st.error("API connection failed.")


# ==========================================================
# CLAIM VERIFICATION MODE
# ==========================================================
st.markdown("---")
st.header("🧾 Claim Verification Mode")

st.write(
"Paste a Tweet, WhatsApp forward, or social media claim."
)

claim_text = st.text_area(
    "Enter Claim Text"
)

if st.button("Verify Claim"):

    if not claim_text:
        st.warning("Please enter a claim.")
    else:

        response = requests.post(
            CLAIM_API,
            json={"text": claim_text}
        )

        if response.status_code == 200:

            result = response.json()

            # Extracted Claim
            st.subheader("Extracted Claim")
            st.info(result["extracted_claim"])

            # Prediction
            st.subheader("Verification Result")

            if result["prediction"] == "REAL":
                st.success(result["prediction"])
            else:
                st.error(result["prediction"])

            st.write(f"Confidence: {result['confidence']}%")

            # Trust Score
            trust = result["trust_analysis"]

            st.subheader("🔎 Trust Analysis")

            col1, col2, col3 = st.columns(3)

            col1.metric("Trust Score", f"{trust['trust_score']}%")
            col2.metric("Source Credibility", f"{trust['source_score']}%")
            col3.metric("News Consensus", f"{trust['consensus_score']}%")

            st.write("ML Confidence:", trust["ml_score"])

            # Evidence
            st.subheader("📰 Supporting Evidence")

            evidence = result.get("evidence", [])

            if evidence:
                for ev in evidence:
                    st.markdown(
                        f"""
                        **{ev['title']}**  
                        Source: {ev['source']}  
                        [Read Article]({ev['url']})
                        """
                    )
            else:
                st.info("No supporting articles found yet.")

            st.subheader("🌍 Live News Verification")

            live = result.get("live_evidence", [])

            if live:
                for art in live:
                    st.markdown(
                        f"""
                        **{art['title']}**  
                        Source: {art['source']}  
                        [Read Article]({art['url']})
                        """
                    )
            else:
                st.info("No live news evidence found.")

        else:
            st.error("API connection failed.")

st.markdown("---")
st.header("📊 Real-Time News Monitoring")

monitor = requests.get("http://127.0.0.1:8000/monitoring")

if monitor.status_code == 200:

    data = monitor.json()

    if data:

        col1, col2 = st.columns(2)

        col1.metric("Total Articles Collected", data["total_articles"])
        col2.metric("Average Article Length", data["avg_length"])

        st.subheader("Top News Sources")

        st.bar_chart(data["top_sources"])

    else:
        st.info("No monitoring data available yet.")

st.markdown("---")
st.header("📄 Daily Intelligence Report")

if st.button("Generate Today's Report"):

    response = requests.get("http://127.0.0.1:8000/generate_report")

    if response.status_code == 200:
        data = response.json()

        st.success("Report Generated!")

        st.write(data["file"])
    else:
        st.error("Report generation failed.")