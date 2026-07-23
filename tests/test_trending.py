from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from github_trending_daily.models import ProjectBrief, RepositoryDetails
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

        self.assertIn("# GitHub Trending 中文日报 · 2026-07-23", report)
        self.assertIn("[octocat/hello-world]", report)
        self.assertIn("今日 +234", report)
        self.assertIn("MIT", report)

        html = render_email_html(date(2026, 7, 23), [(repo, details, brief)])
        self.assertIn("<!doctype html>", html)
        self.assertIn("https://github.com/octocat/hello-world", html)
        self.assertIn("GitHub Trending 中文日报", html)


if __name__ == "__main__":
    unittest.main()
