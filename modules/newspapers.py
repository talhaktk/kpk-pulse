import feedparser
from datetime import datetime

KPK_KEYWORDS = [
    "kpk", "khyber pakhtunkhwa", "peshawar", "nowshera",
    "mardan", "swat", "abbottabad", "dera ismail khan",
    "bannu", "kohat", "charsadda", "malakand",
]

RSS_FEEDS = {
    "Dawn": "https://www.dawn.com/feeds/home",
    "Geo News": "https://www.geo.tv/rss/1/1",
    "ARY News": "https://arynews.tv/feed/",
    "Express Tribune": "https://tribune.com.pk/feed",
    "Samaa News": "https://www.samaa.tv/feed/",
    "Daily Aaj": "https://www.aaj.tv/feed/",
    "The News": "https://www.thenews.com.pk/rss/1/1",
}


def fetch_articles(max_per_feed=10):
    articles = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                if any(kw in text for kw in KPK_KEYWORDS):
                    articles.append(_normalize(entry, source))
        except Exception as e:
            print(f"[newspapers] {source} error: {e}")

    if not articles:
        return _mock_articles()
    return articles


def _normalize(entry, source):
    published = entry.get("published", "")
    try:
        from email.utils import parsedate_to_datetime
        published = parsedate_to_datetime(published).isoformat()
    except Exception:
        published = datetime.utcnow().isoformat()

    return {
        "title": entry.get("title", ""),
        "description": entry.get("summary", "")[:300],
        "url": entry.get("link", ""),
        "source": source,
        "published_at": published,
        "image": _extract_image(entry),
        "module": "newspapers",
    }


def _extract_image(entry):
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    if hasattr(entry, "enclosures") and entry.enclosures:
        return entry.enclosures[0].get("href", "")
    return ""


def _mock_articles():
    now = datetime.utcnow().isoformat()
    return [
        {
            "title": "Dawn: KPK Assembly Passes Budget Bill",
            "description": "The Khyber Pakhtunkhwa assembly passed the annual budget with focus on education and health.",
            "url": "#",
            "source": "Dawn",
            "published_at": now,
            "image": "",
            "module": "newspapers",
        },
        {
            "title": "Geo: Peshawar Expressway Progress Update",
            "description": "Construction work on the Peshawar Expressway has reached 70% completion.",
            "url": "#",
            "source": "Geo News",
            "published_at": now,
            "image": "",
            "module": "newspapers",
        },
        {
            "title": "Express Tribune: Swat Tourism Record",
            "description": "Swat Valley recorded a record number of tourists in the summer season.",
            "url": "#",
            "source": "Express Tribune",
            "published_at": now,
            "image": "",
            "module": "newspapers",
        },
    ]
