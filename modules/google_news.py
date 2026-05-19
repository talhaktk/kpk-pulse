import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEWS_API_KEY")
BASE_URL = "https://newsapi.org/v2/everything"

KPK_QUERY = (
    "KPK OR \"Khyber Pakhtunkhwa\" OR Peshawar OR Nowshera OR Mardan "
    "OR Swat OR Abbottabad OR \"North Waziristan\" OR \"South Waziristan\" "
    "OR PDMA OR \"KPK police\" OR ISPR OR \"CM KPK\""
)

OTHER_PROVINCES = ["karachi", "sindh", "lahore", "punjab", "balochistan", "quetta"]


def fetch_news(keyword=None, page_size=30):
    if not API_KEY or API_KEY == "your_newsapi_key_here":
        return []   # return empty — no fake data

    query = keyword if keyword else KPK_QUERY
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": API_KEY,
        # Strictly last 24 hours only
        "from": (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        result = _normalize(articles)
        print(f"[google_news] {len(result)} articles (last 24h)")
        return result
    except Exception as e:
        print(f"[google_news] Error: {e}")
        return []


def _normalize(articles):
    results = []
    for a in articles:
        url = a.get("url", "")
        title = (a.get("title") or "").strip()
        # Skip removed/deleted articles and those without URLs
        if not url or not url.startswith("http"):
            continue
        if title in ("[Removed]", "", "None"):
            continue
        # Skip non-KPK stories that only mention other provinces
        text = f"{title} {a.get('description','') or ''}".lower()
        if any(p in text for p in OTHER_PROVINCES) and "kpk" not in text and "khyber" not in text and "peshawar" not in text:
            continue
        results.append({
            "title":        title,
            "description":  (a.get("description") or "").strip(),
            "url":          url,
            "source":       a.get("source", {}).get("name", "NewsAPI"),
            "published_at": a.get("publishedAt", ""),
            "image":        a.get("urlToImage", "") or "",
            "module":       "google_news",
        })
    return results
