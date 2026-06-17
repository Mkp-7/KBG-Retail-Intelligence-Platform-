"""
Voice of Customer AI engine.
Handles App Store, Amazon, and Reddit data sources.
"""

import os, json
import pandas as pd
import numpy as np
from groq import Groq
from dotenv import load_dotenv
load_dotenv()


def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY","")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set.\n"
            "Get a free key at https://console.groq.com\n"
            "Add it to .env or Streamlit Secrets."
        )
    return Groq(api_key=api_key)


def cluster_themes(reviews_sample, client, industry="retail"):
    numbered = "\n".join([f"[{i+1}] {r[:300]}" for i,r in enumerate(reviews_sample)])
    prompt = f"""You are analyzing customer reviews/mentions for a {industry} brand.

Here are {len(reviews_sample)} customer reviews:

{numbered}

Identify the TOP 6 recurring themes. For each theme:
- name: short label (3-5 words)
- description: what customers say (1 sentence)
- percent: estimated % of reviews mentioning it (integer)
- sentiment: exactly one of: positive, negative, mixed
- example_quote: one representative phrase under 15 words

Respond ONLY in this JSON format, no other text:
{{"themes": [{{"name":"...","description":"...","percent":0,"sentiment":"positive","example_quote":"..."}}]}}"""

    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0.3, max_tokens=1000,
    )
    raw = r.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    try:
        return json.loads(raw.strip())
    except Exception:
        return {"themes":[], "error":"Parse error", "raw":raw}


def write_exec_summary(themes, anomaly_stores, total_reviews, avg_rating,
                       date_range, client, brand_name="the brand"):
    themes_text = "".join([
        f"- {t['name']} ({t['percent']}%, {t['sentiment']}): {t['description']}\n"
        for t in themes[:5]
    ])
    anomaly_text = "No significant anomalies detected.\n"
    if not anomaly_stores.empty:
        for _, row in anomaly_stores.head(3).iterrows():
            anomaly_text += f"- {row.get('label', row.get('version','?'))}: dropped {row.get('rating_drop',0):.1f} stars\n"

    prompt = f"""Write a weekly executive summary for the VP of Customer Experience at {brand_name}.

DATA:
- Period: {date_range}
- Reviews analyzed: {total_reviews:,}
- Average rating: {avg_rating:.2f if avg_rating else 'N/A'} / 5.0

TOP THEMES:
{themes_text}

ANOMALIES:
{anomaly_text}

Write 3-4 short paragraphs. Plain English. No bullet points. No headers. Under 200 words."""

    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0.4, max_tokens=400,
    )
    return r.choices[0].message.content.strip()
