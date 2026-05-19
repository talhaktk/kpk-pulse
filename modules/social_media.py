"""
Social Media module — Twitter/X, Facebook, Instagram, Reddit.
Uses RSSHub (free public bridge) which converts all major platforms to RSS.
No API keys required.
"""
import feedparser
import re
from datetime import datetime

KPK_KEYWORDS = [
    "kpk", "khyber pakhtunkhwa", "peshawar", "nowshera", "mardan",
    "swat", "abbottabad", "khyber", "pdma", "waziristan", "pti kpk",
    "cm kpk", "kp government", "ispr", "bajaur", "chitral", "dir",
    "kohat", "bannu", "buner", "shangla", "dera ismail khan",
]

RSSHUB_INSTANCES = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
    "https://hub.slarba.com",
]

# ── Twitter/X Accounts ────────────────────────────────────────────────────────
TWITTER_ACCOUNTS = [
    # KPK Government
    ("CMKPKOfficial",   True),   # (username, is_kpk_specific — skip keyword filter)
    ("KPPolice",        True),
    ("PDMAKPK",         True),
    ("ESEDKPKOfficial", True),
    ("KPITBoard",       True),
    ("OfficialDGISPR",  True),
    # KPK Media
    ("KhyberNews",      True),
    ("AVTKhyber",       True),
    ("MashriqNews",     True),
    # Politicians
    ("PTIofficial",     False),
    ("AliAminKhan",     False),
    ("Asad_Umar",       False),
    ("ImranKhanPTI",    False),
    ("ShehryarAfridi",  True),
]

# ── Facebook Pages ────────────────────────────────────────────────────────────
# RSSHub route: /facebook/page/{page_name or ID}
FACEBOOK_PAGES = [
    ("KhyberNews",          True),
    ("AVTKhyber",           True),
    ("GeoNewsUrdu",         False),
    ("arynewsofficial",     False),
    ("insaf.pk",            False),    # PTI
    ("CMKPKOfficial",       True),
    ("pdmakpk",             True),
    ("KPKPoliceOfficial",   True),
    ("mashriqtv",           True),
    ("DunyaNews",           False),
]

# ── Instagram Accounts ────────────────────────────────────────────────────────
# RSSHub route: /picnob/user/{username}  (picnob is a public Instagram viewer)
INSTAGRAM_ACCOUNTS = [
    ("khybernewstv",    True),
    ("arynewstv",       False),
    ("geonews",         False),
    ("ptv_news",        False),
]

# ── Reddit Feeds ──────────────────────────────────────────────────────────────
REDDIT_FEEDS = {
    "r/pakistan (KPK)":       "https://www.reddit.com/r/pakistan/search.rss?q=KPK+OR+Peshawar+OR+Waziristan&sort=new&limit=20",
    "r/PakistanPolitics":     "https://www.reddit.com/r/PakistanPolitics/.rss?limit=20",
}

# ── Nitter Fallback ───────────────────────────────────────────────────────────
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.cz",
]


def fetch_social_posts():
    posts = []

    # Priority 1: RSSHub (Twitter + Facebook + Instagram)
    posts.extend(_fetch_twitter_rsshub())
    posts.extend(_fetch_facebook_rsshub())
    posts.extend(_fetch_instagram_rsshub())

    # Priority 2: Reddit (always reliable, no auth)
    posts.extend(_fetch_reddit())

    # Priority 3: Nitter fallback for Twitter if RSSHub failed
    if sum(1 for p in posts if p.get("platform") == "twitter") < 3:
        posts.extend(_fetch_nitter())

    # Deduplicate + sort
    seen, unique = set(), []
    for p in posts:
        key = (p.get("title", "")[:60]).lower()
        if key not in seen and key:
            seen.add(key); unique.append(p)

    unique.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    print(f"[social_media] Total: {len(unique)} posts")
    return unique if unique else _mock_posts()


# ── Fetchers ──────────────────────────────────────────────────────────────────

def _fetch_twitter_rsshub():
    posts = []
    for instance in RSSHUB_INSTANCES:
        instance_posts = []
        try:
            for username, is_kpk in TWITTER_ACCOUNTS:
                feed = feedparser.parse(f"{instance}/twitter/user/{username}")
                if not feed.entries:
                    continue
                for entry in feed.entries[:6]:
                    text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                    if is_kpk or any(kw in text for kw in KPK_KEYWORDS):
                        instance_posts.append(_make_post(entry, f"@{username}", "twitter"))
            if instance_posts:
                print(f"[social_media] Twitter via {instance}: {len(instance_posts)} posts")
                return instance_posts
        except Exception as e:
            print(f"[social_media] RSSHub Twitter {instance}: {e}")
    return posts


