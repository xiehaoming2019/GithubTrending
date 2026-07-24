from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

from .models import InterestMatch, RepositoryDetails, TrendingRepository


def load_previous_candidate_totals(
    report_date: date,
    *,
    days: int = 7,
    candidate_dir: Path = Path("data/candidates"),
) -> dict[str, int]:
    for offset in range(1, days + 1):
        path = candidate_dir / f"{(report_date - timedelta(days=offset)).isoformat()}.json"
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[warn] Ignoring invalid candidate snapshot {path}: {exc}", file=sys.stderr)
            continue
        if not isinstance(rows, list):
            continue
        totals: dict[str, int] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            repository = row.get("repository")
            if not isinstance(repository, dict):
                continue
            full_name = repository.get("full_name")
            if isinstance(full_name, str) and full_name:
                totals[full_name.lower()] = int(repository.get("total_stars") or 0)
        if totals:
            return totals
    return {}


def apply_ranking_metrics(
    candidates: list[tuple[TrendingRepository, RepositoryDetails]],
    matches: list[InterestMatch],
    *,
    report_date: date,
    previous_totals: dict[str, int],
) -> None:
    matches_by_repository = {
        match.repository.lower(): match for match in matches
    }
    for repo, details in candidates:
        previous_total = previous_totals.get(repo.full_name.lower())
        observed_gain = (
            max(0, repo.total_stars - previous_total)
            if previous_total is not None
            else 0
        )
        repo.star_gain = max(repo.stars_today, observed_gain)

        match = matches_by_repository.get(repo.full_name.lower())
        if match is None:
            continue
        match.velocity_score = _velocity_score(repo.star_gain)
        match.freshness_score = _freshness_score(details.created_at, report_date)
        match.ranking_score = round(
            match.score * 0.50
            + match.velocity_score * 0.25
            + match.freshness_score * 0.15,
            1,
        )


def write_candidate_snapshot(
    report_date: date,
    candidates: list[tuple[TrendingRepository, RepositoryDetails]],
    matches: list[InterestMatch],
    *,
    candidate_dir: Path = Path("data/candidates"),
) -> Path:
    matches_by_repository = {
        match.repository.lower(): match for match in matches
    }
    rows = []
    for repo, details in candidates:
        match = matches_by_repository.get(repo.full_name.lower())
        rows.append(
            {
                "repository": {
                    "full_name": repo.full_name,
                    "source": repo.source,
                    "total_stars": repo.total_stars,
                    "stars_today": repo.stars_today,
                    "star_gain": repo.star_gain,
                },
                "activity": {
                    "created_at": details.created_at,
                    "pushed_at": details.pushed_at,
                },
                **({"interest": asdict(match)} if match is not None else {}),
            }
        )

    candidate_dir.mkdir(parents=True, exist_ok=True)
    path = candidate_dir / f"{report_date.isoformat()}.json"
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _velocity_score(star_gain: int) -> int:
    if star_gain <= 0:
        return 0
    return min(100, round(math.log1p(star_gain) / math.log1p(2_000) * 100))


def _freshness_score(created_at: str, report_date: date) -> int:
    if not created_at:
        return 20
    try:
        created_date = datetime.fromisoformat(
            created_at.replace("Z", "+00:00")
        ).date()
    except ValueError:
        return 20
    age_days = max(0, (report_date - created_date).days)
    if age_days <= 14:
        return 100
    if age_days <= 30:
        return 85
    if age_days <= 90:
        return 70
    if age_days <= 365:
        return 40
    return 20
