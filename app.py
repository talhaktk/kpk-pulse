import os
import json
import threading
import time
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "kpk-pulse-dev-key")

# In-memory cache so we don't hammer APIs on every request
_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 900  # 15 minutes


def cached(key, ttl=CACHE_TTL):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            with _cache_lock:
                entry = _cache.get(key)
                if entry and (time.time() - entry["ts"]) < ttl:
                    return entry["data"]
            result = fn(*args, **kwargs)
            with _cache_lock:
                _cache[key] = {"data": result, "ts": time.time()}
            return result
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


@cached("news", 900)
def _get_news():
    from modules.google_news import fetch_news
    return fetch_news()


@cached("trends", 1800)
def _get_trends():
    from modules.google_trends import fetch_trends
    return fetch_trends()


@cached("youtube", 900)
def _get_youtube():
    from modules.youtube import fetch_videos
    return fetch_videos()


@cached("govt", 900)
def _get_govt():
    from modules.kpk_govt import fetch_govt_news
    return fetch_govt_news()


@cached("newspapers", 900)
def _get_newspapers():
    from modules.newspapers import fetch_articles
    return fetch_articles()


@cached("social", 600)
def _get_social():
    from modules.social_media import fetch_social_posts
    return fetch_social_posts()


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/news")
def api_news():
    keyword = request.args.get("q", "")
    if keyword:
        from modules.google_news import fetch_news
        data = fetch_news(keyword=keyword)
    else:
        data = _get_news()
    return jsonify({"status": "ok", "data": data, "count": len(data)})


@app.route("/api/trends")
def api_trends():
    return jsonify({"status": "ok", "data": _get_trends()})


@app.route("/api/youtube")
def api_youtube():
    return jsonify({"status": "ok", "data": _get_youtube()})


@app.route("/api/newspapers")
def api_newspapers():
    return jsonify({"status": "ok", "data": _get_newspapers()})


@app.route("/api/social")
def api_social():
    return jsonify({"status": "ok", "data": _get_social()})


@app.route("/api/govt")
def api_govt():
    return jsonify({"status": "ok", "data": _get_govt()})


@app.route("/api/all")
def api_all():
    news = _get_news()
    newspapers = _get_newspapers()
    social = _get_social()
    govt = _get_govt()
    combined = news + newspapers + social + govt
    combined.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    # Deduplicate by title
    seen, unique = set(), []
    for a in combined:
        key = (a.get("title", "")[:60]).lower()
        if key not in seen:
            seen.add(key); unique.append(a)
    return jsonify({"status": "ok", "data": unique, "count": len(unique)})


@app.route("/api/breaking")
def api_breaking():
    all_articles = _get_news() + _get_newspapers()
    breaking = [a for a in all_articles if _is_breaking(a.get("title", ""))]
    return jsonify({"status": "ok", "data": breaking[:5]})


@app.route("/api/send_alert", methods=["POST"])
def api_send_alert():
    data = request.get_json(force=True)
    article = data.get("article", {})
    from modules.telegram_alert import send_breaking_news
    ok = send_breaking_news(
        article.get("title", ""),
        article.get("description", ""),
        article.get("url", ""),
    )
    return jsonify({"status": "ok" if ok else "skipped"})


@app.route("/api/send_digest", methods=["POST"])
def api_send_digest():
    period = request.args.get("period", "morning")
    articles = _get_news() + _get_newspapers()
    from modules.email_digest import send_morning_digest, send_evening_summary
    if period == "evening":
        ok = send_evening_summary(articles)
    else:
        ok = send_morning_digest(articles)
    return jsonify({"status": "ok" if ok else "skipped"})


@app.route("/api/telegram/chat_ids")
def api_telegram_chat_ids():
    """Call this after messaging your bot to discover your chat ID."""
    token = os.getenv("TELEGRAM_TOKEN")
    if not token or "your_telegram" in token:
        return jsonify({"error": "TELEGRAM_TOKEN not set"}), 400
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10)
        updates = resp.json().get("result", [])
        chats = {}
        for u in updates:
            msg = u.get("message") or u.get("channel_post") or {}
            chat = msg.get("chat", {})
            if chat:
                chats[chat["id"]] = {
                    "id": chat["id"],
                    "type": chat.get("type"),
                    "name": chat.get("title") or chat.get("username") or chat.get("first_name", ""),
                }
        return jsonify({"status": "ok", "chats": list(chats.values())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/telegram/test", methods=["POST"])
def api_telegram_test():
    """Send a test message to all configured chat IDs."""
    from modules.telegram_alert import send_breaking_news
    ok = send_breaking_news("KPK Pulse Test", "Your Telegram alerts are working correctly!", "")
    return jsonify({"status": "ok" if ok else "failed — check TELEGRAM_CHAT_IDS in .env"})


@app.route("/api/email/test", methods=["POST"])
def api_email_test():
    """Send a test digest to all configured email recipients."""
    articles = _get_news() + _get_newspapers()
    from modules.email_digest import send_morning_digest
    ok = send_morning_digest(articles[:5])
    return jsonify({"status": "ok" if ok else "failed — check EMAIL_* vars in .env"})


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    keys = request.get_json(force=True).get("modules", list(_cache.keys()))
    with _cache_lock:
        for k in keys:
            _cache.pop(k, None)
    return jsonify({"status": "ok", "cleared": keys})


@app.route("/api/status")
def api_status():
    has_news_key = bool(os.getenv("NEWS_API_KEY") and os.getenv("NEWS_API_KEY") != "your_newsapi_key_here")
    has_yt_key = bool(os.getenv("YOUTUBE_API_KEY") and os.getenv("YOUTUBE_API_KEY") != "your_youtube_api_key_here")
    has_tg = bool(os.getenv("TELEGRAM_TOKEN") and os.getenv("TELEGRAM_TOKEN") != "your_telegram_bot_token_here")
    has_email = bool(os.getenv("EMAIL_ADDRESS") and os.getenv("EMAIL_ADDRESS") != "your_gmail@gmail.com")
    return jsonify({
        "status": "ok",
        "api_keys": {
            "news_api": has_news_key,
            "youtube": has_yt_key,
            "telegram": has_tg,
            "email": has_email,
        },
        "cache": {k: bool(v) for k, v in _cache.items()},
        "server_time": datetime.utcnow().isoformat(),
    })


# ── Helpers ──────────────────────────────────────────────────────────────────

BREAKING_WORDS = [
    "breaking", "urgent", "alert", "exclusive", "just in",
    "developing", "emergency", "explosion", "attack", "killed",
    "arrested", "earthquake", "flood",
]


def _is_breaking(title):
    lower = title.lower()
    return any(w in lower for w in BREAKING_WORDS)


# ── Scheduler (background thread) ────────────────────────────────────────────

def _scheduler_loop():
    import schedule

    def refresh_all():
        with _cache_lock:
            _cache.clear()
        print(f"[scheduler] Cache cleared at {datetime.utcnow().isoformat()}")

    def morning_digest():
        articles = _get_news() + _get_newspapers()
        from modules.email_digest import send_morning_digest
        send_morning_digest(articles)

    def evening_digest():
        articles = _get_news() + _get_newspapers()
        from modules.email_digest import send_evening_summary
        send_evening_summary(articles)

    schedule.every(15).minutes.do(refresh_all)
    schedule.every().day.at("08:00").do(morning_digest)
    schedule.every().day.at("20:00").do(evening_digest)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
