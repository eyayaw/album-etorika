from datetime import datetime

from googleapiclient.discovery import build


def get_client(api_key):
    return build("youtube", "v3", developerKey=api_key)


def get_video_stats(client, video_ids):
    """Fetch stats for up to 50 videos in one API call (1 quota unit)."""
    response = (
        client.videos()
        .list(
            part="snippet,statistics",
            id=",".join(video_ids),
        )
        .execute()
    )

    results = []
    for item in response.get("items", []):
        stats = item["statistics"]
        snippet = item["snippet"]
        results.append(
            {
                "video_id": item["id"],
                "title": snippet["title"],
                "channel_id": snippet["channelId"],
                "channel_title": snippet["channelTitle"],
                "published_at": snippet["publishedAt"],
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
            }
        )
    return results


def get_channel_stats(client, channel_id):
    """Fetch channel-level stats (1 quota unit)."""
    response = (
        client.channels()
        .list(
            part="statistics,snippet",
            id=channel_id,
        )
        .execute()
    )

    if not response.get("items"):
        return None

    item = response["items"][0]
    stats = item["statistics"]
    return {
        "channel_id": item["id"],
        "title": item["snippet"]["title"],
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "view_count": int(stats.get("viewCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
    }


def uploads_playlist_id(channel_id):
    """Derive the uploads playlist ID from a channel ID (UC... -> UU...)."""
    return "UU" + channel_id[2:]


def discover_new_videos(client, channel_id, since):
    """Find videos uploaded to a channel after `since` (datetime, UTC).

    Uses the uploads playlist (1 quota unit) instead of search (100 units).
    Returns only videos not yet seen, newest first.
    """
    playlist_id = uploads_playlist_id(channel_id)
    videos = []
    next_page = None

    while True:
        response = (
            client.playlistItems()
            .list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page,
            )
            .execute()
        )

        stop = False
        for item in response.get("items", []):
            snippet = item["snippet"]
            published = snippet["publishedAt"]  # e.g. 2026-04-16T11:00:00Z
            pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))

            if pub_dt < since:
                stop = True
                break

            videos.append(
                {
                    "video_id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "channel_id": snippet.get("channelId"),
                    "published_at": published,
                }
            )

        if stop:
            break
        next_page = response.get("nextPageToken")
        if not next_page:
            break

    return videos


def get_playlist_videos(client, playlist_id):
    """Get all videos from a playlist (e.g., an album playlist)."""
    videos = []
    next_page = None

    while True:
        response = (
            client.playlistItems()
            .list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page,
            )
            .execute()
        )

        for item in response.get("items", []):
            snippet = item["snippet"]
            videos.append(
                {
                    "video_id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "channel_id": snippet.get("channelId"),
                    "published_at": snippet["publishedAt"],
                }
            )

        next_page = response.get("nextPageToken")
        if not next_page:
            break

    return videos
