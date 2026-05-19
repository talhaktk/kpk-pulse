from datetime import datetime

def fetch_trends():
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=300)
        trending = pytrends.trending_searches(pn="pakistan")
        topics = trending[0].tolist()[:10]
        return _normalize(topics)
    except Exception as e:
        print(f"[google_trends] Error: {e}")
        return _mock_trends()


def _normalize(topics):
    results = []
    for i, topic in enumerate(topics, 1):
        results.append({
            "rank": i,
            "title": topic,
            "url": f"https://trends.google.com/trends/explore?q={topic.replace(' ', '+')}&geo=PK",
            "published_at": datetime.utcnow().isoformat(),
            "module": "google_trends",
        })
    return results


def _mock_trends():
    topics = [
        "Peshawar Weather", "KPK Budget 2025", "Swat Tourism",
        "Mardan Education", "KPK Police", "PTI Rally Peshawar",
        "Nowshera Flood", "Abbottabad Hospital", "KPK Cricket",
        "Khyber Pass",
    ]
    return _normalize(topics)
