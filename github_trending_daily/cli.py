from __future__ import annotations

import argparse
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Chinese daily newsletter from GitHub Trending.",
    )
    parser.add_argument("--limit", type=int, default=10, help="maximum report repositories")
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=int(os.getenv("TRENDING_CANDIDATE_LIMIT", "25")),
        help="Trending candidates inspected before interest filtering",
    )
    parser.add_argument(
        "--relevance-threshold",
        type=int,
        default=int(os.getenv("ACG_RELEVANCE_THRESHOLD", "60")),
        help="minimum ACG/creator relevance score, from 0 to 100",
    )
    parser.add_argument("--language", default="", help="programming language filter")
    parser.add_argument("--date", help="report date in YYYY-MM-DD")
    parser.add_argument("--output", type=Path, help="Markdown output path")
    parser.add_argument("--source-html", type=Path, help="parse a local HTML fixture")
    parser.add_argument("--no-enrich", action="store_true", help="skip GitHub REST API")
    parser.add_argument("--no-ai", action="store_true", help="skip AI summaries")
    parser.add_argument(
        "--no-interest-filter",
        action="store_true",
        help="disable ACG/creator relevance filtering",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="send the report when QQ/SMTP credentials are configured",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")
    if args.candidate_limit < 1:
        raise SystemExit("--candidate-limit must be at least 1")
    if not 0 <= args.relevance_threshold <= 100:
        raise SystemExit("--relevance-threshold must be between 0 and 100")

    report_date = (
        date.fromisoformat(args.date)
        if args.date
        else datetime.now(ZoneInfo("Asia/Shanghai")).date()
    )
    output = args.output or Path("reports") / f"{report_date.isoformat()}.md"
    result = run_pipeline(
        report_date=report_date,
        limit=args.limit,
        output=output,
        language=args.language,
        source_html=args.source_html,
        enrich=not args.no_enrich,
        use_ai=not args.no_ai,
        deliver_email=args.send_email,
        filter_interests=not args.no_interest_filter,
        relevance_threshold=args.relevance_threshold,
        candidate_limit=args.candidate_limit,
    )
    print(f"Generated {result}")
    return 0
