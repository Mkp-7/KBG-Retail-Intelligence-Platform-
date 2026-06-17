"""
Module 3 — Test & Learn Autopilot
"""

import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats


def cohens_d(a, b):
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 0.0
    pooled = np.sqrt(((n1-1)*np.var(a,ddof=1)+(n2-1)*np.var(b,ddof=1))/(n1+n2-2))
    return (np.mean(a)-np.mean(b))/pooled if pooled else 0.0


def verdict(p, d, pilot_mean, control_mean):
    sig  = p < 0.05
    big  = abs(d) >= 0.2
    pos  = pilot_mean > control_mean
    if sig and big and pos:
        return "SCALE IT UP", "#1D9E75", "Statistically significant and practically meaningful improvement. Recommend expanding to the next group of locations immediately."
    if sig and big and not pos:
        return "KILL THE PILOT", "#E24B4A", "Pilot is significantly underperforming control locations. Recommend halting and investigating root cause."
    if sig and not big:
        return "MONITOR", "#BA7517", "Statistically significant but small effect. Continue collecting data for 2-4 more weeks before deciding."
    return "TOO EARLY TO CALL", "#5F5E5A", f"Not enough data yet. Current p-value is {p:.3f} (need < 0.05). Keep running."


def sample_csv(label):
    import random
    random.seed(42 if label=="pilot" else 99)
    dates = pd.date_range("2024-01-01","2024-06-30",freq="W")
    rows = []
    base = 3.8 if label=="pilot" else 3.5
    for d in dates:
        for _ in range(random.randint(5,15)):
            rows.append({"date":d.strftime("%Y-%m-%d"),
                         "stars":min(5,max(1,round(base+random.gauss(0,0.8))))})
    return pd.DataFrame(rows).to_csv(index=False)


def show():
    st.markdown("## Test & Learn Autopilot")
    st.markdown(
        "Upload pilot and control location CSVs. "
        "Get instant statistical significance and a clear verdict: **scale it, kill it, or keep watching.**"
    )

    with st.expander("Download sample CSVs"):
        c1, c2 = st.columns(2)
        c1.download_button("sample_pilot.csv", data=sample_csv("pilot"),
                            file_name="sample_pilot.csv", mime="text/csv")
        c2.download_button("sample_control.csv", data=sample_csv("control"),
                            file_name="sample_control.csv", mime="text/csv")
        st.caption("CSV must have: `date` (YYYY-MM-DD) and `stars` (1–5) columns.")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Pilot Locations** — running the new initiative")
        pilot_file = st.file_uploader("Upload pilot CSV", type=["csv"], key="pilot")
    with c2:
        st.markdown("**Control Locations** — business as usual")
        ctrl_file = st.file_uploader("Upload control CSV", type=["csv"], key="control")

    if not pilot_file or not ctrl_file:
        st.info("Upload both CSVs above to run the analysis.")
        return

    try:
        pdf = pd.read_csv(pilot_file, parse_dates=["date"])
        cdf = pd.read_csv(ctrl_file,  parse_dates=["date"])
    except Exception as e:
        st.error(f"Error reading files: {e}")
        return

    for df, name in [(pdf,"pilot"),(cdf,"control")]:
        if "stars" not in df.columns:
            st.error(f"{name} CSV must have a 'stars' column.")
            return

    pdf["stars"] = pd.to_numeric(pdf["stars"], errors="coerce")
    cdf["stars"] = pd.to_numeric(cdf["stars"], errors="coerce")
    pdf = pdf.dropna(subset=["stars"])
    cdf = cdf.dropna(subset=["stars"])

    pa, ca = pdf["stars"].values, cdf["stars"].values
    _, p = stats.ttest_ind(pa, ca, equal_var=False)
    d      = cohens_d(pa, ca)
    pm, cm = float(np.mean(pa)), float(np.mean(ca))

    verd, color, detail = verdict(p, d, pm, cm)

    st.markdown("---")
    st.markdown(
        f"""<div style="background:{color}15;border:2px solid {color};border-radius:12px;padding:20px 24px;margin-bottom:20px;">
            <div style="font-size:26px;font-weight:700;color:{color};margin-bottom:8px;">{verd}</div>
            <div style="font-size:14px;color:#444;line-height:1.6;">{detail}</div>
        </div>""", unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Pilot Avg ⭐",  f"{pm:.2f}", f"{pm-cm:+.2f} vs control")
    c2.metric("Control Avg ⭐", f"{cm:.2f}")
    c3.metric("P-Value",        f"{p:.4f}", "significant" if p<0.05 else "not yet")
    c4.metric("Effect Size (d)", f"{abs(d):.2f}")
    c5.metric("Sample (P/C)",   f"{len(pa):,} / {len(ca):,}")

    st.markdown("---")
    st.markdown("### Weekly Trend: Pilot vs Control")
    pw = pdf.set_index("date")["stars"].resample("W").mean().reset_index()
    cw = cdf.set_index("date")["stars"].resample("W").mean().reset_index()
    pw.columns = cw.columns = ["Week","Avg"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pw["Week"], y=pw["Avg"], name="Pilot",
                             line=dict(color="#1D9E75",width=2.5), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=cw["Week"], y=cw["Avg"], name="Control",
                             line=dict(color="#E24B4A",width=2.5,dash="dot"), mode="lines+markers"))
    fig.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      yaxis=dict(range=[1,5]), legend=dict(orientation="h",y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Rating Distribution")
    star_data = pd.DataFrame({
        "Stars":  [f"{s}⭐" for s in range(1,6)]*2,
        "Pct":    [(pa==s).mean()*100 for s in range(1,6)] + [(ca==s).mean()*100 for s in range(1,6)],
        "Group":  ["Pilot"]*5 + ["Control"]*5,
    })
    fig2 = px.bar(star_data, x="Stars", y="Pct", color="Group", barmode="group",
                  color_discrete_map={"Pilot":"#1D9E75","Control":"#E24B4A"},
                  labels={"Pct":"% of Reviews"})
    fig2.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0),
                       plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

    if p >= 0.05:
        st.markdown("---")
        st.markdown("### How much more data do you need?")
        cur_d   = abs(d) if abs(d) > 0.05 else 0.2
        n_need  = int(np.ceil((2.80**2)*2/(cur_d**2)))
        n_more  = max(0, n_need - min(len(pa),len(ca)))
        c1,c2,c3 = st.columns(3)
        c1.metric("Current sample (smaller)", min(len(pa),len(ca)))
        c2.metric("Needed for 80% power",     n_need)
        c3.metric("Additional needed",         n_more)
