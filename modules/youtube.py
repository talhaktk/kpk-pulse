import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

CHANNEL_IDS = {
    "Khyber News": "UCiQZ_saslhxeyURqcxrkGkQ",
    "AVT Khyber": "UCwQF2yhcgjZGDp7gx8gV0dQ",
    "Geo News": "UCnlMBzk7XDdEFBfOzPaqxkA",
}


def fetch_videos(max_results=6):
    if not API_KEY or API_KEY == "your_youtube_api_key_here":
        return _mock_videos()

    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=API_KEY)
        videos = []
        for channel_name, channel_id in CHANNEL_IDS.items():
            req = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                maxResults=max_results,
                order="date",
                type="video",
            )
            resp = req.execute()
            for item in resp.get("items", []):
                snippet = item["snippet"]
                video_id = item["id"]["videoId"]
                videos.append({
                    "title": snippet.get("title", ""),
                    "channel": channel_name,
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "description": snippet.get("description", "")[:200],
                    "module": "youtube",
                })
        return videos
    except Exception as e:
        print(f"[youtube] Error: {e}")
        return _mock_videos()


def _mock_videos():
    now = datetime.utcnow().isoformat()
    return [
        {
            "title": "KPK Latest News | Khyber News Live",
            "channel": "Khyber News",
            "video_id": "dQw4w9WgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "thumbnail": "",
            "published_at": now,
            "description": "Latest breaking news from Khyber Pakhtunkhwa.",
            "module": "youtube",
        },
        {
            "title": "AVT Khyber Morning Show",
            "channel": "AVT Khyber",
            "video_id": "dQw4w9WgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "thumbnail": "",
            "published_at": now,
            "description": "Morning program on AVT Khyber covering provincial affairs.",
            "module": "youtube",
        },
        {
            "title": "Geo News: Pakistan Headlines",
            "channel": "Geo News",
            "video_id": "dQw4w9WgXcQ",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "thumbnail": "",
            "published_at": now,
            "description": "Top headlines including KPK updates.",
            "module": "youtube",
        },
    ]
