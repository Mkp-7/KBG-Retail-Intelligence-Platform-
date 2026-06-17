"""
Retail Intelligence Platform — main entry point.
Run with: streamlit run main_app.py
"""

import streamlit as st
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import PLATFORM_TITLE, PLATFORM_SUBTITLE, PLATFORM_ICON

st.set_page_config(
    page_title=PLATFORM_TITLE,
    page_icon=PLATFORM_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stRadio label {
    color: #94a3b8 !important;
    font-size: 13px !important;
    padding: 6px 0 !important;
}

.hero-container {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
    border-radius: 24px;
    padding: 48px 40px;
    margin-bottom: 32px;
    border: 1px solid #1e40af33;
}
.hero-title {
    font-size: 38px;
    font-weight: 700;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 12px;
    line-height: 1.2;
}
.hero-sub { font-size: 16px; color: #94a3b8; line-height: 1.7; max-width: 600px; }

.kpi-row { display: flex; gap: 16px; margin-top: 32px; flex-wrap: wrap; }
.kpi-box {
    background: rgba(255,255,255,0.04);
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 18px 24px;
    min-width: 140px;
}
.kpi-num { font-size: 26px; font-weight: 700; color: #60a5fa; }
.kpi-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; }

.module-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 22px 22px 14px 22px;
    margin-bottom: 4px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.module-card:hover { border-color: #3b82f6; }
.module-card .icon { font-size: 28px; margin-bottom: 10px; display: block; }
.module-card .title { font-size: 15px; font-weight: 600; color: #f1f5f9; margin-bottom: 6px; }
.module-card .desc { font-size: 12px; color: #94a3b8; line-height: 1.6; margin-bottom: 12px; }
.module-card .badge {
    position: absolute; top: 14px; right: 14px;
    font-size: 9px; font-weight: 700;
    padding: 3px 8px; border-radius: 20px; letter-spacing: 0.06em; color: white;
}

[data-testid="stMetric"] {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px !important;
}
[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 12px !important; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 24px !important; }

.main .block-container { background: #0b1120; padding-top: 2rem; }
.stApp { background: #0b1120; }

.stButton button {
    background: linear-gradient(135deg, #2563eb, #7c3aed) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
}
.stButton button:hover { opacity: 0.88 !important; }

h1, h2, h3 { color: #f1f5f9 !important; }
p, li { color: #cbd5e1; }
hr { border-color: #1e293b !important; }

.brand-block {
    text-align: center;
    padding: 20px 0 20px;
    border-bottom: 1px solid #334155;
    margin-bottom: 12px;
}
.brand-icon { font-size: 32px; }
.brand-title { font-size: 14px; font-weight: 600; color: #f1f5f9; margin-top: 6px; }
.brand-sub { font-size: 11px; color: #64748b; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ── Page routing via query params (enables direct navigation) ─────────────────
PAGES = {
    "home":    "🏠  Home",
    "voc":     "🗣️  Voice of Customer AI",
    "map":     "🗺️  Store Pulse Map",
    "test":    "🧪  Test & Learn Autopilot",
    "copilot": "🤖  Analyst Copilot",
}
PAGE_OPTIONS = list(PAGES.values())

# Read current page from query param
params   = st.query_params
cur_page = params.get("page", "home")
if cur_page not in PAGES:
    cur_page = "home"
default_idx = list(PAGES.keys()).index(cur_page)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="brand-block">
        <div class="brand-icon">{PLATFORM_ICON}</div>
        <div class="brand-title">{PLATFORM_TITLE}</div>
        <div class="brand-sub">{PLATFORM_SUBTITLE}</div>
    </div>
    """, unsafe_allow_html=True)

    selected = st.radio(
        "nav",
        options=PAGE_OPTIONS,
        index=default_idx,
        label_visibility="collapsed",
    )

    # Sync sidebar selection → query param
    selected_key = [k for k, v in PAGES.items() if v == selected][0]
    if selected_key != cur_page:
        st.query_params["page"] = selected_key
        st.rerun()

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        st.markdown("---")
        st.warning("⚠️ Add GROQ_API_KEY to a `.env` file.\nFree key: console.groq.com")


def nav_to(page_key: str):
    """Navigate to a page by setting query param and rerunning."""
    st.query_params["page"] = page_key
    st.rerun()


# ── Load home KPI data ────────────────────────────────────────────────────────
def load_home_kpis():
    import pandas as pd
    rev_path = os.path.join(BASE_DIR, "data", "reviews.csv")

    if not os.path.exists(rev_path):
        return None

    rev = pd.read_csv(rev_path, parse_dates=["date"])
    rev["stars"] = pd.to_numeric(rev["stars"], errors="coerce")

    kpis = {}
    kpis["total_reviews"] = len(rev)

    rated = rev.dropna(subset=["stars"])
    kpis["avg_rating"]   = round(rated["stars"].mean(), 2) if len(rated) > 0 else "N/A"
    kpis["pct_negative"] = round((rated["stars"] <= 2).mean() * 100, 1) if len(rated) > 0 else 0
    kpis["pct_positive"] = round((rated["stars"] >= 4).mean() * 100, 1) if len(rated) > 0 else 0

    # Sources breakdown
    if "source" in rev.columns:
        src_counts = rev["source"].str.split("_").str[0].value_counts()
        kpis["sources"] = ", ".join([f"{k}: {v}" for k,v in src_counts.items()])
    else:
        kpis["sources"] = "app_store"

    kpis["versions"] = rev["version"].nunique() if "version" in rev.columns else "N/A"

    if "date" in rev.columns and not rev["date"].isna().all():
        valid_dates = rev["date"].dropna()
        if len(valid_dates) > 0:
            kpis["date_min"] = valid_dates.min().strftime("%b %Y")
            kpis["date_max"] = valid_dates.max().strftime("%b %Y")
        else:
            kpis["date_min"] = kpis["date_max"] = "N/A"
    else:
        kpis["date_min"] = kpis["date_max"] = "N/A"

    return kpis


# ── Pages ─────────────────────────────────────────────────────────────────────
if cur_page == "home":

    kpis = load_home_kpis()

    # Hero
    if kpis:
        hero_reviews = f"{kpis['total_reviews']:,}"
        hero_versions = str(kpis.get("versions", "—"))
        hero_period   = f"{kpis.get('date_min','—')} – {kpis.get('date_max','—')}"
        hero_avg      = str(kpis.get("avg_rating", "—"))
        hero_neg      = f"{kpis.get('pct_negative','—')}%"
        hero_pos      = f"{kpis.get('pct_positive','—')}%"
    else:
        hero_reviews = hero_versions = hero_period = "—"
        hero_avg = hero_neg = hero_pos = "—"

    st.markdown(f"""
    <div class="hero-container">
        <div class="hero-title">Customer Intelligence<br>Operating System</div>
        <div class="hero-sub">
            Real customer reviews. AI-powered analysis. Instant decisions for Store Operations leaders.
        </div>
        <div class="kpi-row">
            <div class="kpi-box">
                <div class="kpi-num">{hero_reviews}</div>
                <div class="kpi-label">Reviews Analyzed</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-num">{hero_versions}</div>
                <div class="kpi-label">App Versions</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-num" style="color:#34d399;">{hero_avg} ⭐</div>
                <div class="kpi-label">Avg Rating</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-num" style="color:#f87171;">{hero_neg}</div>
                <div class="kpi-label">1-2 Star Reviews</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-num" style="color:#34d399;">{hero_pos}</div>
                <div class="kpi-label">4-5 Star Reviews</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-num" style="font-size:18px;">{hero_period}</div>
                <div class="kpi-label">Data Period</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not kpis:
        st.warning("No data loaded yet. Run: `python module1_voice_of_customer/01_extract_reviews.py`")

    st.markdown("### 🚀 Choose a Module")

    modules = [
        ("🗣️", "Voice of Customer AI",
         "Groq AI reads every review, clusters themes, flags anomaly stores, and writes the exec summary. What used to take 3 days takes 30 seconds.",
         "AI POWERED", "#3b82f6", "voc"),
        ("🗺️", "Store Pulse Map",
         "Interactive map benchmarking every location vs its state peer group. Red stores need a Field Leader call this week.",
         "LIVE MAP", "#10b981", "map"),
        ("🧪", "Test & Learn Autopilot",
         "Upload pilot vs control CSVs. Instant t-test, effect size, and a verdict: scale it, kill it, or keep watching.",
         "STATISTICS", "#8b5cf6", "test"),
        ("🤖", "Analyst Copilot",
         "Plain-English chat. Ask 'Which states are trending down?' and get a real answer with numbers — no SQL needed.",
         "AI CHAT", "#f59e0b", "copilot"),
    ]

    col1, col2 = st.columns(2)
    for i, (icon, name, desc, badge, color, page_key) in enumerate(modules):
        col = col1 if i % 2 == 0 else col2
        with col:
            st.markdown(f"""
            <div class="module-card">
                <span class="badge" style="background:{color};">{badge}</span>
                <span class="icon">{icon}</span>
                <div class="title">{name}</div>
                <div class="desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Open {name} →", key=f"nav_{i}", use_container_width=True):
                nav_to(page_key)

elif cur_page == "voc":
    from module1_voice_of_customer.app import show
    show()

elif cur_page == "map":
    from module2_store_pulse_map.app import show
    show()

elif cur_page == "test":
    from module3_test_and_learn.app import show
    show()

elif cur_page == "copilot":
    from module4_analyst_copilot.app import show
    show()
