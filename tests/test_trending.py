from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from github_trending_daily.models import (
    ProjectBrief,
    RepositoryDetails,
    TrendingRepository,
)
from github_trending_daily.render import render_email_html, render_markdown
from github_trending_daily.summarize import fallback_brief
from github_trending_daily.trending import parse_trending, trending_url


FIXTURE = Path(__file__).parent / "fixtures" / "trending.html"


class TrendingParserTests(unittest.TestCase):
    def test_parses_repository_fields(self) -> None:
        repositories = parse_trending(FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(2, len(repositories))
        first = repositories[0]
        self.assertEqual("octocat/hello-world", first.full_name)
        self.assertEqual("Python", first.language)
        self.assertEqual(12_345, first.total_stars)
        self.assertEqual(678, first.forks)
        self.assertEqual(234, first.stars_today)
        self.assertEqual(1, first.rank)

    def test_builds_language_url(self) -> None:
        self.assertEqual(
            "https://github.com/trending/python?since=daily",
            trending_url("Python"),
        )

    def test_fallback_and_render(self) -> None:
        repo = parse_trending(FIXTURE.read_text(encoding="utf-8"))[0]
        details = RepositoryDetails(topics=["example"], license_name="MIT")
        brief = fallback_brief(repo, details)

        report = render_markdown(date(2026, 7, 23), [(repo, details, brief)])

        self.assertIn("# GitHub Trending ACG 日报 · 2026-07-23", report)
        self.assertIn("[octocat/hello-world]", report)
        self.assertIn("今日 +234", report)
        self.assertIn("约 3 分钟读完", report)
        self.assertIn("今天只看这 1 个", report)

        html = render_email_html(date(2026, 7, 23), [(repo, details, brief)])
        self.assertIn("<!doctype html>", html)
        self.assertIn("https://github.com/octocat/hello-world", html)
        self.assertIn("GitHub Trending ACG 日报", html)
        self.assertIn("约 3 分钟读完", html)

    def test_renders_an_empty_filtered_edition(self) -> None:
        report = render_markdown(date(2026, 7, 23), [])
        html = render_email_html(date(2026, 7, 23), [])

        self.assertIn("今天不硬凑", report)
        self.assertIn("没有项目达到 ACG", report)
        self.assertIn("今天不硬凑", html)
        self.assertIn("<!doctype html>", html)

    def test_featured_section_prefers_category_diversity(self) -> None:
        details = RepositoryDetails()
        agent_brief = ProjectBrief(
            summary="Agent 项目",
            problem="",
            highlights=["Agent 亮点"],
            target_users=[],
            why_trending="",
            caveat="注意",
            category="AI Agent / Skills",
        )
        game_brief = ProjectBrief(
            summary="游戏项目",
            problem="",
            highlights=["游戏亮点"],
            target_users=[],
            why_trending="",
            caveat="注意",
            category="游戏开发",
        )
        items = [
            (
                TrendingRepository(
                    rank=index,
                    full_name=f"agent/project-{index}",
                    url=f"https://github.com/agent/project-{index}",
                    stars_today=400 - index,
                ),
                details,
                agent_brief,
            )
            for index in range(1, 4)
        ]
        items.append(
            (
                TrendingRepository(
                    rank=4,
                    full_name="studio/game",
                    url="https://github.com/studio/game",
                    stars_today=50,
                ),
                details,
                game_brief,
            )
        )

        report = render_markdown(date(2026, 7, 23), items)

        self.assertIn("### 2. [studio/game]", report)
        self.assertIn("· 游戏开发 · 今日 +50", report)


if __name__ == "__main__":
    unittest.main()
