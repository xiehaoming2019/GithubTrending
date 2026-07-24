from __future__ import annotations

import json
import sys
from dataclasses import dataclass, replace
from datetime import date, timedelta
from pathlib import Path

from .models import TrendingRepository


@dataclass(slots=True)
class HistoricalRepository:
    last_seen: date
    appearances: int
    total_stars: int
    stars_today: int


def load_recent_history(
    report_date: date,
    *,
    days: int = 7,
    snapshot_dir: Path = Path("data/snapshots"),
) -> dict[str, HistoricalRepository]:
    history: dict[str, HistoricalRepository] = {}
    for offset in range(days, 0, -1):
        snapshot_date = report_date - timedelta(days=offset)
        path = snapshot_dir / f"{snapshot_date.isoformat()}.json"
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[warn] Ignoring invalid history snapshot {path}: {exc}", file=sys.stderr)
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            repository = row.get("repository")
            if not isinstance(repository, dict):
                continue
            full_name = repository.get("full_name")
            if not isinstance(full_name, str) or not full_name:
                continue
            key = full_name.lower()
            previous = history.get(key)
            history[key] = HistoricalRepository(
                last_seen=snapshot_date,
                appearances=(previous.appearances if previous else 0) + 1,
                total_stars=int(repository.get("total_stars") or 0),
                stars_today=int(repository.get("stars_today") or 0),
            )
    return history


def filter_recent_repeats(
    repositories: list[TrendingRepository],
    history: dict[str, HistoricalRepository],
    *,
    report_date: date,
    trending_repeat_stars: int = 1_500,
    radar_repeat_gain: int = 250,
) -> tuple[list[TrendingRepository], int]:
    selected: list[TrendingRepository] = []
    skipped = 0

    for repo in repositories:
        previous = history.get(repo.full_name.lower())
        if previous is None:
            selected.append(replace(repo, history_label="本周首次收录"))
            continue

        total_gain = max(0, repo.total_stars - previous.total_stars)
        if repo.source == "trending":
            deserves_repeat = repo.stars_today >= trending_repeat_stars
        else:
            deserves_repeat = total_gain >= radar_repeat_gain

        if not deserves_repeat:
            skipped += 1
            continue

        days_since = (report_date - previous.last_seen).days
        label = "连续上榜" if days_since == 1 else "热度再升"
        selected.append(replace(repo, history_label=label))

    return selected, skipped
