from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from github_trending_daily.failure_alert import _actions_run_url, main


class FailureAlertCliTests(unittest.TestCase):
    def test_builds_actions_run_url(self) -> None:
        environment = {
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_REPOSITORY": "example/repo",
            "GITHUB_RUN_ID": "123",
        }
        with patch.dict(os.environ, environment, clear=True):
            url = _actions_run_url()

        self.assertEqual(
            "https://github.com/example/repo/actions/runs/123",
            url,
        )

    def test_dry_run_does_not_connect_to_smtp(self) -> None:
        environment = {
            "QQ_EMAIL": "sender@qq.com",
            "QQ_SMTP_AUTH_CODE": "authorization-code",
        }
        output = io.StringIO()
        with (
            patch.dict(os.environ, environment, clear=True),
            patch(
                "github_trending_daily.failure_alert.send_message"
            ) as send_message_mock,
            redirect_stdout(output),
        ):
            result = main(["--date", "2026-07-24", "--dry-run"])

        self.assertEqual(0, result)
        self.assertIn("Failure alert ready", output.getvalue())
        send_message_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
