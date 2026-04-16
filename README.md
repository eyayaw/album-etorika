# Etorika Album (ኢቶሪካ አልበም)

<p align="center">
  <img src="assets/etorika-album-cover.jpg" alt="ETORIKA album cover" width="480">
</p>

Teddy Afro's *ETORIKA* — 18 tracks, released on YouTube on
**2026-04-16 at 13:00 CET** (11:00 UTC). This repo watches the official
channel in real time and turns the release into a live dashboard of how each
track is doing, minute by minute.

## The tracker

A single page refreshed every 30 seconds, showing:

- **Track standings** — current views per track, ranked
- **Views per track** — each song's growth curve since release
- **Album momentum** — cumulative total views across all 18 tracks
- **Channel subscribers** — how the album translates to channel growth
- **Latest snapshot** — precise numbers at the most recent poll

Under the hood: the tracker polls the YouTube Data API every 2 minutes,
stores snapshots in SQLite, and rewrites a JSON file that the dashboard
reads. Charts are Observable Plot.

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
