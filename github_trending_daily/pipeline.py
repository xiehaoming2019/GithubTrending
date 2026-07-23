from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .github_api import GitHubClient
from .models import ProjectBrief, RepositoryDetails, TrendingRepository
from .render import render_markdown
from .summarize import OpenAISummarizer, fallback_brief
from .trending import fetch_trending, load_trending


def run_pipeline(
    *,
    report_date: date,
    limit: int,
    output: Path,
    language: str = "",
    source_html: Path | None = None,
    enrich: bool = True,
    use_ai: bool = True,
) -> Path:
    if source_html:
        html, repositories = load_trending(source_html)
    else:
        html, repositories = fetch_trending(language)
    repositories = repositories[:limit]

    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{report_date.isoformat()}.html").write_text(html, encoding="utf-8")

    github = GitHubClient()
    summarizer = OpenAISummarizer()
    items: list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]] = []
    cached_details, cached_briefs = _load_cached_snapshot(report_date)
    enrichment_available = enrich
    ai_available = use_ai and summarizer.enabled

    for repo in repositories:
        details = RepositoryDetails()
        if enrichment_available:
            try:
                details = github.repository_details(repo.full_name)
            except Exception as exc:  # Keep the daily edition publishable.
                print(f"[warn] GitHub enrichment failed for {repo.full_name}: {exc}", file=sys.stderr)
                details = cached_details.get(repo.full_name, RepositoryDetails())
                if "rate limit" in str(exc).lower():
                    enrichment_available = False
        elif enrich:
            details = cached_details.get(repo.full_name, RepositoryDetails())

        if ai_available:
            try:
                brief = summarizer.summarize(repo, details)
            except Exception as exc:  # Publish deterministic copy if the model is unavailable.
                print(f"[warn] AI summary failed for {repo.full_name}: {exc}", file=sys.stderr)
                brief = cached_briefs.get(repo.full_name) or fallback_brief(repo, details)
                ai_available = False
        else:
            brief = fallback_brief(repo, details)
        items.append((repo, details, brief))

    snapshot_dir = Path("data/snapshots")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot = [
        {
            "repository": asdict(repo),
            "details": asdict(details),
            "brief": asdict(brief),
        }
        for repo, details, brief in items
    ]
    (snapshot_dir / f"{report_date.isoformat()}.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(report_date, items), encoding="utf-8")
    return output


def _load_cached_snapshot(
    report_date: date,
) -> tuple[dict[str, RepositoryDetails], dict[str, ProjectBrief]]:
    path = Path("data/snapshots") / f"{report_date.isoformat()}.json"
    if not path.exists():
        return {}, {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        details = {
            row["repository"]["full_name"]: RepositoryDetails(**row["details"])
            for row in rows
        }
        briefs = {
            row["repository"]["full_name"]: ProjectBrief(**row["brief"])
            for row in rows
            if row.get("brief", {}).get("generated_by_ai")
        }
        return details, briefs
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"[warn] Ignoring invalid cached snapshot {path}: {exc}", file=sys.stderr)
        return {}, {}
