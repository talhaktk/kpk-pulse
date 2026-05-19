import feedparser
import re
from datetime import datetime

# If ONLY these appear with zero KPK keywords → exclude
OTHER_PROVINCES = [
    "karachi", "sindh", "lahore", "punjab", "balochistan",
    "quetta", "multan", "faisalabad", "hyderabad", "gwadar",
    "sukkur", "larkana",
]

# English + Urdu KPK keywords for filtering
KPK_KEYWORDS = [
    # English
    "kpk", "khyber pakhtunkhwa", "peshawar", "nowshera", "mardan", "swat",
    "abbottabad", "dera ismail khan", "bannu", "kohat", "charsadda",
    "malakand", "buner", "dir", "chitral", "waziristan", "bajaur",
    "mohmand", "khyber", "kurram", "lakki marwat", "tank", "hangu",
    "kpk government", "cm kpk", "pda", "pdma kpk",
    # Urdu transliteration
    "khyber", "peshwar", "swabi", "haripur",
]

# KPK-specific channels shown without filtering (inherently KPK content)
KPK_CHANNELS = {
    "Khyber News":    "https://www.khybernews.tv/feed/",
    "AVT Khyber":     "https://www.avt.com.pk/feed/",
    "Mashriq":        "https://mashriqtv.pk/feed/",
    "Daily Aaj":      "https://www.aaj.tv/feed/",
}

# National sources — filter for KPK relevance
NATIONAL_FEEDS = {
    "Dawn":            "https://www.dawn.com/feeds/home",
    "Geo News":        "https://www.geo.tv/rss/1/1",
    "ARY News":        "https://arynews.tv/feed/",
    "Express Tribune": "https://tribune.com.pk/feed",
    "Samaa News":      "https://www.samaa.tv/feed/",
    "The News":        "https://www.thenews.com.pk/rss/1/1",
    "92 News":         "https://92newshd.tv/feed/",
    "BOL News":        "https://www.bolnews.com/feed/",
    "Dunya News":      "https://dunyanews.tv/index.php/en?format=feed&type=rss",
    "Pakistan Today":  "https://www.pakistantoday.com.pk/feed/",
}

# Urdu-language sources — filter for KPK relevance
URDU_FEEDS = {
    "Jang":            "https://jang.com.pk/rss",
    "Express Urdu":    "https://www.express.pk/rss/latest-news",
    "Geo Urdu":        "https://urdu.geo.tv/rss/",
    "ARY Urdu":        "https://urdu.arynews.tv/feed/",
    "Nawa-i-Waqt":     "https://www.nawaiwaqt.com.pk/rss",
}


def fetch_articles(max_per_feed=15):
    articles = []

    # KPK-specific channels — no filter needed
    for source, url in KPK_CHANNELS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_per_feed]:
                articles.append(_normalize(entry, source, lang="ur" if source in ("Mashriq",) else "en"))
            print(f"[newspapers] {source}: {len(feed.entries[:max_per_feed])} articles")
        except Exception as e:
            print(f"[newspapers] {source} error: {e}")

    # National + Urdu — filter for KPK
    for feed_group in (NATIONAL_FEEDS, URDU_FEEDS):
        for source, url in feed_group.items():
            try:
                feed = feedparser.parse(url)
                count = 0
                for entry in feed.entries[:max_per_feed]:
                    text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                    if _is_kpk_relevant(text):
                        articles.append(_normalize(entry, source))
                        count += 1
                if count:
                    print(f"[newspapers] {source}: {count} KPK-relevant articles")
            except Exception as e:
                print(f"[newspapers] {source} error: {e}")

    articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    print(f"[newspapers] Total: {len(articles)} articles")
    return articles if articles else _mock_articles()


def _is_kpk_relevant(text):
    has_kpk = any(kw in text for kw in KPK_KEYWORDS)
    if not has_kpk:
        return False
    has_other_only = (
        any(p in text for p in OTHER_PROVINCES)
        and not any(kw in text for kw in KPK_KEYWORDS[:10])
    )
    return not has_other_only


def _normalize(entry, source, lang="en"):
    published = entry.get("published", "")
    try:
        from email.utils import parsedate_to_datetime
        published = parsedate_to_datetime(published).isoformat()
    except Exception:
        published = datetime.utcnow().isoformat()

    return {
        "title": _clean(entry.get("title", "")),
        "description": _clean(entry.get("summary", ""))[:300],
        "url": entry.get("link", ""),
        "source": source,
        "published_at": published,
        "image": _extract_image(entry),
        "lang": lang,
        "module": "newspapers",
    }


def _clean(text):
    """Strip HTML tags and extra whitespace."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_image(entry):
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    if hasattr(entry, "media_content") and entry.media_content:
        return entry.media_content[0].get("url", "")
    if hasattr(entry, "enclosures") and entry.enclosures:
        return entry.enclosures[0].get("href", "")
    # Try to find image in content
    content = entry.get("summary", "")
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
    return match.group(1) if match else ""


def _mock_articles():
    now = datetime.utcnow().isoformat()
    return [
        {"title": "KPK Assembly Passes Budget Bill", "description": "Khyber Pakhtunkhwa assembly passed the annual budget.", "url": "#", "source": "Dawn", "published_at": now, "image": "", "lang": "en", "module": "newspapers"},
        {"title": "Peshawar BRT Extension Confirmed", "description": "Officials confirmed plans to extend the BRT network.", "url": "#", "source": "Geo News", "published_at": now, "image": "", "lang": "en", "module": "newspapers"},
    ]
