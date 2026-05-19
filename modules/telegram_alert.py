import os
import requests
from dotenv import load_dotenv

load_dotenv()


def _token():
    return os.getenv("TELEGRAM_TOKEN", "").strip()


def _chat_ids():
    raw = os.getenv("TELEGRAM_CHAT_IDS", "").strip()
    ids = [c.strip() for c in raw.split(",") if c.strip() and c.strip().lstrip("-").isdigit()]
    return ids


def send_breaking_news(title, description, url=""):
    msg = f"🚨 *BREAKING — KPK Pulse*\n\n*{_esc(title)}*\n\n{_esc(description)}"
    if url and url.startswith("http"):
        msg += f"\n\n[Read more]({url})"
    return _broadcast(msg)


def send_alert(article, engagement_score=0):
    if engagement_score < 100:
        return False
    title  = article.get("title", "")
    source = article.get("source", "")
    desc   = article.get("description", "")[:200]
    url    = article.get("url", "")
    msg    = f"📰 *KPK Pulse Alert*\n\n*{_esc(title)}*\n_{_esc(source)}_\n\n{_esc(desc)}"
    if url and url.startswith("http"):
        msg += f"\n\n[Read more]({url})"
    return _broadcast(msg)


def _broadcast(message):
    token = _token()
    if not token:
        print("[telegram] TELEGRAM_TOKEN not set")
        return False

    chat_ids = _chat_ids()
    if not chat_ids:
        print("[telegram] TELEGRAM_CHAT_IDS not set or invalid — must be numeric IDs like: 6001278334")
        return False

    success = False
    for cid in chat_ids:
        ok = _send_one(token, cid, message)
        if ok:
            success = True
    return success


def _send_one(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(
            url,
            json={
                "chat_id":    chat_id,
                "text":       message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        data = r.json()
        if data.get("ok"):
            print(f"[telegram] ✓ Sent to {chat_id}")
            return True
        else:
            print(f"[telegram] ✗ Failed to {chat_id}: {data.get('description')}")
            return False
    except Exception as e:
        print(f"[telegram] ✗ Exception sending to {chat_id}: {e}")
        return False


def _esc(text):
    """Escape Markdown special chars."""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


def get_debug_info():
    """Return current config status for the /api/telegram/debug endpoint."""
    token    = _token()
    chat_ids = _chat_ids()
    return {
        "token_set":     bool(token),
        "token_preview": f"...{token[-8:]}" if token else "NOT SET",
        "chat_ids":      chat_ids,
        "chat_ids_raw":  os.getenv("TELEGRAM_CHAT_IDS", "NOT SET"),
        "ready":         bool(token and chat_ids),
    }
