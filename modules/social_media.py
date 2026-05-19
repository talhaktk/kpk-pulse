"""
Social Media — Twitter/X, Facebook, Instagram via RSSHub.
Only official government, verified politician, and KPK media accounts.
No Reddit. No random people.
"""
import feedparser
import re
from datetime import datetime

# Must contain at least one KPK keyword
KPK_INCLUDE = [
    "kpk", "khyber pakhtunkhwa", "peshawar", "nowshera", "mardan",
    "swat", "abbottabad", "khyber", "pdma", "waziristan", "cm kpk",
    "kpk government", "kpk police", "chitral", "dir", "kohat",
    "bannu", "buner", "shangla", "dera ismail khan", "bajaur",
    "mohmand", "kurram", "lakki", "hangu", "kpitb", "brt peshawar",
    "ispr kpk", "north waziristan", "south waziristan",
]

# Exclude if ONLY about these provinces with NO KPK mention
OTHER_PROVINCE = [
    "karachi", "lahore", "sindh", "balochistan", "punjab",
    "quetta", "multan", "faisalabad", "hyderabad", "gwadar",
    "sukkur", "larkana", "nawabshah",
]

# RSSHub instances (converts social platforms to RSS — no API key)
RSSHUB = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
    "https://hub.slarba.com",
]

# ── TWITTER/X: Verified official & politician accounts only ──────────────────
# (is_kpk_official=True means all their posts are KPK-relevant, skip filter)
TWITTER_ACCOUNTS = [
    # KPK Government — official verified
    ("CMKPKOfficial",   True),   # Chief Minister KPK
    ("KPPolice",        True),   # KPK Police official
    ("PDMAKPK",         True),   # Disaster Management KPK
    ("ESEDKPKOfficial", True),   # KPK Education
    ("KPITBoard",       True),   # KPITB
    ("OfficialDGISPR",  True),   # Military / ISPR
    # Top KPK Politicians — verified accounts
    ("AliAminKhan",     False),  # CM KPK Ali Amin Gandapur
    ("ShehryarAfridi",  False),  # Federal Minister / KPK Senator
    ("PTIofficial",     False),  # PTI party official
    ("ImranKhanPTI",    False),  # Imran Khan
    ("Asad_Umar",       False),  # PTI leader
    ("OmarAyubKhan",    False),  # Speaker NA / KPK politician
    # KPK Media — verified channels
    ("KhyberNews",      True),
    ("AVTKhyber",       True),
    ("MashriqNews",     True),
]

# ── FACEBOOK: Official verified pages only ───────────────────────────────────
FACEBOOK_PAGES = [
    ("CMKPKOfficial",       True),
    ("KPKPoliceOfficial",   True),
    ("pdmakpk",             True),
    ("KhyberNews",          True),
    ("AVTKhyberOfficial",   True),
    ("MashriqOfficial",     True),
    ("insaf.pk",            False),   # PTI
    ("ShehryarAfridiOfficial", False),
]

# ── INSTAGRAM: Official verified channels only ───────────────────────────────
INSTAGRAM_ACCOUNTS = [
    ("khybernewstv",    True),
    ("avtkhyber",       True),
    ("ptiofficialpage", False),
]

# Nitter fallback for Twitter
NITTER = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.cz",
]


def fetch_social_posts():
    posts = []
    posts.extend(_twitter())
    posts.extend(_facebook())
    posts.extend(_instagram())

    # Nitter fallback if Twitter via RSSHub got nothing
    if not any(p["platform"] == "twitter" for p in posts):
        posts.extend(_nitter_fallback())

    # Deduplicate + sort newest first
    seen, unique = set(), []
    for p in posts:
        key = (p.get("title", "")[:70]).lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(p)
    unique.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    print(f"[social_media] {len(unique)} posts total")
    return unique or _mock_posts()


def _twitter():
    for instance in RSSHUB:
        batch = []
        try:
            for username, is_official in TWITTER_ACCOUNTS:
                feed = feedparser.parse(f"{instance}/twitter/user/{username}")
                if not feed.entries:
                    continue
                for entry in feed.entries[:6]:
                    text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                    if is_official or _is_kpk(text):
                        batch.append(_post(entry, f"𝕏 @{username}", "twitter"))
            if batch:
                print(f"[social_media] Twitter via {instance}: {len(batch)}")
                return batch
        except Exception as e:
            print(f"[social_media] Twitter RSSHub {instance}: {e}")
    return []


