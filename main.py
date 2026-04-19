import argparse
import http.server
import os
import socketserver
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

import db
import youtube

DASHBOARD_DIR = Path(__file__).parent / "dashboard"
DASHBOARD_DATA = DASHBOARD_DIR / "data.json"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env_file(Path(__file__).parent / ".env")
console = Console()

DEFAULT_CHANNEL = "UCydlocDyvRtFmMffKytKqgQ"  # Teddy Afro Official
DEFAULT_INTERVAL = 120  # 2 minutes
# Album release: 2026-04-16 1:00 PM CET (= 11:00 UTC)
DEFAULT_SINCE = "2026-04-16T11:00:00+00:00"


def get_client():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        console.print("[red]YOUTUBE_API_KEY not set. "
                      "Add it to .env or export it.[/red]")
        sys.exit(1)
    return youtube.get_client(api_key)


# ── Auto-discovery ────────────────────────────────────────────────────


def discover_and_add(client, channel_id, since):
    """Check for new uploads since `since` and add any we aren't tracking."""
    known = {v["video_id"] for v in db.get_tracked_videos()}
    new_videos = youtube.discover_new_videos(client, channel_id, since)

    new_ids = [v["video_id"] for v in new_videos if v["video_id"] not in known]
    if not new_ids:
        return 0

    # Fetch full stats for the new videos
    stats = youtube.get_video_stats(client, new_ids)
    for s in stats:
        db.add_video(s["video_id"], s["title"], s["channel_id"],
                     s["channel_title"], s["published_at"])
        db.save_video_snapshot(s["video_id"], s["view_count"],
                               s["like_count"], s["comment_count"])
        console.print(f"[green]NEW[/green] {s['title']}  "
                      f"({s['view_count']:,} views)")
    return len(stats)


# ── Commands ──────────────────────────────────────────────────────────


def cmd_add(args):
    """Add videos by ID and take an initial snapshot."""
    client = get_client()
    stats = youtube.get_video_stats(client, args.video_ids)
    for s in stats:
        db.add_video(s["video_id"], s["title"], s["channel_id"],
                     s["channel_title"], s["published_at"])
        db.save_video_snapshot(s["video_id"], s["view_count"],
                               s["like_count"], s["comment_count"])
        console.print(f"[green]+[/green] {s['title']}  "
                      f"({s['view_count']:,} views)")

    found = {s["video_id"] for s in stats}
    for vid in args.video_ids:
        if vid not in found:
            console.print(f"[yellow]Not found:[/yellow] {vid}")


def cmd_add_playlist(args):
    """Add all videos from a playlist."""
    client = get_client()
    videos = youtube.get_playlist_videos(client, args.playlist_id)
    if not videos:
        console.print("[yellow]No videos found in playlist.[/yellow]")
        return

    video_ids = [v["video_id"] for v in videos]
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        stats = youtube.get_video_stats(client, batch)
        for s in stats:
            db.add_video(s["video_id"], s["title"], s["channel_id"],
                         s["channel_title"], s["published_at"])
            db.save_video_snapshot(s["video_id"], s["view_count"],
                                   s["like_count"], s["comment_count"])
            console.print(f"[green]+[/green] {s['title']}  "
                          f"({s['view_count']:,} views)")


def take_snapshot(client):
    """Snapshot all tracked videos + their channel."""
    videos = db.get_tracked_videos()
    if not videos:
        return 0

    video_ids = [v["video_id"] for v in videos]
    stats = youtube.get_video_stats(client, video_ids)
    for s in stats:
        db.save_video_snapshot(s["video_id"], s["view_count"],
                               s["like_count"], s["comment_count"])

    # Channel stats
    for cid in db.get_channel_ids():
        cs = youtube.get_channel_stats(client, cid)
        if cs:
            db.save_channel_snapshot(
                cid, cs["subscriber_count"],
                cs["view_count"], cs["video_count"])

    # Refresh dashboard data
    if DASHBOARD_DIR.exists():
        db.export_to_json(DASHBOARD_DATA)

    return len(stats)


def cmd_snapshot(_args):
    """Take a single snapshot."""
    client = get_client()
    since = datetime.fromisoformat(
        getattr(_args, "since", DEFAULT_SINCE))
    channel = getattr(_args, "channel", DEFAULT_CHANNEL)

    discover_and_add(client, channel, since)
    n = take_snapshot(client)

    now = datetime.now().strftime("%H:%M:%S")
    console.print(f"[dim]{now}[/dim]  snapshot saved ({n} videos)")
    _print_stats()


def cmd_run(args):
    """Auto-discover new videos and poll stats in a loop."""
    interval = args.interval
    channel = args.channel
    since = datetime.fromisoformat(args.since)

    console.print(f"[bold]Channel:[/bold] {channel}")
    console.print(f"[bold]Since:[/bold]   {since.isoformat()}")
    console.print(f"[bold]Poll:[/bold]    every {interval}s")
    console.print("[bold]Ctrl+C to stop[/bold]\n")

    client = get_client()

    try:
        while True:
            # 1. Discover any new uploads
            added = discover_and_add(client, channel, since)

            # 2. Snapshot everything we're tracking
            n = take_snapshot(client)

            now = datetime.now().strftime("%H:%M:%S")
            label = f"  (+{added} new)" if added else ""
            console.print(f"[dim]{now}[/dim]  snapshot saved "
                          f"({n} videos){label}")

            # 3. Display
            _print_stats()
            console.print()

            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped.[/yellow]")


