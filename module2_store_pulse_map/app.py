"""
Module 2 — Version & Time Intelligence
(Replaces geo map since App Store reviews have no location data)
Shows rating trends by app version, time period, and sentiment distribution.
"""

import os, sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from config import REVIEWS_CSV, APP_NAME


def load_data():
    if not os.path.exists(REVIEWS_CSV):
        return None
    df = pd.read_csv(REVIEWS_CSV, parse_dates=["date"])
    df["stars"] = pd.to_numeric(df["stars"], errors="coerce")
    return df.dropna(subset=["stars"])


def show():
    st.markdown("## 📊 Version & Trend Intelligence")
    st.markdown(f"How **{APP_NAME}** ratings evolve across app versions and time — spot which release hurt or helped.")

    df = load_data()
    if df is None or df.empty:
        st.error("No data yet. Push a change to config.py to trigger the scraper.")
        return

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total      = len(df)
    avg        = df["stars"].mean()
    pct_neg    = (df["stars"] <= 2).mean() * 100
    pct_pos    = (df["stars"] >= 4).mean() * 100
    versions   = df["version"].nunique() if "version" in df.columns else "—"

    # Recent trend (last 30 days vs prior 30 days)
    if "date" in df.columns and not df["date"].isna().all():
        latest = df["date"].max()
        recent = df[df["date"] >= latest - pd.Timedelta(days=30)]["stars"].mean()
        prior  = df[(df["date"] >= latest - pd.Timedelta(days=60)) &
                    (df["date"] <  latest - pd.Timedelta(days=30))]["stars"].mean()
        trend  = round(recent - prior, 2) if not np.isnan(prior) else 0
    else:
        trend = 0

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Total Reviews",   f"{total:,}")
    c2.metric("Avg Rating",      f"{avg:.2f} ⭐")
    c3.metric("1-2 Star",        f"{pct_neg:.1f}%")
    c4.metric("4-5 Star",        f"{pct_pos:.1f}%")
    c5.metric("App Versions",    versions)
    c6.metric("30-day Trend",    f"{trend:+.2f} ⭐", delta=f"{trend:+.2f}")

    st.markdown("---")

    # ── Rating over time ──────────────────────────────────────────────────────
    if "date" in df.columns and not df["date"].isna().all():
        st.markdown("### 📈 Rating Trend Over Time")

        col1, col2 = st.columns([3,1])
        with col2:
            freq = st.selectbox("Interval", ["Weekly","Monthly"], index=1)
        resample_freq = "W" if freq == "Weekly" else "ME"

        monthly = df.set_index("date")["stars"].resample(resample_freq).agg(["mean","count"]).reset_index()
        monthly.columns = ["Period","Avg Rating","Review Count"]
        monthly = monthly[monthly["Review Count"] >= 2]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly["Period"], y=monthly["Avg Rating"],
            name="Avg Rating", line=dict(color="#60a5fa", width=2.5),
            mode="lines+markers", marker=dict(size=5),
        ))
        fig.add_hline(y=df["stars"].mean(), line_dash="dot", line_color="#94a3b8",
                      annotation_text=f"Overall avg: {df['stars'].mean():.2f}")
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          yaxis=dict(range=[1,5], title="Avg Rating"),
                          legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom":True})

    # ── Version analysis ──────────────────────────────────────────────────────
    if "version" in df.columns:
        st.markdown("---")
        st.markdown("### 📱 Rating by App Version")
        st.caption("Which release caused a spike in negative reviews?")

        va = (df.groupby("version")["stars"]
              .agg(avg_rating="mean", review_count="count")
              .reset_index())
        va = va[va["review_count"] >= 3].copy()
        va["avg_rating"] = va["avg_rating"].round(2)
        va = va.sort_values("avg_rating")

        fig2 = px.bar(
            va, x="avg_rating", y="version",
            orientation="h",
            color="avg_rating",
            color_continuous_scale=["#E24B4A","#EF9F27","#1D9E75"],
            range_color=[1,5],
            text="avg_rating",
            hover_data={"review_count":True},
            labels={"avg_rating":"Avg Rating","version":"Version","review_count":"Reviews"},
        )
        fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig2.update_layout(
            height=max(300, len(va)*30),
            margin=dict(l=0,r=0,t=10,b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False, yaxis_title="",
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Worst versions table
        worst = va.nsmallest(5,"avg_rating")[["version","avg_rating","review_count"]]
        best  = va.nlargest(5,"avg_rating")[["version","avg_rating","review_count"]]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**🔴 Lowest Rated Versions**")
            st.dataframe(worst, column_config={
                "avg_rating":    st.column_config.NumberColumn("Avg Rating ⭐", format="%.2f"),
                "review_count":  st.column_config.NumberColumn("Reviews"),
            }, use_container_width=True, hide_index=True)
        with col2:
            st.markdown("**🟢 Highest Rated Versions**")
            st.dataframe(best, column_config={
                "avg_rating":    st.column_config.NumberColumn("Avg Rating ⭐", format="%.2f"),
                "review_count":  st.column_config.NumberColumn("Reviews"),
            }, use_container_width=True, hide_index=True)

    # ── Sentiment over time heatmap ───────────────────────────────────────────
    if "date" in df.columns and not df["date"].isna().all():
        st.markdown("---")
        st.markdown("### 🔥 Review Volume by Rating Over Time")

        df["month"]  = df["date"].dt.to_period("M").astype(str)
        df["rating"] = df["stars"].astype(int).astype(str) + " ⭐"

        heat = df.groupby(["month","rating"]).size().reset_index(name="count")

        fig3 = px.density_heatmap(
            heat, x="month", y="rating", z="count",
            color_continuous_scale=["#1e293b","#1d4ed8","#60a5fa"],
            labels={"month":"Month","rating":"Rating","count":"Review Count"},
        )
        fig3.update_layout(
            height=280,
            margin=dict(l=0,r=0,t=10,b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)
