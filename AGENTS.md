# AGENTS

## Purpose

Charts the YouTube views of the 18 tracks on Teddy Afro's ETORIKA and the subscriber count of his
channel, on a static site at <https://etorika.datakomari.com> served by GitHub Pages.

## Map

- `videos.csv`: the tracked videos (`track`, `video_id`, `title`, `published_at`). The release time
  is the earliest `published_at`.
- `album.json`: the page heading and tab title (`title`, used verbatim), the credit (`artist`,
  `album`), and the accent color per color scheme.
- `collect.py`: appends one row per video and per channel to `data/videos/YYYY-MM.csv` and
  `data/channel/YYYY-MM.csv`. An empty count means the API omitted it. The `collect` workflow runs
  it at 11:17 and 23:17 UTC and commits `data/`.
- `build_site.py`: copies `site/`, `album.json`, and `videos.csv` into `_site/` and writes the
  chart CSVs from `data/`. The `pages` workflow builds and deploys after each push to `main` and
  each successful `collect` run.
- `site/index.html`: the whole page, with Observable Plot and d3 from jsDelivr and no build step.
  `site/fonts/` holds the Libre Franklin Latin subset.

## Design

- `RACE_HOURS` and `RANK_HOURS` in `build_site.py` set the chart windows. The `<h3>` titles and the
  rank-window buttons in `site/index.html` repeat 48, 168, and 336 hours, so change them together.
- `data/` up to 2026-11-13 holds the VPS tracker's two-minute samples, thinned to what the windows
  read: every sample in a track's first 48 hours, the last of each hour of its first 14 days, and
  the last of each UTC day. A wider window needs the full archive, which is `exports/` in the git
  history up to commit `b658e7d`.
- Marks take their colors from CSS variables (`var(--ink)`), so a color-scheme switch needs no
  redraw. Each mark drawn per track carries the video ID as its `aria-label`, and highlighting
  toggles the `.on` class on matching marks across charts.
- The custom domain is a Namecheap CNAME `etorika` → `eyayaw.github.io`, with the domain set in the
  repo's Pages settings. The site deploys from a workflow, so there is no `CNAME` file.

## Non-goals

- Commentary on the page. Titles name what each chart plots, and axis and data labels carry the
  numbers, because computed findings stop fitting the data.
- Committed build output. `_site/` is built in CI.

## Verify

```bash
uvx ruff check . && uvx ruff format --check .
python3 -m unittest discover -s tests
uv run build_site.py && python3 -m http.server -d _site 8000
```

Check the page in both light and dark color schemes. `collect.py` spends YouTube Data API quota.
