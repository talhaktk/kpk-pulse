import os
import requests
from dotenv import load_dotenv

load_dotenv()

ENGAGEMENT_THRESHOLD = 100


def _get_bots():
    """
    Parse all bots from environment.

    Supports two formats in .env:

    FORMAT A — One bot, multiple chat IDs:
        TELEGRAM_TOKEN=tokenA
        TELEGRAM_CHAT_IDS=111,222,333

    FORMAT B — Multiple bots (each with their own chat IDs):
        TELEGRAM_BOT_1=tokenA::111,222
        TELEGRAM_BOT_2=tokenB::333,444
        TELEGRAM_BOT_3=tokenC::555

    Both formats work together simultaneously.
    Returns a list of (token, chat_id) tuples.
    """
    pairs = []

    # Format A — single token + chat IDs
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS", "").strip()
    if token and "your_telegram" not in token and chat_ids_raw:
        for cid in chat_ids_raw.split(","):
            cid = cid.strip()
            if cid and "your_personal" not in cid:
                pairs.append((token, cid))

    # Format B — TELEGRAM_BOT_1, TELEGRAM_BOT_2, ... (up to 20)
    for i in range(1, 21):
        entry = os.getenv(f"TELEGRAM_BOT_{i}", "").strip()
        if not entry:
            continue
        # expected format: token::chatid1,chatid2
        if "::" not in entry:
            print(f"[telegram_alert] TELEGRAM_BOT_{i} must be in format token::chatid1,chatid2")
            continue
        bot_token, chat_part = entry.split("::", 1)
        bot_token = bot_token.strip()
        for cid in chat_part.split(","):
            cid = cid.strip()
            if bot_token and cid:
                pairs.append((bot_token, cid))

    return pairs


def send_breaking_news(title, description, url=""):
    message = f"🚨 *BREAKING NEWS*\n\n*{title}*\n\n{description}"
    if url and url != "#":
        message += f"\n\n[Read more]({url})"
    return _broadcast(message)


def send_alert(article, engagement_score=0):
    if engagement_score < ENGAGEMENT_THRESHOLD:
        return False
    return _broadcast(_format_message(article))


def send_to_specific(token, chat_id, message):
    """Send to one specific bot + chat ID combination."""
    return _send_one(token, chat_id, message)


def _broadcast(message):
    """Send message via every configured bot to every configured chat ID."""
    bots = _get_bots()
    if not bots:
        print("[telegram_alert] No bots configured. Set TELEGRAM_TOKEN + TELEGRAM_CHAT_IDS or TELEGRAM_BOT_1 etc. in .env")
        return False
    results = [_send_one(token, cid, message) for token, cid in bots]
    return any(results)


def _send_one(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        print(f"[telegram_alert] Sent via bot ...{token[-6:]} to chat {chat_id}")
        return True
    except Exception as e:
        print(f"[telegram_alert] Error (bot ...{token[-6:]}, chat {chat_id}): {e}")
        return False


def _format_message(article):
    title = article.get("title", "")
    source = article.get("source", "")
    url = article.get("url", "")
    description = article.get("description", "")[:200]
    msg = f"📰 *KPK Pulse Alert*\n\n*{title}*\n_{source}_\n\n{description}"
    if url and url != "#":
        msg += f"\n\n[Read more]({url})"
    return msg
