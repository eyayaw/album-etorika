# /// script
# requires-python = ">=3.11"
# ///
"""
Build the static site in _site/ from site/, album.json, videos.csv, and the samples in exports/ and
data/.

Next to the copied files, the build writes the CSVs that site/index.html charts:

- race.csv: every sample in each track's first RACE_HOURS after it was published.
- hourly.csv: for each track and each hour since it was published, up to RANK_HOURS, the last
  sample in that hour. An hour without a sample has no row.
- daily.csv: each track's last sample per UTC day.
- channel.csv: every channel sample up to RACE_HOURS after the first track was published, then the
  last sample per UTC day.
"""

import csv
import glob
import json
import math
import shutil
import sys
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

SITE = Path("_site")
RACE_HOURS = 48
# The longest window of the rank chart in site/index.html.
RANK_HOURS = 14 * 24

# Maps each output column to its field in the archive's JSONL. The CSVs that collect.py writes
# already use the output column names.
VIDEO_FIELDS = {
    "video_id": "video_id",
    "views": "view_count",
    "likes": "like_count",
    "comments": "comment_count",
}
CHANNEL_FIELDS = {"subscribers": "subscriber_count", "views": "view_count", "videos": "video_count"}


def samples(
    archive: str, collected: str, fields: dict[str, str]
) -> Iterator[tuple[datetime, dict]]:
    """Yield (time, row) for each sample in archive/*.jsonl, then in collected/*.csv."""
    for path in sorted(glob.glob(f"{archive}/*.jsonl")):
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                yield datetime.fromisoformat(r["timestamp"]), {k: r[v] for k, v in fields.items()}
    for path in sorted(glob.glob(f"{collected}/*.csv")):
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                yield datetime.fromisoformat(r["retrieved_at"]), {k: r[k] for k in fields}


def keep_latest(table: dict, key: object, at: datetime, row: dict) -> None:
    if key not in table or at > table[key][0]:
        table[key] = (at, row)


def write_csv(name: str, fields: list[str], rows: list[dict]) -> None:
    with open(SITE / name, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    with open("videos.csv", encoding="utf-8") as f:
        published = {
            r["video_id"]: datetime.fromisoformat(r["published_at"]) for r in csv.DictReader(f)
        }

    race: list[dict] = []
    hourly: dict[tuple[str, int], tuple[datetime, dict]] = {}
    daily: dict[tuple[str, str], tuple[datetime, dict]] = {}
    for at, row in samples("exports/snapshots", "data/videos", VIDEO_FIELDS):
        if row["video_id"] not in published:
            continue
        hours = (at - published[row["video_id"]]).total_seconds() / 3600
        if 0 < hours <= RACE_HOURS:
            race.append({**row, "hours": round(hours, 3)})
        if 0 < hours <= RANK_HOURS:
            hour = math.ceil(hours)
            keep_latest(hourly, (row["video_id"], hour), at, {**row, "hour": hour})
        keep_latest(daily, (at.date().isoformat(), row["video_id"]), at, row)

    missing = sorted(set(published) - {r["video_id"] for r in race})
    if missing:
        sys.exit(
            f"No samples in the first {RACE_HOURS} hours after publication for "
            f"{', '.join(missing)}. Check their video_id and published_at in videos.csv."
        )

    release = min(published.values())
    channel: dict[str, tuple[datetime, dict]] = {}
    for at, row in samples("exports/channel_snapshots", "data/channel", CHANNEL_FIELDS):
        within_race = at - release <= timedelta(hours=RACE_HOURS)
        keep_latest(channel, at.isoformat() if within_race else at.date().isoformat(), at, row)

    shutil.rmtree(SITE, ignore_errors=True)
    shutil.copytree("site", SITE)
    for name in ["album.json", "videos.csv"]:
        shutil.copy(name, SITE)
    write_csv("race.csv", ["video_id", "hours", "views"], race)
    write_csv(
        "hourly.csv", ["video_id", "hour", "views"], [r for _, (_, r) in sorted(hourly.items())]
    )
    write_csv(
        "daily.csv",
        ["date", "video_id", "views", "likes", "comments"],
        [{"date": date, **row} for (date, _), (_, row) in sorted(daily.items())],
    )
    write_csv(
        "channel.csv",
        ["retrieved_at", "subscribers", "views", "videos"],
        [
            {"retrieved_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"), **row}
            for at, row in sorted(channel.values(), key=lambda v: v[0])
        ],
    )
    print(
        f"Built {SITE}/: {len(race)} race, {len(hourly)} hourly, {len(daily)} daily, "
        f"{len(channel)} channel rows."
    )


if __name__ == "__main__":
    main()
