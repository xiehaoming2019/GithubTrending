from __future__ import annotations

import os
import unittest
from datetime import date
from unittest.mock import patch

from github_trending_daily.email_delivery import (
    EmailSettings,
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
        self.assertEqual("receiver@qq.com", str(message["To"]))
        self.assertTrue(message.is_multipart())
        self.assertEqual(2, len(message.get_payload()))


if __name__ == "__main__":
    unittest.main()
