import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


class BuildSiteTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.dir.name)
        Path("site").mkdir()
        Path("site/index.html").write_text("<html></html>")
        Path("album.json").write_text("{}")
        Path("videos.csv").write_text(
            "track,video_id,title,published_at\n1,a,A,2026-04-16T11:00:00Z\n"
        )
        snap = lambda ts, v: {
            "video_id": "a",
            "timestamp": ts,
            "view_count": v,
            "like_count": 1,
            "comment_count": 1,
        }
        jsonl(
            Path("exports/snapshots/2026-04-16.jsonl"),
            [snap("2026-04-16T12:00:00+00:00", 10), snap("2026-04-16T23:00:00+00:00", 20)],
        )
        jsonl(Path("exports/snapshots/2026-04-20.jsonl"), [snap("2026-04-20T12:00:00+00:00", 50)])
        chan = lambda ts, s: {
            "channel_id": "UC",
            "timestamp": ts,
            "subscriber_count": s,
            "view_count": 1,
            "video_count": 1,
        }
        jsonl(
            Path("exports/channel_snapshots/2026-04-16.jsonl"),
            [chan("2026-04-16T12:00:00+00:00", 100), chan("2026-04-16T23:00:00+00:00", 200)],
        )
        jsonl(
            Path("exports/channel_snapshots/2026-04-20.jsonl"),
            [chan("2026-04-20T01:00:00+00:00", 300), chan("2026-04-20T02:00:00+00:00", 400)],
        )
        Path("data/videos").mkdir(parents=True)
        Path("data/videos/2026-04.csv").write_text(
            "retrieved_at,video_id,views,likes,comments\n2026-04-20T23:00:00Z,a,60,,\n"
        )

    def tearDown(self):
        os.chdir(self.cwd)
        self.dir.cleanup()

    def read(self, name):
        return list(csv.DictReader(Path("_site", name).read_text().splitlines()))

    def test_each_csv_keeps_the_samples_of_its_window(self):
        build_site.main()
        self.assertEqual([r["views"] for r in self.read("race.csv")], ["10", "20"])
        self.assertEqual(
            [(r["hour"], r["views"]) for r in self.read("hourly.csv")],
            [("1", "10"), ("12", "20"), ("97", "50"), ("108", "60")],
        )
        daily = self.read("daily.csv")
        self.assertEqual(
            [(r["date"], r["views"], r["likes"]) for r in daily],
            [("2026-04-16", "20", "1"), ("2026-04-20", "60", "")],
        )
        self.assertEqual(
            [r["subscribers"] for r in self.read("channel.csv")], ["100", "200", "400"]
        )

    def test_listed_video_without_race_samples_stops_the_build(self):
        Path("videos.csv").write_text(
            "track,video_id,title,published_at\n1,a,A,2026-04-16T11:00:00Z\n2,b,B,2026-04-16T11:00:00Z\n"
        )
        with self.assertRaises(SystemExit):
            build_site.main()


if __name__ == "__main__":
    unittest.main()
