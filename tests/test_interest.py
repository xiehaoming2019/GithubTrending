from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from github_trending_daily.interest import (
    OpenAIInterestClassifier,
    fallback_interest,
    select_repositories,
)
from github_trending_daily.models import (
    InterestMatch,
    RepositoryDetails,
    TrendingRepository,
)


def _repo(
    full_name: str,
    description: str,
    *,
    rank: int = 1,
    stars_today: int = 100,
) -> TrendingRepository:
    return TrendingRepository(
        rank=rank,
        full_name=full_name,
        url=f"https://github.com/{full_name}",
        description=description,
        stars_today=stars_today,
    )


class FallbackInterestTests(unittest.TestCase):
    def test_recognizes_agent_skills(self) -> None:
        repo = _repo("creator/agent-skills", "MCP agent skills for Codex workflows")

        match = fallback_interest(repo, RepositoryDetails(topics=["mcp", "ai-agent"]))

        self.assertGreaterEqual(match.score, 60)
        self.assertEqual("AI Agent / Skills", match.category)
        self.assertFalse(match.generated_by_ai)

    def test_recognizes_game_development(self) -> None:
        repo = _repo("studio/game-engine", "An open source game engine for Godot creators")

        match = fallback_interest(repo, RepositoryDetails(topics=["gamedev"]))

        self.assertGreaterEqual(match.score, 60)
        self.assertEqual("游戏开发", match.category)

    def test_rejects_crypto_trading_agent(self) -> None:
        repo = _repo("finance/trading-agent", "AI agent for a crypto trading bot")

        match = fallback_interest(repo, RepositoryDetails(topics=["cryptocurrency"]))

        self.assertLess(match.score, 60)

    def test_selection_keeps_category_diversity(self) -> None:
        repositories = [
            _repo(f"agents/project-{index}", "agent", rank=index, stars_today=200 - index)
            for index in range(1, 5)
        ]
        repositories.extend(
            [
                _repo("games/engine", "game", rank=5, stars_today=80),
                _repo("video/editor", "video", rank=6, stars_today=70),
            ]
        )
        matches = [
            InterestMatch(repo.full_name, 95 - repo.rank, "AI Agent / Skills", "")
            for repo in repositories[:4]
        ]
        matches.extend(
            [
                InterestMatch("games/engine", 85, "游戏开发", ""),
                InterestMatch("video/editor", 80, "视频剪辑", ""),
            ]
        )

        selected = select_repositories(
            repositories,
            matches,
            limit=5,
            threshold=60,
        )

        self.assertEqual(5, len(selected))
        self.assertIn("games/engine", {repo.full_name for repo in selected})
        self.assertIn("video/editor", {repo.full_name for repo in selected})
        self.assertEqual(
            3,
            sum(repo.full_name.startswith("agents/") for repo in selected),
        )


class OpenAIInterestClassifierTests(unittest.TestCase):
    @patch("github_trending_daily.interest.post_json")
    def test_parses_batch_response(self, post_json_mock) -> None:
        post_json_mock.return_value = {
            "output_text": json.dumps(
                {
                    "matches": [
                        {
                            "repository": "studio/game",
                            "score": 91,
                            "category": "游戏开发",
                            "reason": "面向游戏开发",
                        }
                    ]
                },
                ensure_ascii=False,
            )
        }
        classifier = OpenAIInterestClassifier(api_key="test-key")
        candidates = [
            (
                _repo("studio/game", "A Godot game engine"),
                RepositoryDetails(topics=["gamedev"]),
            )
        ]

        matches = classifier.classify(candidates)

        self.assertEqual(1, len(matches))
        self.assertEqual(91, matches[0].score)
        self.assertEqual("游戏开发", matches[0].category)
        self.assertTrue(matches[0].generated_by_ai)


if __name__ == "__main__":
    unittest.main()
