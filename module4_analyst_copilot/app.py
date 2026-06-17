"""Module 4 - Analyst Copilot"""

import os, sys
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from config import REVIEWS_CSV, APP_NAME, GROQ_MODEL
from module1_voice_of_customer.voc_analyzer import get_groq_client


@st.cache_data(show_spinner=False)
def build_context():
    if not os.path.exists(REVIEWS_CSV):
        return None, None
    df = pd.read_csv(REVIEWS_CSV, parse_dates=["date"])
    df["stars"] = pd.to_numeric(df["stars"], errors="coerce")
    df = df.dropna(subset=["stars"])

    total = len(df)
    avg   = df["stars"].mean()
    d_min = df["date"].min().strftime("%Y-%m-%d") if "date" in df.columns else "N/A"
    d_max = df["date"].max().strftime("%Y-%m-%d") if "date" in df.columns else "N/A"

    dist = df["stars"].value_counts().sort_index()
    dist_text = ", ".join([f"{int(k)} star: {int(v)} ({v/total*100:.1f}%)" for k,v in dist.items()])

    if "version" in df.columns:
        va = df.groupby("version")["stars"].agg(avg="mean",count="count").reset_index().sort_values("avg")
        worst_v = "\n".join([f"  v{row.version}: {row.avg:.2f}⭐ ({row.count} reviews)" for row in va.head(3).itertuples(index=False)])
        best_v  = "\n".join([f"  v{row.version}: {row.avg:.2f}⭐ ({row.count} reviews)" for row in va.tail(3).itertuples(index=False)])
    else:
        worst_v = best_v = "N/A"

    low_reviews = df[df["stars"]<=2]["text"].dropna().sample(min(10,len(df[df["stars"]<=2])),random_state=42).tolist()
    low_sample  = "\n".join([f"- {r[:200]}" for r in low_reviews])

    high_reviews = df[df["stars"]>=4]["text"].dropna().sample(min(5,len(df[df["stars"]>=4])),random_state=42).tolist()
    high_sample  = "\n".join([f"- {r[:150]}" for r in high_reviews])

    context = f"""APP STORE REVIEW DATA - {APP_NAME}
====================================
Total reviews: {total:,}
Date range: {d_min} to {d_max}
Average rating: {avg:.2f} / 5.0

RATING DISTRIBUTION:
{dist_text}

LOWEST RATED VERSIONS:
{worst_v}

HIGHEST RATED VERSIONS:
{best_v}

SAMPLE NEGATIVE REVIEWS (1-2 stars):
{low_sample}

SAMPLE POSITIVE REVIEWS (4-5 stars):
{high_sample}
"""
    return context, df


def show():
    st.markdown("## 🤖 Analyst Copilot")
    st.markdown(f"Ask anything about **{APP_NAME}** customer reviews in plain English.")

    with st.spinner("Preparing data context..."):
        context, df = build_context()

    if context is None:
        st.error("No data found. Push a change to trigger the scraper."); return

    try:
        client = get_groq_client()
    except ValueError as e:
        st.error(str(e)); return

    st.markdown("### 💡 Try asking:")
    questions = [
        "What are customers complaining about most?",
        "Which app version caused the most issues?",
        "What do happy customers love?",
        "What is the overall sentiment trend?",
        "What features do users request most?",
        "Why are 1-star reviews being left?",
        "What percentage of reviews mention shipping?",
        "Summarize the top 3 problems to fix.",
    ]
    cols = st.columns(4)
    for i, q in enumerate(questions):
        if cols[i%4].button(q, key=f"q{i}"):
            st.session_state["pending"] = q

    st.markdown("---")

    if "history" not in st.session_state:
        st.session_state["history"] = []

    for msg in st.session_state["history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pending  = st.session_state.pop("pending", "")
    user_in  = st.chat_input("Ask anything about the reviews...")
    question = user_in or pending

    if question:
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state["history"].append({"role":"user","content":question})

        system = f"""You are an expert product analyst for {APP_NAME} with access to this App Store review data:

{context}

Answer using ONLY the data above. Be direct and specific. Use numbers. Under 150 words unless asked for detail.
You are speaking to a Product Manager or VP of Customer Experience."""

        msgs = [{"role":"system","content":system}]
        msgs += [{"role":m["role"],"content":m["content"]} for m in st.session_state["history"][-6:]]

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                resp = client.chat.completions.create(
                    model=GROQ_MODEL, messages=msgs, temperature=0.3, max_tokens=500,
                )
                answer = resp.choices[0].message.content.strip()
                st.markdown(answer)

        st.session_state["history"].append({"role":"assistant","content":answer})

    if st.session_state.get("history"):
        if st.button("Clear conversation"):
            st.session_state["history"] = []
            st.rerun()

    with st.expander("View data context the AI uses"):
        st.code(context, language="text")
