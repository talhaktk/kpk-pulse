import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ENGAGEMENT_THRESHOLD = 100


def send_alert(article, engagement_score=0):
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your_telegram_bot_token_here":
        print(f"[telegram_alert] Mock alert: {article.get('title', '')}")
        return False

    if engagement_score < ENGAGEMENT_THRESHOLD:
        return False

    message = _format_message(article)
    return _send(message)


def send_breaking_news(title, description, url=""):
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your_telegram_bot_token_here":
        print(f"[telegram_alert] Mock breaking news: {title}")
        return False
    message = f"🚨 *BREAKING NEWS*\n\n*{title}*\n\n{description}"
    if url and url != "#":
        message += f"\n\n[Read more]({url})"
    return _send(message)


def _format_message(article):
    title = article.get("title", "")
    source = article.get("source", "")
    url = article.get("url", "")
    description = article.get("description", "")[:200]
    msg = f"📰 *KPK Pulse Alert*\n\n*{title}*\n_{source}_\n\n{description}"
    if url and url != "#":
        msg += f"\n\n[Read more]({url})"
    return msg


def _send(message):
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[telegram_alert] Send error: {e}")
        return False
