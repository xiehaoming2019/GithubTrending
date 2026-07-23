from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from github_trending_daily.pipeline import _load_cached_snapshot


class SnapshotCacheTests(unittest.TestCase):
    def test_loads_repository_details_and_ai_brief(self) -> None:
        payload = [
            {
                "repository": {
                    "rank": 1,
                    "full_name": "example/project",
                    "url": "https://github.com/example/project",
                    "description": "Example",
                    "language": "Python",
                    "total_stars": 100,
                    "forks": 10,
                    "stars_today": 25,
                },
                "details": {
                    "topics": ["example"],
                    "license_name": "MIT",
                    "created_at": "",
                    "updated_at": "",
                    "pushed_at": "",
                    "open_issues": 0,
                    "homepage": "",
                    "archived": False,
                    "default_branch": "main",
                    "readme": "",
                },
                "brief": {
                    "summary": "示例项目",
                    "problem": "解决示例问题",
                    "highlights": ["特点"],
                    "target_users": ["开发者"],
                    "why_trending": "今日受到关注",
                    "caveat": "需要评估",
                    "category": "开发工具",
                    "generated_by_ai": True,
                },
            }
        ]

        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                os.chdir(temp_dir)
                snapshot_dir = Path("data/snapshots")
                snapshot_dir.mkdir(parents=True)
                (snapshot_dir / "2026-07-24.json").write_text(
                    json.dumps(payload, ensure_ascii=False),
                    encoding="utf-8",
                )

                repositories, details, briefs = _load_cached_snapshot(date(2026, 7, 24))
            finally:
                os.chdir(original_cwd)

        self.assertEqual(25, repositories["example/project"].stars_today)
        self.assertEqual("MIT", details["example/project"].license_name)
        self.assertTrue(briefs["example/project"].generated_by_ai)


if __name__ == "__main__":
    unittest.main()