def _fetch_facebook_rsshub():
    posts = []
    for instance in RSSHUB_INSTANCES:
        instance_posts = []
        try:
            for page, is_kpk in FACEBOOK_PAGES:
                feed = feedparser.parse(f"{instance}/facebook/page/{page}")
                if not feed.entries:
                    continue
                for entry in feed.entries[:5]:
                    text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                    if is_kpk or any(kw in text for kw in KPK_KEYWORDS):
                        instance_posts.append(_make_post(entry, f"fb/{page}", "facebook"))
            if instance_posts:
                print(f"[social_media] Facebook via {instance}: {len(instance_posts)} posts")
                return instance_posts
        except Exception as e:
            print(f"[social_media] RSSHub Facebook {instance}: {e}")
        break  # try only first instance for FB to save time
    return posts


def _fetch_instagram_rsshub():
    posts = []
    for instance in RSSHUB_INSTANCES:
        instance_posts = []
        try:
            for username, is_kpk in INSTAGRAM_ACCOUNTS:
                feed = feedparser.parse(f"{instance}/picnob/user/{username}")
                if not feed.entries:
                    continue
                for entry in feed.entries[:4]:
                    text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                    if is_kpk or any(kw in text for kw in KPK_KEYWORDS):
                        instance_posts.append(_make_post(entry, f"@{username}", "instagram"))
            if instance_posts:
                print(f"[social_media] Instagram via {instance}: {len(instance_posts)} posts")
                return instance_posts
        except Exception as e:
            print(f"[social_media] RSSHub Instagram {instance}: {e}")
        break
    return posts


def _fetch_reddit():
    posts = []
    headers = {"User-Agent": "KPKPulse/1.0 (media intelligence dashboard)"}
    for source, url in REDDIT_FEEDS.items():
        try:
            feed = feedparser.parse(url, request_headers=headers)
            count = 0
            for entry in feed.entries[:15]:
                text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                if any(kw in text for kw in KPK_KEYWORDS):
                    posts.append(_make_post(entry, source, "reddit"))
                    count += 1
            if count:
                print(f"[social_media] Reddit {source}: {count} posts")
        except Exception as e:
            print(f"[social_media] Reddit {source}: {e}")
    return posts


def _fetch_nitter():
    posts = []
    for instance in NITTER_INSTANCES:
        instance_posts = []
        try:
            for username, is_kpk in TWITTER_ACCOUNTS[:8]:
                feed = feedparser.parse(f"{instance}/{username}/rss")
                if not feed.entries:
                    continue
                for entry in feed.entries[:4]:
                    text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                    if is_kpk or any(kw in text for kw in KPK_KEYWORDS):
                        instance_posts.append(_make_post(entry, f"@{username}", "twitter"))
            if instance_posts:
                print(f"[social_media] Nitter {instance}: {len(instance_posts)} posts")
                return instance_posts
        except Exception as e:
            print(f"[social_media] Nitter {instance}: {e}")
    return posts


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_post(entry, source, platform):
    return {
        "title": _clean(entry.get("title", ""))[:250],
        "description": _clean(entry.get("summary", ""))[:350],
        "url": entry.get("link", ""),
        "source": source,
        "published_at": _parse_date(entry.get("published", "")),
        "image": _extract_media(entry),
        "platform": platform,
        "module": "social_media",
    }


def _parse_date(date_str):
    if not date_str:
        return datetime.utcnow().isoformat()
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str).isoformat()
    except Exception:
        return datetime.utcnow().isoformat()


def _clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _extract_media(entry):
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    if hasattr(entry, "enclosures") and entry.enclosures:
        return entry.enclosures[0].get("href", "")
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.get("summary", ""))
    return match.group(1) if match else ""


def _mock_posts():
    now = datetime.utcnow().isoformat()
    return [
        {"title": "@CMKPKOfficial: 500 new schools announced across KPK", "description": "CM KPK announced a major education initiative targeting underserved districts.", "url": "#", "source": "@CMKPKOfficial", "published_at": now, "image": "", "platform": "twitter", "module": "social_media"},
        {"title": "@KPPolice: Suspect arrested in Peshawar operation", "description": "KPK Police conducted a successful counter-terrorism operation in Peshawar.", "url": "#", "source": "@KPPolice", "published_at": now, "image": "", "platform": "twitter", "module": "social_media"},
        {"title": "r/pakistan: KPK flood situation update", "description": "Latest updates from PDMA KPK on rain and flood situation.", "url": "#", "source": "r/pakistan", "published_at": now, "image": "", "platform": "reddit", "module": "social_media"},
    ]
