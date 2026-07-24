from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from github_trending_daily.history import (
    filter_recent_repeats,
    load_recent_history,
)
from github_trending_daily.models import TrendingRepository


def _repo(
    full_name: str,
    *,
    total_stars: int,
    stars_today: int = 0,
    source: str = "trending",
) -> TrendingRepository:
    return TrendingRepository(
        rank=1,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        total_stars=total_stars,
        stars_today=stars_today,
        source=source,
    )


class HistoryTests(unittest.TestCase):
    def test_loads_recent_snapshots_and_counts_appearances(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = Path(temp_dir)
            for day, stars in (("2026-07-22", 100), ("2026-07-23", 130)):
                payload = [
                    {
                        "repository": {
                            "full_name": "studio/game",
                            "total_stars": stars,
                            "stars_today": 30,
                        }
                    }
                ]
                (snapshot_dir / f"{day}.json").write_text(
                    json.dumps(payload),
                    encoding="utf-8",
                )

            history = load_recent_history(
                date(2026, 7, 24),
                days=7,
                snapshot_dir=snapshot_dir,
            )

        record = history["studio/game"]
        self.assertEqual(2, record.appearances)
        self.assertEqual(date(2026, 7, 23), record.last_seen)
        self.assertEqual(130, record.total_stars)

    def test_skips_recent_repeat_but_keeps_hot_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = Path(temp_dir)
            payload = [
                {
                    "repository": {
                        "full_name": "studio/old",
                        "total_stars": 1_000,
                        "stars_today": 100,
                    }
                },
                {
                    "repository": {
                        "full_name": "studio/hot",
                        "total_stars": 2_000,
                        "stars_today": 1_600,
                    }
                },
            ]
            (snapshot_dir / "2026-07-23.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            history = load_recent_history(
                date(2026, 7, 24),
                snapshot_dir=snapshot_dir,
            )

        repositories = [
            _repo("studio/old", total_stars=1_050, stars_today=50),
            _repo("studio/hot", total_stars=3_600, stars_today=1_600),
            _repo("studio/new", total_stars=50, stars_today=20),
        ]
        selected, skipped = filter_recent_repeats(
            repositories,
            history,
            report_date=date(2026, 7, 24),
        )

        self.assertEqual(1, skipped)
        self.assertEqual(
            {"studio/hot", "studio/new"},
            {repo.full_name for repo in selected},
        )
        labels = {repo.full_name: repo.history_label for repo in selected}
        self.assertEqual("连续上榜", labels["studio/hot"])
        self.assertEqual("本周首次收录", labels["studio/new"])

    def test_radar_repeat_requires_meaningful_star_growth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = Path(temp_dir)
            payload = [
                {
                    "repository": {
                        "full_name": "creator/tool",
                        "total_stars": 1_000,
                        "stars_today": 0,
                    }
                }
            ]
            (snapshot_dir / "2026-07-23.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            history = load_recent_history(
                date(2026, 7, 24),
                snapshot_dir=snapshot_dir,
            )

        selected, skipped = filter_recent_repeats(
            [_repo("creator/tool", total_stars=1_100, source="radar")],
            history,
            report_date=date(2026, 7, 24),
        )
        self.assertEqual([], selected)
        self.assertEqual(1, skipped)


if __name__ == "__main__":
    unittest.main()
