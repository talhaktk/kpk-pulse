"""
KPK Trending Topics — two sources, both reliable:

1. Bing News RSS for Pakistan/KPK (free, no API key)
2. Keyword frequency analysis on live KPK headlines (self-contained fallback)

pytrends is NOT used — Google has rate-blocked it globally.
"""
import re
import feedparser
import requests
from datetime import datetime
from collections import Counter

BING_RSS_URLS = [
    "https://www.bing.com/news/search?q=KPK+Khyber+Pakhtunkhwa+Peshawar&format=rss&setmkt=en-PK",
    "https://www.bing.com/news/search?q=Pakistan+KPK+news+today&format=rss&setmkt=en-PK",
    "https://news.google.com/rss/search?q=KPK+Peshawar+Khyber+Pakhtunkhwa&hl=en-PK&gl=PK&ceid=PK:en",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Place names and entities to surface as trends
KNOWN_ENTITIES = [
    "Peshawar", "Swat", "Mardan", "Abbottabad", "Nowshera", "Chitral",
    "Dir", "Kohat", "Bannu", "Buner", "Charsadda", "Bajaur",
    "Waziristan", "PDMA", "KPK Police", "ISPR", "KPITB", "BRT",
    "PTI", "CM KPK", "KPK Assembly", "Malakand", "Kurram",
    "Ali Amin", "Shehryar", "Imran Khan",
]


def fetch_trends():
    # 1. Try Bing / Google News RSS (fast, no auth)
    results = _from_rss()
    if results:
        return results

    # 2. Fallback: keyword frequency from live newspaper headlines
    return _from_headlines()


def _from_rss():
    for url in BING_RSS_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=6)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            if not feed.entries:
                continue

            # Count most-mentioned KPK entities in headlines
            counter = Counter()
            entry_map = {}
            for entry in feed.entries[:30]:
                title = _clean(entry.get("title", ""))
                for ent in KNOWN_ENTITIES:
                    if ent.lower() in title.lower():
                        counter[ent] += 1
                        if ent not in entry_map:
                            entry_map[ent] = {
                                "title": title,
                                "url":   entry.get("link", ""),
                            }

            if not counter:
                continue

            results = []
            for i, (topic, count) in enumerate(counter.most_common(12), 1):
                related = entry_map.get(topic, {})
                results.append({
                    "rank":        i,
                    "title":       topic,
                    "score":       min(100, count * 20),
                    "traffic":     f"Mentioned {count}x in latest KPK news",
                    "url":         f"https://trends.google.com/trends/explore?q={topic.replace(' ', '+')}&geo=PK",
                    "news_title":  related.get("title", ""),
                    "news_url":    related.get("url", ""),
                    "published_at": datetime.utcnow().isoformat(),
                    "module":      "google_trends",
                })
            print(f"[google_trends] {len(results)} trends via RSS ({url[:40]})")
            return results

        except Exception as e:
            print(f"[google_trends] RSS error: {e}")
    return []


def _from_headlines():
    """Extract trending keywords from our newspaper RSS feeds directly."""
    try:
        from modules.newspapers import fetch_articles
        articles = fetch_articles(max_per_feed=20)
        all_text = " ".join(a.get("title", "") for a in articles)

        counter = Counter()
        for ent in KNOWN_ENTITIES:
            count = len(re.findall(re.escape(ent), all_text, re.IGNORECASE))
            if count > 0:
                counter[ent] = count

        if not counter:
            return []

        results = []
        for i, (topic, count) in enumerate(counter.most_common(10), 1):
            results.append({
                "rank":        i,
                "title":       topic,
                "score":       min(100, count * 15),
                "traffic":     f"Mentioned {count}x today",
                "url":         f"https://trends.google.com/trends/explore?q={topic.replace(' ', '+')}&geo=PK",
                "news_title":  "",
                "published_at": datetime.utcnow().isoformat(),
                "module":      "google_trends",
            })
        print(f"[google_trends] {len(results)} trends via headline analysis")
        return results
    except Exception as e:
        print(f"[google_trends] headline fallback error: {e}")
        return []


def _clean(text):
    return re.sub(r"<[^>]+>", " ", text or "").strip()
