# Etorika Album (ኤቶሪካ አልበም)

<p align="center">
  <img src="assets/etorika-album-cover.jpg" alt="ETORIKA album cover" width="480">
</p>

Teddy Afro's *ኤቶሪካ (Etorika)* album — 18 tracks, released on YouTube on
**2026-04-16 at 14:00 EAT** (11:00 UTC). This repo watches the official
channel in real time and turns the release into a live dashboard of how each
track is doing, minute by minute.

**🔴 Live:** <https://etorika.datakomari.com>

## The dashboard

Auto-refreshed every 30 seconds, showing:

- **KPI strip** — total album views, likes, comments, average like rate,
  channel subscriber growth, all anchored to release time
- **Track standings** — horizontal bar chart ranked by views, with a live
  running total overlaid in the empty corner
- **Views per track** — one line per song since release, with per-track
  release markers (tracks didn't all drop at the same moment)
- **Album momentum** — cumulative total with a smooth curve + release dots
- **Channel subscribers** — buzz translated into channel growth
- **Latest snapshot** — precise current numbers, each row clickable to the
  track on YouTube

The page is mobile-aware, dark-mode only (with `color-scheme: dark` so Dark
Reader leaves it alone), and completely static — it just fetches
`data.json` from the tracker.

## Under the hood

- **Tracker** — polls the YouTube Data API every 2 minutes, auto-discovers
  new uploads on the channel since release time, and stores per-track +
  channel-level snapshots in SQLite (WAL mode).
- **Export** — after every poll, the tracker rewrites `dashboard/data.json`,
  which the dashboard reads.
- **Charts** — Observable Plot + d3 in a single static HTML file.
- **Hosted** on a small Hetzner VPS; nginx serves the static dashboard on
  an allowlist of exactly three paths.

## Try it locally

```bash
uv sync                                    # install deps
echo "YOUTUBE_API_KEY=your-key" > .env     # get one from the link below
uv run python main.py run                  # start the tracker
uv run python main.py dashboard            # → http://localhost:8000
```

Get a YouTube Data API key at
[console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
— enable "YouTube Data API v3" first.
