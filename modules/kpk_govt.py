"""
KPK Government Departments module.
Sources: official RSS feeds, press release pages, and NewsAPI searches
for department-specific keywords.
"""
import re
import feedparser
import requests
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# Official KPK government department RSS / news feeds
GOVT_FEEDS = {
    "ISPR":             "https://www.ispr.gov.pk/rss/press-release.xml",
    "PDMA KPK":         "https://www.pdma.gov.pk/feed/",
    "KPK Govt":         "https://www.khyberpakhtunkhwa.gov.pk/feed/",
    "CM KPK Office":    "https://cm.kp.gov.pk/feed/",
    "KPK Police":       "https://kppolice.gov.pk/feed/",
    "PDA Peshawar":     "https://pda.gkp.pk/feed/",
    "KPK Education":    "https://esed.kp.gov.pk/feed/",
    "KPK Health":       "https://health.kp.gov.pk/feed/",
    "KPK Finance":      "https://finance.kp.gov.pk/feed/",
    "KPK Agriculture":  "https://www.kpagri.gov.pk/feed/",
    "KPITB":            "https://kpitb.gov.pk/feed/",
    "P&D KPK":          "https://pnd.kp.gov.pk/feed/",
    "TEVTA KPK":        "https://tevta.gkp.pk/feed/",
    "BRT Peshawar":     "https://brt.com.pk/feed/",
}

# NewsAPI department search terms (supplementary)
DEPT_KEYWORDS = [
    "KPK government", "CM KPK", "KP government", "Khyber Pakhtunkhwa government",
    "PDMA KPK", "KPK police", "KPK health department", "KPK education department",
    "Peshawar Development Authority", "KPITB", "TEVTA KPK", "KPK finance",
    "KPK assembly", "ISPR KPK", "Waziristan operation",
]


def fetch_govt_news():
    articles = []

    # Try official RSS feeds
    for dept, url in GOVT_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                for entry in feed.entries[:8]:
                    articles.append(_normalize(entry, dept))
                print(f"[kpk_govt] {dept}: {len(feed.entries[:8])} articles")
        except Exception as e:
            print(f"[kpk_govt] {dept} RSS error: {e}")

    # Supplement with NewsAPI
    api_key = os.getenv("NEWS_API_KEY")
    if api_key and api_key != "your_newsapi_key_here":
        for kw in DEPT_KEYWORDS[:5]:  # limit API calls
            try:
                resp = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": kw,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 5,
                        "apiKey": api_key,
                    },
                    timeout=8,
                )
                for a in resp.json().get("articles", []):
                    articles.append({
                        "title": _clean(a.get("title", "")),
                        "description": _clean(a.get("description", ""))[:280],
                        "url": a.get("url", ""),
                        "source": a.get("source", {}).get("name", "NewsAPI"),
                        "published_at": a.get("publishedAt", datetime.utcnow().isoformat()),
                        "image": a.get("urlToImage", ""),
                        "department": _guess_dept(a.get("title", "") + " " + a.get("description", "")),
                        "module": "kpk_govt",
                    })
            except Exception as e:
                print(f"[kpk_govt] NewsAPI error for '{kw}': {e}")

    articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    # Deduplicate by title
    seen = set()
    unique = []
    for a in articles:
        key = a["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    print(f"[kpk_govt] Total: {len(unique)} department articles")
    return unique if unique else _mock_govt()


def _normalize(entry, dept):
    published = entry.get("published", "")
    try:
        from email.utils import parsedate_to_datetime
        published = parsedate_to_datetime(published).isoformat()
    except Exception:
        published = datetime.utcnow().isoformat()

    return {
        "title": _clean(entry.get("title", "")),
        "description": _clean(entry.get("summary", ""))[:280],
        "url": entry.get("link", ""),
        "source": dept,
        "published_at": published,
        "image": _extract_image(entry),
        "department": dept,
        "module": "kpk_govt",
    }


def _clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _extract_image(entry):
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    if hasattr(entry, "enclosures") and entry.enclosures:
        return entry.enclosures[0].get("href", "")
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.get("summary", ""))
    return match.group(1) if match else ""


def _guess_dept(text):
    text = text.lower()
    if "police" in text: return "KPK Police"
    if "pdma" in text or "disaster" in text: return "PDMA KPK"
    if "health" in text or "hospital" in text: return "KPK Health"
    if "education" in text or "school" in text: return "KPK Education"
    if "finance" in text or "budget" in text: return "KPK Finance"
    if "ispr" in text or "military" in text or "army" in text: return "ISPR"
    if "brt" in text or "transport" in text: return "BRT / Transport"
    if "kpitb" in text or "technology" in text: return "KPITB"
    return "KPK Government"


def _mock_govt():
    now = datetime.utcnow().isoformat()
    return [
        {"title": "PDMA KPK Issues Flood Warning for Nowshera", "description": "Provincial Disaster Management Authority KPK has issued a flood advisory.", "url": "#", "source": "PDMA KPK", "published_at": now, "image": "", "department": "PDMA KPK", "module": "kpk_govt"},
        {"title": "KPK Police Arrests Terror Cell in Peshawar", "description": "Counter-terrorism force arrested five suspects in a joint operation.", "url": "#", "source": "KPK Police", "published_at": now, "image": "", "department": "KPK Police", "module": "kpk_govt"},
        {"title": "CM KPK Inaugurates New Hospital in Mardan", "description": "Chief Minister inaugurated a 200-bed hospital in Mardan district.", "url": "#", "source": "CM KPK Office", "published_at": now, "image": "", "department": "CM KPK Office", "module": "kpk_govt"},
        {"title": "KPITB Launches Digital Skills Program", "description": "KP IT Board launches a free digital skills training program for 10,000 youth.", "url": "#", "source": "KPITB", "published_at": now, "image": "", "department": "KPITB", "module": "kpk_govt"},
    ]
