# /// script
# requires-python = ">=3.11"
# ///
"""
Record the current YouTube statistics of the videos in videos.csv and of their channel.

Each run appends one row per returned video to data/videos/YYYY-MM.csv and one row per channel to
data/channel/YYYY-MM.csv, for the current UTC month. The run prints the IDs of listed videos that
the API returns no data for to stderr, and exits with an error when YOUTUBE_API_KEY is unset or a
request fails with an HTTP error.
"""

import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

VIDEO_LIST = Path("videos.csv")
VIDEOS_DIR = Path("data/videos")
CHANNEL_DIR = Path("data/channel")
VIDEO_FIELDS = ["retrieved_at", "video_id", "views", "likes", "comments"]
CHANNEL_FIELDS = ["retrieved_at", "channel_id", "subscribers", "views", "videos"]
API_URL = "https://www.googleapis.com/youtube/v3"


def fetch(resource: str, key: str, **params: str) -> list[dict]:
    query = urllib.parse.urlencode({**params, "key": key})
    try:
        with urllib.request.urlopen(f"{API_URL}/{resource}?{query}", timeout=30) as response:
            return json.load(response).get("items", [])
    except urllib.error.HTTPError as e:
        sys.exit(f"{resource}.list failed with HTTP {e.code}: {e.read().decode()}")


def append(directory: Path, fields: list[str], rows: list[dict], month: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{month}.csv"
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        if is_new:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        sys.exit("Set YOUTUBE_API_KEY to a YouTube Data API v3 key.")
    with open(VIDEO_LIST, encoding="utf-8") as f:
        ids = [row["video_id"] for row in csv.DictReader(f)]

    retrieved_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    videos = fetch("videos", key, part="snippet,statistics", id=",".join(ids))
    channel_ids = sorted({v["snippet"]["channelId"] for v in videos})
    channels = fetch("channels", key, part="statistics", id=",".join(channel_ids)) if videos else []

    missing = sorted(set(ids) - {v["id"] for v in videos})
    if missing:
        print(f"No data for these videos in videos.csv: {', '.join(missing)}", file=sys.stderr)

    # An absent count stays empty, because 0 would read as a measured count.
    video_rows = [
        {
            "retrieved_at": retrieved_at,
            "video_id": v["id"],
            "views": v["statistics"].get("viewCount", ""),
            "likes": v["statistics"].get("likeCount", ""),
            "comments": v["statistics"].get("commentCount", ""),
        }
        for v in videos
    ]
    channel_rows = [
        {
            "retrieved_at": retrieved_at,
            "channel_id": c["id"],
            "subscribers": c["statistics"].get("subscriberCount", ""),
            "views": c["statistics"].get("viewCount", ""),
            "videos": c["statistics"].get("videoCount", ""),
        }
        for c in channels
    ]
    month = retrieved_at[:7]
    append(VIDEOS_DIR, VIDEO_FIELDS, video_rows, month)
    append(CHANNEL_DIR, CHANNEL_FIELDS, channel_rows, month)
    print(f"Saved {len(video_rows)} of {len(ids)} videos and {len(channel_rows)} channel(s).")


if __name__ == "__main__":
    main()
