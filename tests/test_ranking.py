from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from github_trending_daily.interest import select_repositories
from github_trending_daily.models import (
    InterestMatch,
    RepositoryDetails,
    TrendingRepository,
)
from github_trending_daily.ranking import (
    apply_ranking_metrics,
    load_previous_candidate_totals,
    write_candidate_snapshot,
)


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


class RankingTests(unittest.TestCase):
    def test_loads_latest_available_candidate_totals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate_dir = Path(temp_dir)
            payload = [
                {
                    "repository": {
                        "full_name": "studio/tool",
                        "total_stars": 450,
                    }
                }
            ]
            (candidate_dir / "2026-07-22.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            totals = load_previous_candidate_totals(
                date(2026, 7, 24),
                days=7,
                candidate_dir=candidate_dir,
            )

        self.assertEqual(450, totals["studio/tool"])

    def test_applies_velocity_freshness_and_weighted_score(self) -> None:
        trending = _repo("studio/game", total_stars=2_000, stars_today=600)
        radar = _repo(
            "creator/video",
            total_stars=900,
            source="radar",
        )
        candidates = [
            (
                trending,
                RepositoryDetails(created_at="2026-07-20T00:00:00Z"),
            ),
            (
                radar,
                RepositoryDetails(created_at="2026-01-01T00:00:00Z"),
            ),
        ]
        matches = [
            InterestMatch("studio/game", 80, "游戏开发", ""),
            InterestMatch("creator/video", 90, "视频剪辑", ""),
        ]

        apply_ranking_metrics(
            candidates,
            matches,
            report_date=date(2026, 7, 24),
            previous_totals={"creator/video": 800},
        )

        self.assertEqual(600, trending.star_gain)
        self.assertEqual(100, radar.star_gain)
        self.assertEqual(100, matches[0].freshness_score)
        self.assertGreater(matches[0].ranking_score, 0)
        self.assertGreater(matches[1].velocity_score, 0)

    def test_selection_uses_weighted_ranking_score(self) -> None:
        slow = _repo("studio/slow", total_stars=10_000)
        fast = _repo("studio/fast", total_stars=500)
        matches = [
            InterestMatch(
                "studio/slow",
                95,
                "游戏开发",
                "",
                ranking_score=50,
            ),
            InterestMatch(
                "studio/fast",
                80,
                "游戏开发",
                "",
                ranking_score=80,
            ),
        ]

        selected = select_repositories(
            [slow, fast],
            matches,
            limit=1,
            threshold=60,
        )

        self.assertEqual("studio/fast", selected[0].full_name)

    def test_writes_compact_candidate_snapshot(self) -> None:
        repo = _repo("studio/game", total_stars=100, stars_today=20)
        details = RepositoryDetails(created_at="2026-07-01T00:00:00Z")
        match = InterestMatch(
            "studio/game",
            88,
            "游戏开发",
            "游戏工具",
            ranking_score=72.5,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_candidate_snapshot(
                date(2026, 7, 24),
                [(repo, details)],
                [match],
                candidate_dir=Path(temp_dir),
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual("studio/game", payload[0]["repository"]["full_name"])
        self.assertEqual(72.5, payload[0]["interest"]["ranking_score"])


if __name__ == "__main__":
    unittest.main()
