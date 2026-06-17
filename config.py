"""
Configuration — edit ONLY these fields for each new brand.

How it works automatically:
  1. If APP_STORE_ID is set → scrapes Apple App Store reviews
  2. If APP_STORE_ID is empty → scrapes Amazon + Reddit automatically
  3. GitHub Actions runs this on every push to config.py
"""

# ── Brand Settings (only thing you change) ────────────────────────────────────
BRAND_NAME   = "Nuuly"
KEYWORDS     = ["Nuuly clothing rental", "Nuuly subscription"]

# ── App Store (leave blank if no app — auto-detects Amazon+Reddit instead) ────
APP_STORE_ID = "1511548818"
APP_COUNTRY  = "us"

# ── Amazon ASINs (auto-used if APP_STORE_ID is blank) ─────────────────────────
# Leave empty [] to auto-search, or add specific ASINs for precision
AMAZON_ASINS = []

# ── Reddit Subreddits to search (auto-used if APP_STORE_ID is blank) ──────────
REDDIT_SUBREDDITS = [
    "beauty", "drugstorebeauty", "makeupaddiction",
    "femalefashionadvice", "frugalfemalefashion", "findfashion"
]

# ── Platform Branding ─────────────────────────────────────────────────────────
PLATFORM_TITLE    = "Retail Intelligence Platform"
PLATFORM_SUBTITLE = "Customer Insights & Operations"
PLATFORM_ICON     = "🏪"

# ── AI Model ─────────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Scraper Settings ──────────────────────────────────────────────────────────
MAX_REVIEW_PAGES   = 10      # App Store: 50 reviews/page × 10 = 500 max
MAX_AMAZON_ASINS   = 5       # Max products to scrape from Amazon
MAX_REDDIT_POSTS   = 200     # Max Reddit posts to pull

# ── Data Paths ────────────────────────────────────────────────────────────────
DATA_DIR       = "data"
REVIEWS_CSV    = "data/reviews.csv"
BUSINESSES_CSV = "data/businesses.csv"

# ── Analytics Settings ────────────────────────────────────────────────────────
ANOMALY_THRESHOLD_STARS = 0.4
SIGNIFICANT_DELTA_STARS = 0.3