def _print_stats():
    """Render the stats table."""
    snapshots = db.get_latest_snapshots()
    if not snapshots:
        console.print("[yellow]No data yet.[/yellow]")
        return

    table = Table(title="Album Stats", show_lines=False, pad_edge=False)
    table.add_column("#", style="dim", justify="right")
    table.add_column("Title", style="cyan", max_width=55)
    table.add_column("Views", justify="right", style="green")
    table.add_column("Likes", justify="right", style="magenta")
    table.add_column("Comments", justify="right", style="blue")
    table.add_column("Like %", justify="right")
    table.add_column("Time", style="dim")

    total_views = total_likes = total_comments = 0

    for i, row in enumerate(snapshots, 1):
        views = row["view_count"] or 0
        likes = row["like_count"] or 0
        comments = row["comment_count"] or 0
        total_views += views
        total_likes += likes
        total_comments += comments

        like_pct = f"{likes / views * 100:.1f}%" if views else "—"
        ts = (row["timestamp"] or "")[11:19] or "—"

        table.add_row(
            str(i),
            row["title"] or row["video_id"],
            f"{views:,}", f"{likes:,}", f"{comments:,}",
            like_pct, ts,
        )

    table.add_section()
    total_pct = f"{total_likes / total_views * 100:.1f}%" if total_views else "—"
    table.add_row(
        "", "[bold]TOTAL[/bold]",
        f"[bold]{total_views:,}[/bold]",
        f"[bold]{total_likes:,}[/bold]",
        f"[bold]{total_comments:,}[/bold]",
        f"[bold]{total_pct}[/bold]", "",
    )
    console.print(table)

    # Channel summary
    for cid in db.get_channel_ids():
        cs = db.get_latest_channel_snapshot(cid)
        if cs:
            console.print(
                f"  Channel subs: [bold]{cs['subscriber_count']:,}[/bold]  "
                f"Total channel views: {cs['view_count']:,}")


def cmd_stats(_args):
    _print_stats()


def cmd_export(args):
    """Append new snapshots to date-partitioned JSONL files."""
    n_snaps, n_chan = db.export_jsonl_incremental(args.out)
    console.print(f"[green]+{n_snaps}[/green] video snapshots, "
                  f"[green]+{n_chan}[/green] channel snapshots → {args.out}")


def cmd_dashboard(args):
    """Serve the dashboard. Run alongside `run` for live updates."""
    DASHBOARD_DIR.mkdir(exist_ok=True)
    db.export_to_json(DASHBOARD_DATA)

    handler = http.server.SimpleHTTPRequestHandler
    handler.directory = str(DASHBOARD_DIR)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(DASHBOARD_DIR), **kw)

        def do_GET(self):
            # Refresh data.json on every request — always up to date
            if self.path.startswith("/data.json"):
                db.export_to_json(DASHBOARD_DATA)
            super().do_GET()

        def log_message(self, *a):
            pass  # quiet

    with socketserver.TCPServer(("0.0.0.0", args.port), Handler) as httpd:
        console.print(
            f"[bold green]Dashboard:[/bold green] "
            f"http://localhost:{args.port}  (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped.[/yellow]")


def cmd_history(args):
    """Show snapshot history for one video."""
    rows = db.get_video_history(args.video_id, limit=args.limit)
    if not rows:
        console.print(f"[yellow]No history for {args.video_id}[/yellow]")
        return

    table = Table(title=f"History: {args.video_id}")
    table.add_column("Time", style="dim")
    table.add_column("Views", justify="right", style="green")
    table.add_column("delta", justify="right", style="yellow")
    table.add_column("Likes", justify="right", style="magenta")
    table.add_column("Comments", justify="right", style="blue")

    prev_views = None
    for row in reversed(rows):          # oldest first
        views = row["view_count"]
        delta = ""
        if prev_views is not None:
            d = views - prev_views
            delta = f"+{d:,}" if d >= 0 else f"{d:,}"
        prev_views = views

        table.add_row(
            row["timestamp"][11:19],
            f"{views:,}", delta,
            f"{row['like_count']:,}", f"{row['comment_count']:,}",
        )

    console.print(table)


# ── CLI ───────────────────────────────────────────────────────────────


def main():
    db.init_db()

    parser = argparse.ArgumentParser(
        description="YouTube realtime stats tracker")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("add", help="Track videos by ID")
    p.add_argument("video_ids", nargs="+")

    p = sub.add_parser("add-playlist", help="Track all videos in a playlist")
    p.add_argument("playlist_id")

    p = sub.add_parser("snapshot", help="Take one snapshot now")
    p.add_argument("-c", "--channel", default=DEFAULT_CHANNEL)
    p.add_argument("--since", default=DEFAULT_SINCE)

    p = sub.add_parser("run", help="Auto-discover and poll in a loop")
    p.add_argument("-i", "--interval", type=int, default=DEFAULT_INTERVAL,
                   help="Seconds between snapshots (default: 120)")
    p.add_argument("-c", "--channel", default=DEFAULT_CHANNEL,
                   help="Channel ID to watch for new uploads")
    p.add_argument("--since", default=DEFAULT_SINCE,
                   help="Only track videos published after this time (ISO 8601)")

    sub.add_parser("stats", help="Show latest stats")

    p = sub.add_parser("history", help="View history for a video")
    p.add_argument("video_id")
    p.add_argument("-n", "--limit", type=int, default=50)

    p = sub.add_parser("dashboard", help="Serve the web dashboard")
    p.add_argument("-p", "--port", type=int, default=8000)

    p = sub.add_parser("export",
                       help="Append new snapshots to date-partitioned JSONL files")
    p.add_argument("-o", "--out", default="exports",
                   help="Output directory (default: exports/)")

    args = parser.parse_args()

    commands = {
        "add": cmd_add,
        "add-playlist": cmd_add_playlist,
        "snapshot": cmd_snapshot,
        "run": cmd_run,
        "stats": cmd_stats,
        "history": cmd_history,
        "dashboard": cmd_dashboard,
        "export": cmd_export,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
