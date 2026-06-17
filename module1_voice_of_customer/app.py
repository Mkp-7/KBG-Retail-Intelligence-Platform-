"""Module 1 - Voice of Customer AI"""

import os, sys
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from config import REVIEWS_CSV, BRAND_NAME as APP_NAME
from module1_voice_of_customer.voc_analyzer import get_groq_client, cluster_themes, write_exec_summary


@st.cache_data(show_spinner=False)
def load_data():
    if not os.path.exists(REVIEWS_CSV):
        return None
    df = pd.read_csv(REVIEWS_CSV)
    df["stars"] = pd.to_numeric(df["stars"], errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def detect_anomalies(df):
    df = df.copy()
    if "date" not in df.columns or df["date"].isna().all():
        return pd.DataFrame()
    cutoff = df["date"].max() - pd.Timedelta(days=30)
    hist = df.groupby("version")["stars"].agg(hist_avg="mean", total="count").reset_index() if "version" in df.columns else pd.DataFrame()
    recent = df[df["date"] >= cutoff]
    if recent.empty or "version" not in df.columns:
        return pd.DataFrame()
    rec = recent.groupby("version")["stars"].agg(recent_avg="mean", recent_count="count").reset_index()
    merged = hist.merge(rec, on="version", how="inner")
    merged["drop"] = merged["hist_avg"] - merged["recent_avg"]
    return merged[merged["drop"] >= 0.4].sort_values("drop", ascending=False)


def show():
    st.markdown("## 🗣️ Voice of Customer AI")
    st.markdown(f"AI-powered analysis of real **{APP_NAME}** App Store reviews - themes, anomalies, and executive summaries.")

    df = load_data()
    if df is None:
        st.error("No data yet. GitHub Actions will scrape it automatically on next push.\n\nOr run locally:\n```\npython module1_voice_of_customer/01_extract_reviews.py\n```")
        return

    # ── Sidebar filters ───────────────────────────────────────────────────────
    st.sidebar.markdown("### 🗣️ VoC Filters")
    star_filter = st.sidebar.multiselect("Star ratings", [1,2,3,4,5], default=[1,2,3,4,5])
    if "version" in df.columns:
        versions = sorted(df["version"].dropna().unique(), reverse=True)
        sel_ver = st.sidebar.multiselect("App version", versions, default=versions[:5] if len(versions)>5 else versions)
    else:
        sel_ver = []

    if "date" in df.columns and df["date"].notna().any():
        try:
            min_d, max_d = df["date"].min().date(), df["date"].max().date()
            date_range = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
        except Exception:
            date_range = []
    else:
        date_range = []

    mask = df["stars"].isin(star_filter)
    if sel_ver and "version" in df.columns:
        mask &= df["version"].isin(sel_ver)
    if len(date_range) == 2 and "date" in df.columns:
        mask &= (df["date"].dt.date >= date_range[0]) & (df["date"].dt.date <= date_range[1])
    filtered = df[mask].copy()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Reviews",    f"{len(filtered):,}")
    c2.metric("Avg Rating", f"{filtered['stars'].mean():.2f} ⭐")
    c3.metric("1-2 Star",   f"{(filtered['stars']<=2).mean()*100:.1f}%")
    c4.metric("4-5 Star",   f"{(filtered['stars']>=4).mean()*100:.1f}%")
    c5.metric("Versions",   filtered["version"].nunique() if "version" in filtered.columns else "-")

    # ── Charts ────────────────────────────────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Rating Distribution")
        rc = filtered["stars"].value_counts().sort_index().reset_index()
        rc.columns = ["Stars","Count"]
        fig = px.bar(rc, x="Stars", y="Count",
                     color="Stars", color_continuous_scale=["#E24B4A","#EF9F27","#FAC775","#97C459","#1D9E75"])
        fig.update_layout(showlegend=False, height=240, margin=dict(l=0,r=0,t=10,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "version" in filtered.columns:
            st.markdown("### Rating by App Version")
            va = filtered.groupby("version")["stars"].agg(avg="mean", count="count").reset_index()
            va = va[va["count"] >= 3].sort_values("avg")
            va["avg"] = va["avg"].round(2)
            fig2 = px.bar(va, x="version", y="avg", color="avg",
                          color_continuous_scale=["#E24B4A","#EF9F27","#1D9E75"],
                          range_color=[1,5], text="avg")
            fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            fig2.update_layout(height=240, margin=dict(l=0,r=0,t=10,b=0),
                               plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

    if "date" in filtered.columns and not filtered["date"].isna().all():
        st.markdown("### Rating Trend Over Time")
        monthly = filtered.set_index("date")["stars"].resample("ME").mean().reset_index()
        monthly.columns = ["Month","Avg Rating"]
        fig3 = px.line(monthly, x="Month", y="Avg Rating", line_shape="spline")
        fig3.update_traces(line_color="#60a5fa", line_width=2.5)
        fig3.update_layout(height=230, margin=dict(l=0,r=0,t=10,b=0),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           yaxis=dict(range=[1,5]))
        st.plotly_chart(fig3, use_container_width=True)

    # ── AI Theme Analysis ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🤖 AI Theme Analysis")

    n = min(60, len(filtered))
    sample = filtered["text"].dropna().sample(n, random_state=42).tolist()

    if st.button("Run AI Theme Analysis", type="primary"):
        try:
            client = get_groq_client()
        except ValueError as e:
            st.error(str(e)); return
        with st.spinner(f"Groq AI analyzing {n} reviews..."):
            result = cluster_themes(sample, client, industry="retail subscription fashion")
        themes = result.get("themes", [])
        if not themes:
            st.warning("Could not extract themes. Check your GROQ_API_KEY.")
        else:
            st.session_state["themes"] = themes

    if "themes" in st.session_state:
        colors = {"positive":"#1D9E75","negative":"#E24B4A","mixed":"#BA7517"}
        cols = st.columns(2)
        for i, t in enumerate(st.session_state["themes"]):
            c = colors.get(t.get("sentiment","mixed"), "#888")
            with cols[i%2]:
                st.markdown(f"""
                <div style="border:1px solid {c}33;border-left:4px solid {c};
                     border-radius:8px;padding:12px 14px;margin-bottom:12px;">
                    <div style="font-weight:600;font-size:14px;margin-bottom:4px;">{t.get('name','')}</div>
                    <div style="font-size:12px;color:#666;margin-bottom:6px;">{t.get('description','')}</div>
                    <span style="background:{c}22;color:{c};font-size:11px;padding:2px 8px;border-radius:4px;">
                        {t.get('sentiment','')}
                    </span>
                    <span style="font-size:12px;color:#888;margin-left:8px;">~{t.get('percent',0)}% of reviews</span>
                    <div style="font-size:12px;color:#888;margin-top:6px;font-style:italic;">"{t.get('example_quote','')}"</div>
                </div>""", unsafe_allow_html=True)

    # ── Executive Summary ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📄 Executive Summary")

    if st.button("Generate Executive Summary", type="primary"):
    if "themes" not in st.session_state:
        st.warning("Run AI Theme Analysis first.")
    else:
        try:
            client = get_groq_client()
        except ValueError as e:
            st.error(str(e))
            return

        # Safe date handling
        if (
            "date" in filtered.columns
            and not filtered.empty
            and filtered["date"].notna().any()
        ):
            d_min = filtered["date"].min().strftime("%b %d, %Y")
            d_max = filtered["date"].max().strftime("%b %d, %Y")
        else:
            d_min = "N/A"
            d_max = "N/A"

        avg_rating = (
            round(filtered["stars"].mean(), 2)
            if not filtered.empty
            else 0
        )

        with st.spinner("Writing summary..."):
            summary = write_exec_summary(
                themes=st.session_state["themes"],
                anomaly_stores=pd.DataFrame(),
                total_reviews=len(filtered),
                avg_rating=avg_rating,
                date_range=f"{d_min} – {d_max}",
                client=client,
                brand_name=APP_NAME,
            )

        st.markdown(
            f"""
            <div style="background:#F1EFE8;border-radius:12px;padding:20px 24px;border:1px solid #D3D1C7;">
                <div style="font-size:11px;font-weight:600;letter-spacing:0.08em;color:#888;text-transform:uppercase;margin-bottom:12px;">
                    Executive Summary · AI Generated
                </div>
                <div style="font-size:15px;line-height:1.8;color:#2C2C2A;">
                    {summary.replace(chr(10), '<br><br>')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.code(summary, language=None)
        filtered = df[mask].copy()

    # ── Raw reviews ───────────────────────────────────────────────────────────
    st.markdown("---")
    if st.checkbox("Show raw reviews"):
        cols = [c for c in ["date","stars","version","title","text"] if c in filtered.columns]
        st.dataframe(filtered[cols].sort_values("date", ascending=False).head(200),
                     use_container_width=True, hide_index=True)
