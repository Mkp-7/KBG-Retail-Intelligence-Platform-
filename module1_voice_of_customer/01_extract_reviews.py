"""
Smart Data Extractor — automatically chooses the right data source:

  1. APP_STORE_ID set in config.py → scrapes Apple App Store (iTunes RSS)
  2. APP_STORE_ID empty           → scrapes Amazon + Reddit automatically

No API keys needed for any source.
Runs automatically via GitHub Actions on every push to config.py.

Usage (local):
    python module1_voice_of_customer/01_extract_reviews.py
"""

import os
import sys
import csv
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    BRAND_NAME, KEYWORDS, APP_STORE_ID, APP_COUNTRY,
    AMAZON_ASINS, REDDIT_SUBREDDITS, MAX_REVIEW_PAGES,
    MAX_AMAZON_ASINS, MAX_REDDIT_POSTS, DATA_DIR, REVIEWS_CSV,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

FIELDNAMES = ["review_id","stars","date","title","text","source","product","version","vote_count"]


def fetch_url(url, extra_headers=None, timeout=20):
    """Fetch a URL and return the response body as string."""
    h = {**HEADERS, **(extra_headers or {})}
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1 — Apple App Store (iTunes RSS)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_app_store():
    print(f"\n📱 Scraping Apple App Store (ID: {APP_STORE_ID})...")
    reviews = []

    for page in range(1, MAX_REVIEW_PAGES + 1):
        url = (f"https://itunes.apple.com/{APP_COUNTRY}/rss/customerreviews"
               f"/page={page}/id={APP_STORE_ID}/sortby=mostrecent/json")
        try:
            data    = json.loads(fetch_url(url))
            entries = data.get("feed", {}).get("entry", [])
            if page == 1 and entries:
                entries = entries[1:]  # skip app metadata entry
            if not entries:
                print(f"   Page {page}: no more reviews.")
                break
            for e in entries:
                reviews.append({
                    "review_id":  e.get("id",{}).get("label",""),
                    "stars":      e.get("im:rating",{}).get("label",""),
                    "date":       e.get("updated",{}).get("label","")[:10],
                    "title":      e.get("title",{}).get("label",""),
                    "text":       e.get("content",{}).get("label","").replace("\n"," ").strip(),
                    "source":     "app_store",
                    "product":    BRAND_NAME,
                    "version":    e.get("im:version",{}).get("label",""),
                    "vote_count": e.get("im:voteCount",{}).get("label","0"),
                })
            print(f"   Page {page}: {len(entries)} reviews (total: {len(reviews)})")
            time.sleep(0.5)
        except urllib.error.HTTPError as ex:
            print(f"   Page {page}: HTTP {ex.code} — stopping.")
            break
        except Exception as ex:
            print(f"   Page {page}: {ex} — stopping.")
            break

    print(f"   ✅ App Store: {len(reviews)} reviews")
    return reviews


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2 — Amazon Product Reviews
# ══════════════════════════════════════════════════════════════════════════════

def search_amazon_asins():
    """Search Amazon for top products matching KEYWORDS and return ASINs."""
    asins = []
    query = urllib.parse.quote_plus(KEYWORDS[0] if KEYWORDS else BRAND_NAME)
    url   = f"https://www.amazon.com/s?k={query}&i=beauty"

    try:
        html  = fetch_url(url, extra_headers={"Accept": "text/html"})
        found = re.findall(r'data-asin="([A-Z0-9]{10})"', html)
        # Deduplicate preserving order
        seen = set()
        for a in found:
            if a not in seen:
                asins.append(a)
                seen.add(a)
        asins = asins[:MAX_AMAZON_ASINS]
        print(f"   Found ASINs on Amazon: {asins}")
    except Exception as ex:
        print(f"   Amazon search failed: {ex}")

    return asins


def scrape_amazon_product(asin):
    """Scrape reviews for one Amazon ASIN via the public reviews page."""
    reviews  = []
    base_url = f"https://www.amazon.com/product-reviews/{asin}?sortBy=recent&pageNumber="

    for page in range(1, 6):  # max 5 pages × ~10 reviews = 50 per product
        try:
            html  = fetch_url(base_url + str(page), extra_headers={"Accept": "text/html"})

            # Extract review blocks
            blocks = re.findall(
                r'data-hook="review".*?(?=data-hook="review"|$)',
                html, re.DOTALL
            )

            # Fallback: extract individual fields directly
            titles  = re.findall(r'data-hook="review-title"[^>]*>.*?<span[^>]*>(.*?)</span>', html, re.DOTALL)
            ratings = re.findall(r'data-hook="review-star-rating"[^>]*>.*?(\d+\.\d+) out of', html, re.DOTALL)
            texts   = re.findall(r'data-hook="review-body"[^>]*>.*?<span[^>]*>(.*?)</span>', html, re.DOTALL)
            dates   = re.findall(r'data-hook="review-date"[^>]*>(.*?)</span>', html, re.DOTALL)
            ids     = re.findall(r'id="([A-Z0-9]{13,})"', html)

            count = min(len(titles), len(ratings), len(texts))
            if count == 0:
                break

            for i in range(count):
                clean_text = re.sub(r'<[^>]+>', '', texts[i]).strip()
                clean_title = re.sub(r'<[^>]+>', '', titles[i]).strip()
                if not clean_text:
                    continue
                reviews.append({
                    "review_id":  ids[i] if i < len(ids) else f"{asin}_{page}_{i}",
                    "stars":      ratings[i] if i < len(ratings) else "",
                    "date":       dates[i].replace("Reviewed in the United States on ","")[:20].strip() if i < len(dates) else "",
                    "title":      clean_title[:200],
                    "text":       clean_text[:1000],
                    "source":     "amazon",
                    "product":    f"{BRAND_NAME} (ASIN: {asin})",
                    "version":    "",
                    "vote_count": "0",
                })

            print(f"   ASIN {asin} page {page}: {count} reviews")
            time.sleep(1.5)  # respectful delay

        except Exception as ex:
            print(f"   ASIN {asin} page {page}: {ex}")
            break

    return reviews