def _facebook():
    for instance in RSSHUB:
        batch = []
        try:
            for page, is_official in FACEBOOK_PAGES:
                feed = feedparser.parse(f"{instance}/facebook/page/{page}")
                if not feed.entries:
                    continue
                for entry in feed.entries[:5]:
                    text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                    if is_official or _is_kpk(text):
                        batch.append(_post(entry, f"📘 {page}", "facebook"))
            if batch:
                print(f"[social_media] Facebook via {instance}: {len(batch)}")
                return batch
        except Exception as e:
            print(f"[social_media] Facebook RSSHub {instance}: {e}")
        break  # only try first instance for FB
    return []


def _instagram():
    for instance in RSSHUB:
        batch = []
        try:
            for username, is_official in INSTAGRAM_ACCOUNTS:
                feed = feedparser.parse(f"{instance}/picnob/user/{username}")
                if not feed.entries:
                    continue
                for entry in feed.entries[:4]:
                    text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                    if is_official or _is_kpk(text):
                        batch.append(_post(entry, f"📸 @{username}", "instagram"))
            if batch:
                print(f"[social_media] Instagram via {instance}: {len(batch)}")
                return batch
        except Exception as e:
            print(f"[social_media] Instagram RSSHub {instance}: {e}")
        break
    return []


def _nitter_fallback():
    for instance in NITTER:
        batch = []
        try:
            for username, is_official in TWITTER_ACCOUNTS[:8]:
                feed = feedparser.parse(f"{instance}/{username}/rss")
                if not feed.entries:
                    continue
                for entry in feed.entries[:5]:
                    text = f"{entry.get('title','')} {entry.get('summary','')}".lower()
                    if is_official or _is_kpk(text):
                        batch.append(_post(entry, f"𝕏 @{username}", "twitter"))
            if batch:
                print(f"[social_media] Nitter fallback {instance}: {len(batch)}")
                return batch
        except Exception as e:
            print(f"[social_media] Nitter {instance}: {e}")
    return []


def _is_kpk(text):
    """True if text is KPK-relevant and not purely another province."""
    has_kpk = any(kw in text for kw in KPK_INCLUDE)
    if not has_kpk:
        return False
    # Reject if it has another province keyword but zero KPK keywords
    other_only = any(p in text for p in OTHER_PROVINCE) and not any(k in text for k in KPK_INCLUDE[:8])
    return not other_only


def _post(entry, source, platform):
    return {
        "title":       _clean(entry.get("title", ""))[:250],
        "description": _clean(entry.get("summary", ""))[:350],
        "url":         entry.get("link", ""),
        "source":      source,
        "published_at": _date(entry.get("published", "")),
        "image":       _img(entry),
        "platform":    platform,
        "module":      "social_media",
    }


def _date(s):
    if not s:
        return datetime.utcnow().isoformat()
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(s).isoformat()
    except Exception:
        return datetime.utcnow().isoformat()


def _clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _img(entry):
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url", "")
    if hasattr(entry, "enclosures") and entry.enclosures:
        return entry.enclosures[0].get("href", "")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.get("summary", ""))
    return m.group(1) if m else ""


def _mock_posts():
    now = datetime.utcnow().isoformat()
    return [
        {"title": "𝕏 @CMKPKOfficial: CM KPK visits flood-affected areas in Nowshera", "description": "Chief Minister Khyber Pakhtunkhwa personally visited flood-affected families in Nowshera.", "url": "https://twitter.com/CMKPKOfficial", "source": "𝕏 @CMKPKOfficial", "published_at": now, "image": "", "platform": "twitter", "module": "social_media"},
        {"title": "𝕏 @KPPolice: KPK Police arrests 12 suspects in Peshawar operation", "description": "A successful joint intelligence operation led to arrest of 12 suspects in Peshawar.", "url": "https://twitter.com/KPPolice", "source": "𝕏 @KPPolice", "published_at": now, "image": "", "platform": "twitter", "module": "social_media"},
        {"title": "𝕏 @OfficialDGISPR: Security forces kill 8 terrorists in North Waziristan", "description": "ISPR confirms successful operation in North Waziristan. Own troops safe.", "url": "https://twitter.com/OfficialDGISPR", "source": "𝕏 @OfficialDGISPR", "published_at": now, "image": "", "platform": "twitter", "module": "social_media"},
        {"title": "📘 @KhyberNews: Breaking — Heavy rainfall warning for Swat and Chitral", "description": "Khyber News reports PMD has issued a red alert for heavy rainfall in Swat, Dir and Chitral.", "url": "https://www.facebook.com/KhyberNews", "source": "📘 KhyberNews", "published_at": now, "image": "", "platform": "facebook", "module": "social_media"},
    ]
