from __future__ import annotations

import os
from urllib.parse import quote, urlencode

from .http_client import HttpError, get_json, get_text
from .models import RepositoryDetails, TrendingRepository


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN", "")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def repository_details(self, full_name: str) -> RepositoryDetails:
        safe_name = "/".join(quote(part, safe="") for part in full_name.split("/", 1))
        data = get_json(
            f"https://api.github.com/repos/{safe_name}",
            headers=self.headers,
        )
        readme = self._readme(safe_name)
        license_data = data.get("license") or {}
        license_name = str(license_data.get("spdx_id") or license_data.get("name") or "")
        if license_name.upper() in {"NOASSERTION", "OTHER"}:
            license_name = ""
        return RepositoryDetails(
            topics=[str(topic) for topic in data.get("topics", [])],
            license_name=license_name,
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            pushed_at=str(data.get("pushed_at") or ""),
            open_issues=int(data.get("open_issues_count") or 0),
            homepage=str(data.get("homepage") or ""),
            archived=bool(data.get("archived")),
            default_branch=str(data.get("default_branch") or ""),
            readme=readme,
        )

    def search_repositories(
        self,
        query: str,
        *,
        per_page: int = 3,
    ) -> list[tuple[TrendingRepository, RepositoryDetails]]:
        parameters = urlencode(
            {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": max(1, min(100, per_page)),
            }
        )
        data = get_json(
            f"https://api.github.com/search/repositories?{parameters}",
            headers=self.headers,
        )
        results: list[tuple[TrendingRepository, RepositoryDetails]] = []
        for index, item in enumerate(data.get("items", []), start=1):
            if not isinstance(item, dict):
                continue
            full_name = str(item.get("full_name") or "")
            url = str(item.get("html_url") or "")
            if not full_name or not url or item.get("archived"):
                continue
            license_data = item.get("license") or {}
            license_name = str(
                license_data.get("spdx_id") or license_data.get("name") or ""
            )
            if license_name.upper() in {"NOASSERTION", "OTHER"}:
                license_name = ""
            results.append(
                (
                    TrendingRepository(
                        rank=index,
                        full_name=full_name,
                        url=url,
                        description=str(item.get("description") or ""),
                        language=str(item.get("language") or ""),
                        total_stars=int(item.get("stargazers_count") or 0),
                        forks=int(item.get("forks_count") or 0),
                        stars_today=0,
                        source="radar",
                    ),
                    RepositoryDetails(
                        topics=[
                            str(topic)
                            for topic in item.get("topics", [])
                            if isinstance(topic, str)
                        ],
                        license_name=license_name,
                        created_at=str(item.get("created_at") or ""),
                        updated_at=str(item.get("updated_at") or ""),
                        pushed_at=str(item.get("pushed_at") or ""),
                        open_issues=int(item.get("open_issues_count") or 0),
                        homepage=str(item.get("homepage") or ""),
                        archived=bool(item.get("archived")),
                        default_branch=str(item.get("default_branch") or ""),
                    ),
                )
            )
        return results

    def _readme(self, safe_name: str) -> str:
        headers = {
            **self.headers,
            "Accept": "application/vnd.github.raw+json",
        }
        try:
            text = get_text(
                f"https://api.github.com/repos/{safe_name}/readme",
                headers=headers,
            )
        except HttpError as exc:
            if "HTTP 404" in str(exc):
                return ""
            raise
        return text[:12_000]