def scrape_amazon():
    print(f"\n🛒 Scraping Amazon reviews for: {BRAND_NAME}...")
    asins = AMAZON_ASINS if AMAZON_ASINS else search_amazon_asins()

    if not asins:
        print("   No ASINs found — skipping Amazon.")
        return []

    all_reviews = []
    for asin in asins[:MAX_AMAZON_ASINS]:
        reviews = scrape_amazon_product(asin)
        all_reviews.extend(reviews)
        time.sleep(1)

    print(f"   ✅ Amazon: {len(all_reviews)} reviews from {len(asins)} products")
    return all_reviews


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 3 — Reddit Posts
# ══════════════════════════════════════════════════════════════════════════════

def scrape_reddit():
    print(f"\n💬 Scraping Reddit mentions of: {BRAND_NAME}...")
    all_posts = []
    query     = urllib.parse.quote_plus(BRAND_NAME)

    for sub in REDDIT_SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/search.json?q={query}&restrict_sr=1&limit=50&sort=new"
        try:
            data  = json.loads(fetch_url(url, extra_headers={"Accept": "application/json"}))
            posts = data.get("data", {}).get("children", [])

            for p in posts:
                d = p.get("data", {})
                text = d.get("selftext", "").strip()
                title = d.get("title", "").strip()
                combined = f"{title}. {text}".strip()
                if len(combined) < 20:
                    continue
                # Only include if brand is actually mentioned
                if BRAND_NAME.lower() not in combined.lower():
                    continue

                all_posts.append({
                    "review_id":  d.get("id",""),
                    "stars":      "",    # Reddit has no star rating — AI infers sentiment
                    "date":       "",
                    "title":      title[:200],
                    "text":       combined[:1000],
                    "source":     f"reddit_r/{sub}",
                    "product":    BRAND_NAME,
                    "version":    "",
                    "vote_count": str(d.get("score", 0)),
                })

                if len(all_posts) >= MAX_REDDIT_POSTS:
                    break

            print(f"   r/{sub}: {len(posts)} posts found, {sum(1 for p in all_posts if f'r/{sub}' in p['source'])} matched")
            time.sleep(0.5)

        except Exception as ex:
            print(f"   r/{sub}: {ex}")

    print(f"   ✅ Reddit: {len(all_posts)} posts mentioning {BRAND_NAME}")
    return all_posts


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def save_reviews(reviews):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REVIEWS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(reviews)
    print(f"\n   💾 Saved {len(reviews)} reviews → {REVIEWS_CSV}")


def main():
    print("=" * 55)
    print(f"  Smart Data Extractor — {BRAND_NAME}")
    print("=" * 55)

    all_reviews = []

    if APP_STORE_ID.strip():
        # ── Mode 1: App Store ─────────────────────────────────────────────────
        print("\n🔍 App Store ID found → using App Store mode")
        all_reviews = scrape_app_store()
    else:
        # ── Mode 2: Amazon + Reddit ───────────────────────────────────────────
        print("\n🔍 No App Store ID → switching to Amazon + Reddit mode")
        amazon_reviews = scrape_amazon()
        reddit_posts   = scrape_reddit()
        all_reviews    = amazon_reviews + reddit_posts

    if not all_reviews:
        print("\n⚠️  No reviews collected. Check config.py settings.")
        sys.exit(1)

    save_reviews(all_reviews)

    # ── Summary ───────────────────────────────────────────────────────────────
    sources = {}
    for r in all_reviews:
        src = r.get("source","unknown").split("_")[0]
        sources[src] = sources.get(src, 0) + 1

    print("\n" + "=" * 55)
    print(f"  ✅ Done — {len(all_reviews)} total reviews collected")
    for src, count in sources.items():
        print(f"     {src}: {count}")
    print("  Run: streamlit run main_app.py")
    print("=" * 55)


if __name__ == "__main__":
    main()
