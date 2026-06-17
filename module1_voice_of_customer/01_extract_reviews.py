"""
Smart Data Extractor - automatically chooses the right data source:

  1. APP_STORE_ID set in config.py → scrapes Apple App Store (iTunes RSS)
  2. APP_STORE_ID empty           → scrapes Google Reviews via SerpAPI

No scraping blocks. Works perfectly from GitHub Actions.

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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    BRAND_NAME, KEYWORDS, APP_STORE_ID, APP_COUNTRY,
    MAX_REVIEW_PAGES, DATA_DIR, REVIEWS_CSV,
)

SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

FIELDNAMES = ["review_id", "stars", "date", "title", "text",
              "source", "product", "version", "vote_count"]


def fetch_url(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1 - Apple App Store (iTunes RSS)
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
                entries = entries[1:]
            if not entries:
                print(f"   Page {page}: no more reviews.")
                break
            for e in entries:
                reviews.append({
                    "review_id":  e.get("id", {}).get("label", ""),
                    "stars":      e.get("im:rating", {}).get("label", ""),
                    "date":       e.get("updated", {}).get("label", "")[:10],
                    "title":      e.get("title", {}).get("label", ""),
                    "text":       e.get("content", {}).get("label", "").replace("\n", " ").strip(),
                    "source":     "app_store",
                    "product":    BRAND_NAME,
                    "version":    e.get("im:version", {}).get("label", ""),
                    "vote_count": e.get("im:voteCount", {}).get("label", "0"),
                })
            print(f"   Page {page}: {len(entries)} reviews (total: {len(reviews)})")
            time.sleep(0.5)
        except urllib.error.HTTPError as ex:
            print(f"   Page {page}: HTTP {ex.code} - stopping.")
            break
        except Exception as ex:
            print(f"   Page {page}: {ex} - stopping.")
            break

    print(f"   ✅ App Store: {len(reviews)} reviews")
    return reviews


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2 - Google Reviews via SerpAPI
# ══════════════════════════════════════════════════════════════════════════════

def search_google_place(keyword):
    """Search for a business on Google and return its place data_id."""
    params = urllib.parse.urlencode({
        "engine":  "google_maps",
        "q":       keyword,
        "api_key": SERPAPI_KEY,
        "type":    "search",
    })
    url = f"https://serpapi.com/search?{params}"
    try:
        data    = json.loads(fetch_url(url))
        results = data.get("local_results", [])
        if results:
            place = results[0]
            print(f"   Found: {place.get('title','?')} - rating: {place.get('rating','?')} ({place.get('reviews','?')} reviews)")
            return place.get("data_id", ""), place.get("title", keyword), place.get("rating", "")
    except Exception as ex:
        print(f"   Google Maps search failed: {ex}")
    return "", keyword, ""


def scrape_google_reviews(data_id, place_name, max_pages=5):
    """Scrape Google reviews for a place using its data_id."""
    reviews  = []
    next_token = None

    for page in range(max_pages):
        params = {
            "engine":      "google_maps_reviews",
            "data_id":     data_id,
            "api_key":     SERPAPI_KEY,
            "sort_by":     "newestFirst",
            "hl":          "en",
        }
        if next_token:
            params["next_page_token"] = next_token

        url = f"https://serpapi.com/search?{urllib.parse.urlencode(params)}"
        try:
            data         = json.loads(fetch_url(url))
            raw_reviews  = data.get("reviews", [])

            if not raw_reviews:
                print(f"   Page {page+1}: no more reviews.")
                break

            for r in raw_reviews:
                reviews.append({
                    "review_id":  r.get("review_id", f"{data_id}_{page}_{len(reviews)}"),
                    "stars":      str(r.get("rating", "")),
                    "date":       r.get("date", ""),
                    "title":      "",
                    "text":       r.get("snippet", "").replace("\n", " ").strip(),
                    "source":     "google_reviews",
                    "product":    place_name,
                    "version":    "",
                    "vote_count": str(r.get("likes", 0)),
                })

            print(f"   Page {page+1}: {len(raw_reviews)} reviews (total: {len(reviews)})")
            next_token = data.get("serpapi_pagination", {}).get("next_page_token", "")
            if not next_token:
                break
            time.sleep(0.5)

        except Exception as ex:
            print(f"   Page {page+1} error: {ex}")
            break

    return reviews


def scrape_google_shopping_reviews(keyword):
    """Scrape Google Shopping product reviews for a brand keyword."""
    reviews = []

    # First find products
    params = urllib.parse.urlencode({
        "engine":  "google_shopping",
        "q":       keyword,
        "api_key": SERPAPI_KEY,
        "num":     "10",
    })
    url = f"https://serpapi.com/search?{urllib.parse.urlencode({'engine':'google_shopping','q':keyword,'api_key':SERPAPI_KEY})}"

    try:
        data     = json.loads(fetch_url(url))
        products = data.get("shopping_results", [])[:5]
        print(f"   Found {len(products)} products on Google Shopping")

        for product in products:
            product_id    = product.get("product_id", "")
            product_title = product.get("title", keyword)

            if not product_id:
                continue

            # Get reviews for this product
            rev_params = urllib.parse.urlencode({
                "engine":     "google_product",
                "product_id": product_id,
                "api_key":    SERPAPI_KEY,
            })
            rev_url = f"https://serpapi.com/search?{rev_params}"

            try:
                rev_data    = json.loads(fetch_url(rev_url))
                raw_reviews = rev_data.get("reviews", [])

                for r in raw_reviews:
                    text = r.get("content", "").strip()
                    if not text:
                        continue
                    reviews.append({
                        "review_id":  r.get("id", f"{product_id}_{len(reviews)}"),
                        "stars":      str(r.get("rating", "")),
                        "date":       r.get("date", ""),
                        "title":      r.get("title", ""),
                        "text":       text.replace("\n", " "),
                        "source":     "google_shopping",
                        "product":    product_title,
                        "version":    "",
                        "vote_count": "0",
                    })

                print(f"   {product_title[:40]}: {len(raw_reviews)} reviews")
                time.sleep(0.3)

            except Exception as ex:
                print(f"   Product reviews error: {ex}")

    except Exception as ex:
        print(f"   Google Shopping search failed: {ex}")

    return reviews


def scrape_serpapi():
    """Main SerpAPI scraper - tries Google Maps then Google Shopping."""
    if not SERPAPI_KEY:
        print("   ❌ SERPAPI_KEY not set. Add it to GitHub Secrets and Streamlit Secrets.")
        return []

    print(f"\n🔍 Scraping Google Reviews via SerpAPI for: {BRAND_NAME}...")
    all_reviews = []

    # Try each keyword
    seen_place_ids = set()
    for keyword in KEYWORDS[:3]:
        print(f"\n   Searching: '{keyword}'")

        # Google Maps reviews (for physical stores)
        data_id, place_name, _ = search_google_place(keyword)
        if data_id and data_id not in seen_place_ids:
            seen_place_ids.add(data_id)
            reviews = scrape_google_reviews(data_id, place_name, max_pages=3)
            all_reviews.extend(reviews)
            time.sleep(0.5)

        # Google Shopping reviews (for products)
        shopping_reviews = scrape_google_shopping_reviews(keyword)
        all_reviews.extend(shopping_reviews)
        time.sleep(0.5)

        # Stop if we have enough
        if len(all_reviews) >= 300:
            break

    print(f"\n   ✅ SerpAPI: {len(all_reviews)} total reviews collected")
    return all_reviews


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
    print(f"  Smart Data Extractor - {BRAND_NAME}")
    print("=" * 55)

    all_reviews = []

    if APP_STORE_ID.strip():
        print("\n🔍 App Store ID found → using App Store mode")
        all_reviews = scrape_app_store()
    else:
        print("\n🔍 No App Store ID → using SerpAPI (Google Reviews) mode")
        all_reviews = scrape_serpapi()

    if not all_reviews:
        print("\n⚠️  No reviews collected.")
        print("   Check: SERPAPI_KEY is set in GitHub Secrets")
        print("   Check: KEYWORDS in config.py match real business names")
        sys.exit(1)

    save_reviews(all_reviews)

    # Summary
    sources = {}
    for r in all_reviews:
        src = r.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    print("\n" + "=" * 55)
    print(f"  ✅ Done - {len(all_reviews)} total reviews")
    for src, count in sources.items():
        print(f"     {src}: {count}")
    print("  Run: streamlit run main_app.py")
    print("=" * 55)


if __name__ == "__main__":
    main()
