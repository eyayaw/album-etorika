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

- **Tracker** — polls the YouTube Data API every 2 minutes, auto-discovers
  new uploads on the channel since release time, and stores per-track +
  channel-level snapshots in SQLite (WAL mode).
- **Export** — after every poll, the tracker rewrites `dashboard/data.json`,
  which the dashboard reads.
- **Charts** — Observable Plot + d3 in a single static HTML file.
- **Hosted** on a small Hetzner VPS; nginx serves the static dashboard on
  an allowlist of exactly three paths.

## Try it locally

### Prerequisites

- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- A YouTube Data API key — create one at
  [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
  and enable *YouTube Data API v3*

### Run

```bash
uv sync                                    # install deps
echo "YOUTUBE_API_KEY=your-key" > .env
uv run python main.py run                  # start the tracker
uv run python main.py dashboard            # → http://localhost:8000
```

<details>
<summary>Other commands</summary>

| Command | What it does |
| --- | --- |
| `run` | Auto-discover new uploads + snapshot everything in a loop |
| `snapshot` | Take a single snapshot of all tracked videos |
| `add VIDEO_ID …` | Manually track specific videos |
| `add-playlist PLAYLIST_ID` | Track all videos in a playlist |
| `stats` | Print the latest snapshot as a table |
| `history VIDEO_ID` | Show snapshot deltas for one track |
| `dashboard` | Serve the web dashboard (default port 8000) |

Useful flags: `-i 60` to poll every 60s, `-p 8080` for a different
dashboard port.

</details>

## Credits

*ETORIKA* © Teddy Afro. This repository is an observer / tracker — it only
stores and visualises publicly-reported YouTube statistics. No audio, video,
lyrics, or artwork (besides the album cover used under fair-use linking) is
redistributed here.

## License

MIT.
