from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .email_delivery import (
    EmailSettings,
    build_failure_message,
    send_message,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a failure alert for the GitHub Trending daily workflow.",
    )
    parser.add_argument("--date", help="report date in YYYY-MM-DD")
    parser.add_argument(
        "--message",
        default="GitHub Actions 日报流程未完成，请查看失败步骤。",
        help="short failure context without secrets",
    )
    parser.add_argument("--run-url", default="", help="GitHub Actions run URL")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="build the alert without connecting to SMTP",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report_date = (
        date.fromisoformat(args.date)
        if args.date
        else datetime.now(ZoneInfo("Asia/Shanghai")).date()
    )
    settings = EmailSettings.alert_from_env()
    if settings is None:
        print(
            "[info] Failure alert skipped: QQ SMTP credentials are not configured.",
            file=sys.stderr,
        )
        return 0

    run_url = args.run_url or _actions_run_url()
    message = build_failure_message(
        settings=settings,
        report_date=report_date,
        failure_context=args.message,
        run_url=run_url,
    )
    if args.dry_run:
        print(f"Failure alert ready for {len(settings.recipients)} recipient(s).")
        return 0

    try:
        send_message(settings, message)
    except Exception as exc:
        print(f"[warn] Failure alert could not be sent: {exc}", file=sys.stderr)
        return 1
    print(f"Sent failure alert to {len(settings.recipients)} recipient(s).")
    return 0


def _actions_run_url() -> str:
    server = os.getenv("GITHUB_SERVER_URL", "")
    repository = os.getenv("GITHUB_REPOSITORY", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    if not server or not repository or not run_id:
        return ""
    return f"{server.rstrip('/')}/{repository}/actions/runs/{run_id}"


if __name__ == "__main__":
    raise SystemExit(main())
