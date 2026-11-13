# ETORIKA album tracker (ኤቶሪካ አልበም)

YouTube views of the 18 tracks on Teddy Afro's *ኤቶሪካ (ETORIKA)*, released 2026-04-16, and the
subscriber count of his channel, charted since release day at <https://etorika.datakomari.com>.

<p align="center">
  <img src="assets/etorika-album-cover.jpg" alt="ETORIKA album cover" width="360">
</p>

## How it works

- `collect.py` runs on GitHub Actions twice a day and appends the statistics of the videos in
  `videos.csv` and of their channel to monthly CSVs under `data/`.
- `exports/` holds the snapshots that a tracker on a separate server has taken about every two
  minutes since release. `scripts/push-exports.sh` pulls new snapshots from that server and commits
  them.
- `build_site.py` builds the site in `_site/` from `site/` and both sets of samples. The `pages`
  workflow publishes it to GitHub Pages after every push to `main` and every successful `collect`
  run.

## Run locally

With a [YouTube Data API v3 key](https://console.cloud.google.com/apis/credentials):

```bash
YOUTUBE_API_KEY=your-key uv run collect.py
uv run build_site.py
python3 -m http.server -d _site 8000
python3 -m unittest discover -s tests
```

## Credits

*ETORIKA* © Teddy Afro. This repository is a tracker. It only stores and visualizes publicly
reported YouTube statistics. It redistributes no audio, video, or lyrics, and it uses the album
cover in `assets/` under fair use.
