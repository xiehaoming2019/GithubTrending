from __future__ import annotations

import json
import sys
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path

from .email_delivery import EmailSettings, build_message, send_message
from .github_api import GitHubClient
from .history import filter_recent_repeats, load_recent_history
from .interest import (
    OpenAIInterestClassifier,
    fallback_interest,
    select_daily_mix,
)
from .models import InterestMatch, ProjectBrief, RepositoryDetails, TrendingRepository
from .radar import fetch_radar_candidates
from .render import render_email_html, render_markdown
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
    deliver_email: bool = False,
    filter_interests: bool = True,
    relevance_threshold: int = 60,
    candidate_limit: int = 25,
    use_radar: bool = True,
    radar_candidate_limit: int = 18,
    radar_limit: int = 3,
    deduplicate: bool = True,
    history_days: int = 7,
) -> Path:
    if source_html:
        html, repositories = load_trending(source_html)
    else:
        html, repositories = fetch_trending(language)
    pool_size = max(limit, candidate_limit) if filter_interests else limit
    trending_repositories = repositories[:pool_size]

    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{report_date.isoformat()}.html").write_text(html, encoding="utf-8")

    github = GitHubClient()
    summarizer = OpenAISummarizer()
    cached_repositories, cached_details, cached_briefs = _load_cached_snapshot(report_date)
    history = (
        load_recent_history(report_date, days=history_days)
        if filter_interests and deduplicate
        else {}
    )
    if history:
        trending_repositories, skipped = filter_recent_repeats(
            trending_repositories,
            history,
            report_date=report_date,
        )
        if skipped:
            print(
                f"Skipped {skipped} Trending project(s) seen in the last "
                f"{history_days} days.",
                file=sys.stderr,
            )

    radar_details_by_repository: dict[str, RepositoryDetails] = {}
    radar_repositories: list[TrendingRepository] = []
    if filter_interests and use_radar and source_html is None and enrich:
        try:
            radar_candidates = fetch_radar_candidates(
                github,
                report_date,
                limit=radar_candidate_limit,
            )
        except Exception as exc:
            print(f"[warn] ACG radar failed: {exc}", file=sys.stderr)
            radar_candidates = []

        trending_names = {
            repo.full_name.lower() for repo in repositories[:pool_size]
        }
        radar_candidates = [
            (repo, details)
            for repo, details in radar_candidates
            if repo.full_name.lower() not in trending_names
        ]
        if history:
            filtered_radar, skipped = filter_recent_repeats(
                [repo for repo, _ in radar_candidates],
                history,
                report_date=report_date,
            )
            allowed_names = {repo.full_name.lower() for repo in filtered_radar}
            radar_candidates = [
                (repo, details)
                for repo, details in radar_candidates
                if repo.full_name.lower() in allowed_names
            ]
            filtered_by_name = {
                repo.full_name.lower(): repo for repo in filtered_radar
            }
            radar_candidates = [
                (filtered_by_name[repo.full_name.lower()], details)
                for repo, details in radar_candidates
            ]
            if skipped:
                print(
                    f"Skipped {skipped} ACG radar project(s) seen in the last "
                    f"{history_days} days.",
                    file=sys.stderr,
                )
        radar_repositories = [repo for repo, _ in radar_candidates]
        radar_details_by_repository = {
            repo.full_name: details for repo, details in radar_candidates
        }

    enrichment_available = enrich
    candidate_details: list[tuple[TrendingRepository, RepositoryDetails]] = []

    for repo in trending_repositories:
        details = RepositoryDetails()
        if enrichment_available:
            try:
                details = github.repository_details(repo.full_name)
            except Exception as exc:  # Keep the daily edition publishable.
                print(
                    f"[warn] GitHub enrichment failed for {repo.full_name}: {exc}",
                    file=sys.stderr,
                )
                details = cached_details.get(repo.full_name, RepositoryDetails())
                if "rate limit" in str(exc).lower():
                    enrichment_available = False
        elif enrich:
            details = cached_details.get(repo.full_name, RepositoryDetails())
        candidate_details.append((repo, details))

    candidate_details.extend(
        (repo, radar_details_by_repository[repo.full_name])
        for repo in radar_repositories
    )

    matches: list[InterestMatch] = []
    if filter_interests:
        classifier = OpenAIInterestClassifier()
        if use_ai and classifier.enabled:
            try:
                matches = classifier.classify(candidate_details)
            except Exception as exc:
                print(
                    f"[warn] AI interest filter failed; using local rules: {exc}",
                    file=sys.stderr,
                )
        if not matches:
            matches = [
                fallback_interest(repo, details)
                for repo, details in candidate_details
            ]
        repositories = select_daily_mix(
            trending_repositories,
            radar_repositories,
            matches,
            limit=limit,
            threshold=relevance_threshold,
            radar_target=radar_limit,
        )
        print(
            f"Selected {len(repositories)} of {len(candidate_details)} candidates "
            f"at relevance >= {relevance_threshold}.",
            file=sys.stderr,
        )
    else:
        repositories = trending_repositories[:limit]

    details_by_repository = {
        repo.full_name: details for repo, details in candidate_details
    }
    if enrich and enrichment_available:
        for repo in repositories:
            if repo.source != "radar":
                continue
            try:
                details_by_repository[repo.full_name] = github.repository_details(
                    repo.full_name
                )
            except Exception as exc:
                print(
                    f"[warn] GitHub radar enrichment failed for {repo.full_name}: {exc}",
                    file=sys.stderr,
                )
                if "rate limit" in str(exc).lower():
                    enrichment_available = False
                    break
    matches_by_repository = {
        match.repository.lower(): match for match in matches
    }
    ai_available = use_ai and summarizer.enabled
    items: list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]] = []
    selected_matches: dict[str, InterestMatch] = {}

    for repo in repositories:
        details = details_by_repository.get(repo.full_name, RepositoryDetails())
        cached_repo = cached_repositories.get(repo.full_name)
        cached_brief = cached_briefs.get(repo.full_name)
        can_reuse_ai = (
            cached_repo is not None
            and cached_brief is not None
            and cached_repo.description == repo.description
            and cached_repo.stars_today == repo.stars_today
        )

        if ai_available and can_reuse_ai:
            brief = cached_brief
        elif ai_available:
            try:
                brief = summarizer.summarize(repo, details)
            except Exception as exc:  # Publish deterministic copy if the model is unavailable.
                print(f"[warn] AI summary failed for {repo.full_name}: {exc}", file=sys.stderr)
                brief = cached_brief or fallback_brief(repo, details)
                ai_available = False
        else:
            brief = fallback_brief(repo, details)

        interest_match = matches_by_repository.get(repo.full_name.lower())
        if interest_match is not None:
            brief = replace(brief, category=interest_match.category)
            selected_matches[repo.full_name] = interest_match
        items.append((repo, details, brief))

    snapshot_dir = Path("data/snapshots")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot = [
        {
            "repository": asdict(repo),
            "details": asdict(details),
            "brief": asdict(brief),
            **(
                {"interest": asdict(selected_matches[repo.full_name])}
                if repo.full_name in selected_matches
                else {}
            ),
        }
        for repo, details, brief in items
    ]
    (snapshot_dir / f"{report_date.isoformat()}.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    markdown = render_markdown(report_date, items)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")

    if deliver_email:
        email_settings = EmailSettings.from_env()
        if email_settings is None:
            print(
                "[info] Email delivery skipped: QQ_EMAIL or QQ_SMTP_AUTH_CODE is not configured.",
                file=sys.stderr,
            )
        else:
            message = build_message(
                settings=email_settings,
                report_date=report_date,
                repository_count=len(items),
                markdown=markdown,
                html=render_email_html(report_date, items),
            )
            send_message(email_settings, message)
            print(
                f"Sent daily report to {len(email_settings.recipients)} recipient(s)."
            )
    return output


def _load_cached_snapshot(
    report_date: date,
) -> tuple[
    dict[str, TrendingRepository],
    dict[str, RepositoryDetails],
    dict[str, ProjectBrief],
]:
    path = Path("data/snapshots") / f"{report_date.isoformat()}.json"
    if not path.exists():
        return {}, {}, {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        repositories = {
            row["repository"]["full_name"]: TrendingRepository(**row["repository"])
            for row in rows
        }
        details = {
            row["repository"]["full_name"]: RepositoryDetails(**row["details"])
            for row in rows
        }
        briefs = {
            row["repository"]["full_name"]: ProjectBrief(**row["brief"])
            for row in rows
            if row.get("brief", {}).get("generated_by_ai")
        }
        return repositories, details, briefs
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"[warn] Ignoring invalid cached snapshot {path}: {exc}", file=sys.stderr)
        return {}, {}, {}
