import pickle
from pathlib import Path

TOKEN_FILE = Path(__file__).parent / "token.pickle"


def get_top_videos(limit: int = 10) -> list[dict]:
    """
    Fetch the channel's top videos by view count using the saved OAuth token.
    Returns a list of dicts with title, views, likes, video_id.
    Returns [] if no token exists yet.
    """
    if not TOKEN_FILE.exists():
        return []

    try:
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        youtube = build("youtube", "v3", credentials=creds)

        # Get upload playlist ID
        ch = youtube.channels().list(part="contentDetails", mine=True).execute()
        uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # Collect video IDs
        video_ids = []
        page_token = None
        while len(video_ids) < 50:
            pl = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_id,
                maxResults=50,
                pageToken=page_token,
            ).execute()
            video_ids += [i["contentDetails"]["videoId"] for i in pl["items"]]
            page_token = pl.get("nextPageToken")
            if not page_token:
                break

        if not video_ids:
            return []

        # Fetch stats in one call (max 50 IDs)
        stats = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids[:50]),
        ).execute()

        videos = []
        for v in stats["items"]:
            s = v.get("statistics", {})
            videos.append({
                "video_id": v["id"],
                "title": v["snippet"]["title"],
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
            })

        videos.sort(key=lambda x: x["views"], reverse=True)
        return videos[:limit]

    except Exception as e:
        print(f"  ⚠️  Analytics fetch failed: {e}")
        return []


def print_report():
    """Print a quick channel performance report to stdout."""
    videos = get_top_videos()
    if not videos:
        print("No videos found (or not authenticated yet).")
        return

    print("\n📊  Channel Performance Report")
    print(f"{'Title':<45} {'Views':>8} {'Likes':>7}")
    print("-" * 63)
    for v in videos:
        title = v["title"][:44]
        print(f"{title:<45} {v['views']:>8,} {v['likes']:>7,}")


if __name__ == "__main__":
    print_report()
