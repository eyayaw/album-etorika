# Etorika Album (ኤቶሪካ አልበም)

A small project to monitor the album's traction in real time.

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

Dark mode, mobile-aware, static HTML + `data.json` — no backend at request
time.

## Under the hood

- **Collection** — a GitHub Actions workflow runs `collect.py` twice a day. It
  appends statistics for the tracks in `videos.csv` to `data/videos/YYYY-MM.csv` and for
  their channel to `data/channel/YYYY-MM.csv`.
- **Tracker** — a process on the VPS polls the YouTube Data API every 2 minutes and
  stores snapshots in SQLite. A daily cron job runs `scripts/push-exports.sh`, which
  copies them into `exports/`, one JSONL file per UTC day.
- **Export** — after every poll, the tracker rewrites `dashboard/data.json`,
  which the dashboard reads.
- **Charts** — Observable Plot + d3 in a single static HTML file.
- **Hosted** on a small Hetzner VPS; nginx serves the static dashboard on
  an allowlist of exactly three paths.

## Try it locally

`collect.py` uses only stdlib Python. Get a
[YouTube Data API key](https://console.cloud.google.com/apis/credentials) with
*YouTube Data API v3* enabled, and run:

```bash
export YOUTUBE_API_KEY=your-key
uv run collect.py
```

## Credits

*ETORIKA* © Teddy Afro. This repository is an observer / tracker — it only
stores and visualises publicly-reported YouTube statistics. No audio, video,
lyrics, or artwork (besides the album cover used under fair-use linking) is
redistributed here.

## License

MIT.
