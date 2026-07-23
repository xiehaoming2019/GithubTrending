from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

from .http_client import get_text
from .models import TrendingRepository


GITHUB_ROOT = "https://github.com"


def _classes(attrs: dict[str, str]) -> set[str]:
    return set(attrs.get("class", "").split())


def _number(text: str) -> int:
    match = re.search(r"[\d][\d,]*", text)
    return int(match.group(0).replace(",", "")) if match else 0


class TrendingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.repositories: list[TrendingRepository] = []
        self.current: dict[str, object] | None = None
        self.in_heading = False
        self.capture_key: str | None = None
        self.capture_tag: str | None = None
        self.capture_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        classes = _classes(attrs)

        if tag == "article" and "Box-row" in classes:
            self.current = {}
            return
        if self.current is None:
            return

        if tag == "h2":
            self.in_heading = True
            return

        if tag == "a":
            href = attrs.get("href", "")
            if self.in_heading and re.fullmatch(r"/[^/]+/[^/]+", href):
                self.current["href"] = href
                self._start_capture("full_name", tag)
            elif href.endswith("/stargazers"):
                self._start_capture("total_stars", tag)
            elif href.endswith("/forks"):
                self._start_capture("forks", tag)
            return

        if tag == "p" and "col-9" in classes:
            self._start_capture("description", tag)
        elif tag == "span" and attrs.get("itemprop") == "programmingLanguage":
            self._start_capture("language", tag)
        elif tag == "span" and "float-sm-right" in classes:
            self._start_capture("stars_today", tag)

    def handle_data(self, data: str) -> None:
        if self.capture_key:
            self.capture_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return

        if self.capture_key and tag == self.capture_tag:
            self._finish_capture()

        if tag == "h2":
            self.in_heading = False
        elif tag == "article":
            self._finish_article()

    def _start_capture(self, key: str, tag: str) -> None:
        if self.capture_key is None:
            self.capture_key = key
            self.capture_tag = tag
            self.capture_parts = []

    def _finish_capture(self) -> None:
        if self.current is None or self.capture_key is None:
            return
        text = " ".join("".join(self.capture_parts).split())
        if self.capture_key in {"total_stars", "forks", "stars_today"}:
            self.current[self.capture_key] = _number(text)
        else:
            self.current[self.capture_key] = text
        self.capture_key = None
        self.capture_tag = None
        self.capture_parts = []

    def _finish_article(self) -> None:
        assert self.current is not None
        full_name = str(self.current.get("full_name", "")).replace(" ", "")
        href = str(self.current.get("href", ""))
        if full_name and href:
            self.repositories.append(
                TrendingRepository(
                    rank=len(self.repositories) + 1,
                    full_name=full_name,
                    url=f"{GITHUB_ROOT}{href}",
                    description=str(self.current.get("description", "")),
                    language=str(self.current.get("language", "")),
                    total_stars=int(self.current.get("total_stars", 0)),
                    forks=int(self.current.get("forks", 0)),
                    stars_today=int(self.current.get("stars_today", 0)),
                )
            )
        self.current = None
        self.in_heading = False
        self.capture_key = None
        self.capture_tag = None
        self.capture_parts = []


def parse_trending(html: str) -> list[TrendingRepository]:
    parser = TrendingParser()
    parser.feed(html)
    parser.close()
    return parser.repositories


def trending_url(language: str = "") -> str:
    path = f"/trending/{quote(language.strip().lower())}" if language.strip() else "/trending"
    return f"{GITHUB_ROOT}{path}?since=daily"


def fetch_trending(language: str = "") -> tuple[str, list[TrendingRepository]]:
    html = get_text(trending_url(language))
    repositories = parse_trending(html)
    if not repositories:
        raise RuntimeError("GitHub Trending 页面未解析到项目，页面结构可能已经变化。")
    return html, repositories


def load_trending(path: Path) -> tuple[str, list[TrendingRepository]]:
    html = path.read_text(encoding="utf-8")
    repositories = parse_trending(html)
    if not repositories:
        raise RuntimeError(f"测试 HTML 未解析到项目：{path}")
    return html, repositories

