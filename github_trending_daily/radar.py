from __future__ import annotations

import sys
from datetime import date, timedelta

from .github_api import GitHubClient
from .models import RepositoryDetails, TrendingRepository


RADAR_TOPICS = (
    "gamedev",
    "game-engine",
    "video-editing",
    "animation",
    "vtuber",
    "generative-art",
    "text-to-speech",
    "music-generation",
    "visual-novel",
    "virtual-production",
)


def fetch_radar_candidates(
    github: GitHubClient,
    report_date: date,
    *,
    limit: int = 18,
    per_topic: int = 3,
    active_days: int = 14,
    minimum_stars: int = 20,
) -> list[tuple[TrendingRepository, RepositoryDetails]]:
    pushed_since = report_date - timedelta(days=active_days)
    by_repository: dict[
        str,
        tuple[TrendingRepository, RepositoryDetails],
    ] = {}

    for topic in RADAR_TOPICS:
        query = (
            f"topic:{topic} pushed:>={pushed_since.isoformat()} "
            f"stars:>={minimum_stars} archived:false"
        )
        try:
            results = github.search_repositories(query, per_page=per_topic)
        except Exception as exc:
            print(f"[warn] ACG radar query failed for {topic}: {exc}", file=sys.stderr)
            continue
        for repo, details in results:
            key = repo.full_name.lower()
            existing = by_repository.get(key)
            if existing is None or repo.total_stars > existing[0].total_stars:
                by_repository[key] = (repo, details)

    candidates = sorted(
        by_repository.values(),
        key=lambda item: (
            item[1].pushed_at,
            item[0].total_stars,
        ),
        reverse=True,
    )
    for rank, (repo, _) in enumerate(candidates, start=1):
        repo.rank = rank
    return candidates[:limit]
