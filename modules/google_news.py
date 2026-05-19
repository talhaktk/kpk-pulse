import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEWS_API_KEY")
KPK_KEYWORDS = ["KPK", "Khyber Pakhtunkhwa", "Peshawar", "Nowshera", "Mardan", "Swat", "Abbottabad"]
BASE_URL = "https://newsapi.org/v2/everything"


def fetch_news(keyword=None, page_size=20):
    if not API_KEY or API_KEY == "your_newsapi_key_here":
        return _mock_news()

    query = keyword if keyword else " OR ".join(KPK_KEYWORDS)
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": API_KEY,
        "from": (datetime.utcnow() - timedelta(hours=24)).isoformat(),
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        return _normalize(articles)
    except Exception as e:
        print(f"[google_news] Error: {e}")
        return _mock_news()


def _normalize(articles):
    results = []
    for a in articles:
        results.append({
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "url": a.get("url", ""),
            "source": a.get("source", {}).get("name", "NewsAPI"),
            "published_at": a.get("publishedAt", ""),
            "image": a.get("urlToImage", ""),
            "module": "google_news",
        })
    return results


def _mock_news():
    return [
        {
            "title": "KPK Government Announces New Development Projects",
            "description": "The provincial government of Khyber Pakhtunkhwa has announced several new development initiatives.",
            "url": "#",
            "source": "Demo Source",
            "published_at": datetime.utcnow().isoformat(),
            "image": "",
            "module": "google_news",
        },
        {
            "title": "Peshawar BRT Extension Plan Revealed",
            "description": "Officials confirmed plans to extend the Bus Rapid Transit network across Peshawar.",
            "url": "#",
            "source": "Demo Source",
            "published_at": datetime.utcnow().isoformat(),
            "image": "",
            "module": "google_news",
        },
    ]
