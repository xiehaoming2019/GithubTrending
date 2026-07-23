from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Chinese daily newsletter from GitHub Trending.",
    )
    parser.add_argument("--limit", type=int, default=10, help="number of repositories")
    parser.add_argument("--language", default="", help="programming language filter")
    parser.add_argument("--date", help="report date in YYYY-MM-DD")
    parser.add_argument("--output", type=Path, help="Markdown output path")
    parser.add_argument("--source-html", type=Path, help="parse a local HTML fixture")
    parser.add_argument("--no-enrich", action="store_true", help="skip GitHub REST API")
    parser.add_argument("--no-ai", action="store_true", help="skip AI summaries")
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
    )
    print(f"Generated {result}")
    return 0
