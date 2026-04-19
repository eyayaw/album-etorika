import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "stats.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            channel_id TEXT,
            channel_title TEXT,
            published_at TEXT,
            added_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS video_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        );

        CREATE TABLE IF NOT EXISTS channel_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            subscriber_count INTEGER,
            view_count INTEGER,
            video_count INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_vs_video_ts
            ON video_snapshots(video_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_cs_channel_ts
            ON channel_snapshots(channel_id, timestamp);
    """)
    conn.commit()
    conn.close()


def add_video(video_id, title, channel_id, channel_title, published_at):
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO videos
           (video_id, title, channel_id, channel_title, published_at, added_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (video_id, title, channel_id, channel_title, published_at,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def save_video_snapshot(video_id, view_count, like_count, comment_count):
    conn = get_connection()
    conn.execute(
        """INSERT INTO video_snapshots
           (video_id, timestamp, view_count, like_count, comment_count)
           VALUES (?, ?, ?, ?, ?)""",
        (video_id, datetime.now(timezone.utc).isoformat(),
         view_count, like_count, comment_count),
    )
    conn.commit()
    conn.close()


def save_channel_snapshot(channel_id, subscriber_count, view_count, video_count):
    conn = get_connection()
    conn.execute(
        """INSERT INTO channel_snapshots
           (channel_id, timestamp, subscriber_count, view_count, video_count)
           VALUES (?, ?, ?, ?, ?)""",
        (channel_id, datetime.now(timezone.utc).isoformat(),
         subscriber_count, view_count, video_count),
    )
    conn.commit()
    conn.close()


def get_tracked_videos():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM videos ORDER BY published_at DESC"
    ).fetchall()
    conn.close()
    return rows


def get_latest_snapshots():
    conn = get_connection()
    rows = conn.execute("""
        SELECT v.video_id, v.title, vs.view_count, vs.like_count,
               vs.comment_count, vs.timestamp
        FROM videos v
        LEFT JOIN video_snapshots vs ON v.video_id = vs.video_id
            AND vs.timestamp = (
                SELECT MAX(timestamp) FROM video_snapshots
                WHERE video_id = v.video_id
            )
        ORDER BY vs.view_count DESC NULLS LAST
    """).fetchall()
    conn.close()
    return rows


def get_video_history(video_id, limit=50):
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM video_snapshots
           WHERE video_id = ? ORDER BY timestamp DESC LIMIT ?""",
        (video_id, limit),
    ).fetchall()
    conn.close()
    return rows


def get_latest_channel_snapshot(channel_id):
    conn = get_connection()
    row = conn.execute(
        """SELECT * FROM channel_snapshots
           WHERE channel_id = ? ORDER BY timestamp DESC LIMIT 1""",
        (channel_id,),
    ).fetchone()
    conn.close()
    return row


def get_channel_ids():
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT channel_id FROM videos WHERE channel_id IS NOT NULL"
    ).fetchall()
    conn.close()
    return [r["channel_id"] for r in rows]


def export_to_json(path):
    """Dump everything to JSON for the dashboard."""
    conn = get_connection()
    videos = [dict(r) for r in conn.execute(
        "SELECT * FROM videos ORDER BY published_at"
    ).fetchall()]
    snapshots = [dict(r) for r in conn.execute(
        """SELECT video_id, timestamp, view_count, like_count, comment_count
           FROM video_snapshots ORDER BY timestamp"""
    ).fetchall()]
    channel_snapshots = [dict(r) for r in conn.execute(
        """SELECT channel_id, timestamp, subscriber_count, view_count, video_count
           FROM channel_snapshots ORDER BY timestamp"""
    ).fetchall()]
    conn.close()

    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "videos": videos,
        "snapshots": snapshots,
        "channel_snapshots": channel_snapshots,
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ── Incremental JSONL export ────────────────────────────────────────


def _max_timestamp(partition_dir):
    """Return the max timestamp across all .jsonl files in partition_dir."""
    files = sorted(Path(partition_dir).glob("*.jsonl"))
    if not files:
        return None
    # Most recent partition contains the latest rows (date-sorted filenames)
    last_ts = None
    with open(files[-1], "rb") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            ts = json.loads(line).get("timestamp")
            if ts and (last_ts is None or ts > last_ts):
                last_ts = ts
    return last_ts


def _append_partitioned(out_dir, rows):
    """Append rows to JSONL files partitioned by UTC date (YYYY-MM-DD)."""
    by_date = {}
    for r in rows:
        d = dict(r)
        date = d["timestamp"][:10]
        by_date.setdefault(date, []).append(d)

    for date, items in by_date.items():
        path = Path(out_dir) / f"{date}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return sum(len(v) for v in by_date.values())


def export_jsonl_incremental(out_dir):
    """Append new snapshots to date-partitioned JSONL files.

    Idempotent: scans existing partitions to find the last exported
    timestamp, then exports only strictly newer rows.

    Layout:
        out_dir/
            videos.jsonl                    (full snapshot, rewritten each run)
            snapshots/YYYY-MM-DD.jsonl      (append-only)
            channel_snapshots/YYYY-MM-DD.jsonl  (append-only)
    """
    out = Path(out_dir)
    snaps_dir = out / "snapshots"
    chan_dir  = out / "channel_snapshots"
    snaps_dir.mkdir(parents=True, exist_ok=True)
    chan_dir.mkdir(parents=True, exist_ok=True)

    last_snap_ts = _max_timestamp(snaps_dir)
    last_chan_ts = _max_timestamp(chan_dir)

    conn = get_connection()

    # videos table is small (~tens of rows); rewrite each run for simplicity
    videos = [dict(r) for r in conn.execute(
        "SELECT * FROM videos ORDER BY published_at"
    ).fetchall()]
    with open(out / "videos.jsonl", "w", encoding="utf-8") as f:
        for v in videos:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")

    new_snaps = [dict(r) for r in conn.execute(
        """SELECT video_id, timestamp, view_count, like_count, comment_count
           FROM video_snapshots
           WHERE timestamp > ?
           ORDER BY timestamp""",
        (last_snap_ts or "",),
    ).fetchall()]

    new_chan = [dict(r) for r in conn.execute(
        """SELECT channel_id, timestamp, subscriber_count, view_count, video_count
           FROM channel_snapshots
           WHERE timestamp > ?
           ORDER BY timestamp""",
        (last_chan_ts or "",),
    ).fetchall()]

    conn.close()

    n_snaps = _append_partitioned(snaps_dir, new_snaps)
    n_chan  = _append_partitioned(chan_dir, new_chan)
    return n_snaps, n_chan
