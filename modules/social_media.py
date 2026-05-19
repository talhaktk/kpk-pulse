"""
Social Media — official KPK government, politician & media accounts.
Uses ThreadPoolExecutor so all feeds are fetched in parallel.
Hard 5-second timeout per request — never hangs on Vercel.
"""
import feedparser
import re
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

REQUEST_TIMEOUT = 5   # seconds per feed request
PARALLEL_WORKERS = 8  # fetch up to 8 feeds simultaneously
MAX_AGE_HOURS = 24

KPK_INCLUDE = [
    "kpk", "khyber pakhtunkhwa", "peshawar", "nowshera", "mardan",
    "swat", "abbottabad", "khyber", "pdma", "waziristan", "cm kpk",
    "kpk government", "kpk police", "chitral", "dir", "kohat",
    "bannu", "buner", "dera ismail khan", "bajaur", "mohmand",
    "kurram", "kpitb", "ispr", "north waziristan", "south waziristan",
    "ali amin", "shehryar", "kp government",
]
OTHER_PROVINCE = [
    "karachi", "sindh", "lahore", "punjab", "balochistan",
    "quetta", "multan", "faisalabad", "hyderabad", "gwadar",
]

RSSHUB_BASES = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
]
NITTER_BASES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.cz",
]

# (account, platform, always_include)
ACCOUNTS = [
    # KPK Government — all content relevant
    ("CMKPKOfficial",   "twitter",   True),
    ("KPPolice",        "twitter",   True),
    ("PDMAKPK",         "twitter",   True),
    ("ESEDKPKOfficial", "twitter",   True),
    ("KPITBoard",       "twitter",   True),
    ("OfficialDGISPR",  "twitter",   True),
    # Top KPK Politicians
    ("AliAminKhan",     "twitter",   False),
    ("ShehryarAfridi",  "twitter",   False),
    ("PTIofficial",     "twitter",   False),
    ("ImranKhanPTI",    "twitter",   False),
    ("OmarAyubKhan",    "twitter",   False),
    # KPK Media
    ("KhyberNews",      "twitter",   True),
    ("AVTKhyber",       "twitter",   True),
    ("MashriqNews",     "twitter",   True),
    # Facebook official pages
    ("CMKPKOfficial",   "facebook",  True),
    ("KPKPoliceOfficial","facebook", True),
    ("KhyberNews",      "facebook",  True),
    ("AVTKhyberOfficial","facebook", True),
    ("insaf.pk",        "facebook",  False),
]


def fetch_social_posts():
    posts = []

    # Build all tasks: (url, account, platform, always_include)
    tasks = []
    for base in RSSHUB_BASES[:1]:          # try first RSSHub instance
        for acc, plat, always in ACCOUNTS:
            if plat == "twitter":
                tasks.append((f"{base}/twitter/user/{acc}", acc, plat, always))
            elif plat == "facebook":
                tasks.append((f"{base}/facebook/page/{acc}", acc, plat, always))

    # Fetch all in parallel
    posts = _parallel_fetch(tasks)

    # If Twitter yielded nothing, try Nitter in parallel
    if not any(p["platform"] == "twitter" for p in posts):
        nitter_tasks = []
        for base in NITTER_BASES:
            for acc, plat, always in ACCOUNTS:
                if plat == "twitter":
                    nitter_tasks.append((f"{base}/{acc}/rss", acc, plat, always))
        posts += _parallel_fetch(nitter_tasks)

    # Deduplicate + age filter + sort
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    seen, unique = set(), []
    for p in sorted(posts, key=lambda x: x.get("published_at", ""), reverse=True):
        key = (p.get("title", "")[:70]).lower()
        if not key or key in seen:
            continue
        # Age filter
        try:
            dt = datetime.fromisoformat(p["published_at"].replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt < cutoff:
                continue
        except Exception:
            pass
        # URL must be real
        if not p.get("url", "").startswith("http"):
            continue
        seen.add(key)
        unique.append(p)

    print(f"[social_media] {len(unique)} posts (parallel fetch)")
    return unique   # return empty list — no fake fallback


def _parallel_fetch(tasks):
    results = []
    with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as ex:
        futures = {ex.submit(_fetch_one, url, acc, plat, always): (acc, plat) for url, acc, plat, always in tasks}
        for future in as_completed(futures, timeout=REQUEST_TIMEOUT + 2):
            try:
                items = future.result(timeout=1)
                results.extend(items)
            except Exception:
                pass
    return results


def _fetch_one(url, account, platform, always_include):
    try:
        # feedparser uses urllib internally; wrap in requests for timeout control
        import requests as req
        resp = req.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": "KPKPulse/1.0"})
        if resp.status_code != 200:
            return []
        feed = feedparser.parse(resp.text)
        posts = []
        for entry in feed.entries[:6]:
            text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
            if always_include or _is_kpk(text):
                url_link = entry.get("link", "")
                if not url_link.startswith("http"):
                    continue
                posts.append({
                    "title":        _clean(entry.get("title", ""))[:250],
                    "description":  _clean(entry.get("summary", ""))[:300],
                    "url":          url_link,
                    "source":       f"{'𝕏' if platform == 'twitter' else '📘' if platform == 'facebook' else '📸'} @{account}",
                    "published_at": _date(entry),
                    "image":        _img(entry),
                    "platform":     platform,
                    "module":       "social_media",
                })
        return posts
    except Exception as e:
        return []


def _is_kpk(text):
    if not any(kw in text for kw in KPK_INCLUDE):
        return False
    return not (any(p in text for p in OTHER_PROVINCE) and not any(k in text for k in KPK_INCLUDE[:8]))


def _date(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            import calendar
            ts = calendar.timegm(entry.published_parsed)
            return datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    s = getattr(entry, "published", "") or ""
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(s).isoformat()
    except Exception:
        return datetime.utcnow().isoformat()


def _clean(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _img(entry):
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    if hasattr(entry, "enclosures") and entry.enclosures:
        return entry.enclosures[0].get("href", "")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.get("summary", ""))
    return m.group(1) if m else ""
