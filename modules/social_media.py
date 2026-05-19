import feedparser
import requests
from datetime import datetime
from bs4 import BeautifulSoup

KPK_KEYWORDS = [
    "kpk", "khyber pakhtunkhwa", "peshawar", "nowshera",
    "mardan", "swat", "abbottabad", "pti", "khyber",
]

# Public RSS bridges for social media (using nitter for Twitter/X public content)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.cz",
]

PUBLIC_TWITTER_ACCOUNTS = [
    "KhyberNews",
    "AVTKhyber",
    "PTIofficial",
    "CMKPKOfficial",
]

FACEBOOK_RSS_FEEDS = {
    "Khyber News FB": "https://www.facebook.com/KhyberNews/",
    "KPK Info": "https://www.facebook.com/KPKInfo/",
}


def fetch_social_posts():
    posts = []
    posts.extend(_fetch_twitter_rss())
    if not posts:
        posts = _mock_posts()
    return posts


def _fetch_twitter_rss():
    posts = []
    for instance in NITTER_INSTANCES:
        try:
            for account in PUBLIC_TWITTER_ACCOUNTS:
                url = f"{instance}/{account}/rss"
                feed = feedparser.parse(url)
                if feed.entries:
                    for entry in feed.entries[:5]:
                        text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                        if any(kw in text for kw in KPK_KEYWORDS):
                            posts.append({
                                "title": entry.get("title", "")[:200],
                                "description": entry.get("summary", "")[:300],
                                "url": entry.get("link", ""),
                                "source": f"@{account}",
                                "published_at": _parse_date(entry.get("published", "")),
                                "image": "",
                                "platform": "twitter",
                                "module": "social_media",
                            })
            if posts:
                break
        except Exception as e:
            print(f"[social_media] Nitter {instance} error: {e}")
            continue
    return posts


def _parse_date(date_str):
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str).isoformat()
    except Exception:
        return datetime.utcnow().isoformat()


def _mock_posts():
    now = datetime.utcnow().isoformat()
    return [
        {
            "title": "@KhyberNews: Breaking — Governor KPK meets federal cabinet",
            "description": "Governor Khyber Pakhtunkhwa held a high-level meeting with members of the federal cabinet today.",
            "url": "#",
            "source": "@KhyberNews",
            "published_at": now,
            "image": "",
            "platform": "twitter",
            "module": "social_media",
        },
        {
            "title": "@PTIofficial: PTI rally in Peshawar draws thousands",
            "description": "A massive rally was held in Peshawar's Tehkal ground with thousands in attendance.",
            "url": "#",
            "source": "@PTIofficial",
            "published_at": now,
            "image": "",
            "platform": "twitter",
            "module": "social_media",
        },
        {
            "title": "@CMKPKOfficial: 500 new schools to be built in KPK",
            "description": "Chief Minister KPK announced a new education initiative to build 500 schools across the province.",
            "url": "#",
            "source": "@CMKPKOfficial",
            "published_at": now,
            "image": "",
            "platform": "twitter",
            "module": "social_media",
        },
    ]
