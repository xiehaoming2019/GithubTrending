from __future__ import annotations

import os
import unittest
from datetime import date
from unittest.mock import patch

from github_trending_daily.email_delivery import (
    EmailSettings,
    build_failure_message,
    build_message,
)


class EmailDeliveryTests(unittest.TestCase):
    def test_returns_none_without_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(EmailSettings.from_env())

    def test_loads_qq_settings_and_recipients(self) -> None:
        environment = {
            "QQ_EMAIL": "sender@qq.com",
            "QQ_SMTP_AUTH_CODE": "authorization-code",
            "EMAIL_TO": "first@example.com, second@example.com",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = EmailSettings.from_env()

        assert settings is not None
        self.assertEqual("smtp.qq.com", settings.host)
        self.assertEqual(465, settings.port)
        self.assertEqual(
            ("first@example.com", "second@example.com"),
            settings.recipients,
        )

    def test_builds_plain_text_and_html_message(self) -> None:
        settings = EmailSettings(
            host="smtp.qq.com",
            port=465,
            username="sender@qq.com",
            authorization_code="secret",
            recipients=("receiver@qq.com",),
        )
        message = build_message(
            settings=settings,
            report_date=date(2026, 7, 24),
            repository_count=10,
            markdown="# Daily",
            html="<h1>Daily</h1>",
        )

        self.assertIn("2026-07-24", str(message["Subject"]))
        self.assertIn("ACG 日报", str(message["Subject"]))
        self.assertEqual("receiver@qq.com", str(message["To"]))
        self.assertTrue(message.is_multipart())
        self.assertEqual(2, len(message.get_payload()))

    def test_alert_defaults_to_sender_not_daily_friends(self) -> None:
        environment = {
            "QQ_EMAIL": "sender@qq.com",
            "QQ_SMTP_AUTH_CODE": "authorization-code",
            "EMAIL_TO": "friend@example.com",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = EmailSettings.alert_from_env()

        assert settings is not None
        self.assertEqual(("sender@qq.com",), settings.recipients)

    def test_alert_can_use_separate_recipient(self) -> None:
        environment = {
            "QQ_EMAIL": "sender@qq.com",
            "QQ_SMTP_AUTH_CODE": "authorization-code",
            "EMAIL_TO": "friend@example.com",
            "ALERT_EMAIL_TO": "owner@example.com",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = EmailSettings.alert_from_env()

        assert settings is not None
        self.assertEqual(("owner@example.com",), settings.recipients)

    def test_builds_failure_alert_with_actions_link(self) -> None:
        settings = EmailSettings(
            host="smtp.qq.com",
            port=465,
            username="sender@qq.com",
            authorization_code="secret",
            recipients=("sender@qq.com",),
        )
        message = build_failure_message(
            settings=settings,
            report_date=date(2026, 7, 24),
            failure_context="日报流程未完成",
            run_url="https://github.com/example/repo/actions/runs/123",
        )

        self.assertIn("失败告警", str(message["Subject"]))
        self.assertEqual("sender@qq.com", str(message["To"]))
        self.assertIn(
            "https://github.com/example/repo/actions/runs/123",
            message.get_body(preferencelist=("plain",)).get_content(),
        )


if __name__ == "__main__":
    unittest.main()
