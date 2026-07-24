from __future__ import annotations

import unittest
from unittest.mock import patch

from github_trending_daily.github_api import GitHubClient


class GitHubSearchTests(unittest.TestCase):
    @patch("github_trending_daily.github_api.get_json")
    def test_maps_search_result_to_radar_candidate(self, get_json_mock) -> None:
        get_json_mock.return_value = {
            "items": [
                {
                    "full_name": "studio/game-tool",
                    "html_url": "https://github.com/studio/game-tool",
                    "description": "A Godot game tool",
                    "language": "GDScript",
                    "stargazers_count": 321,
                    "forks_count": 12,
                    "topics": ["gamedev", "godot"],
                    "license": {"spdx_id": "MIT"},
                    "created_at": "2026-06-01T00:00:00Z",
                    "updated_at": "2026-07-24T00:00:00Z",
                    "pushed_at": "2026-07-24T00:00:00Z",
                    "open_issues_count": 4,
                    "homepage": "",
                    "archived": False,
                    "default_branch": "main",
                }
            ]
        }

        results = GitHubClient(token="test").search_repositories(
            "topic:gamedev",
            per_page=3,
        )

        repo, details = results[0]
        self.assertEqual("radar", repo.source)
        self.assertEqual(321, repo.total_stars)
        self.assertEqual(["gamedev", "godot"], details.topics)
        self.assertEqual("MIT", details.license_name)
        self.assertIn("sort=updated", get_json_mock.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
