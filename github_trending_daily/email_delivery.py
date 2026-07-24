from __future__ import annotations

import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import date
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import getaddresses


@dataclass(frozen=True, slots=True)
class EmailSettings:
    host: str
    port: int
    username: str
    authorization_code: str
    recipients: tuple[str, ...]
    sender_name: str = "GitHub Trending ACG 日报"

    @classmethod
    def from_env(cls) -> EmailSettings | None:
        username = os.getenv("QQ_EMAIL") or os.getenv("SMTP_USERNAME", "")
        authorization_code = os.getenv("QQ_SMTP_AUTH_CODE") or os.getenv(
            "SMTP_PASSWORD",
            "",
        )
        if not username or not authorization_code:
            return None
        if "@" not in username:
            raise ValueError("QQ_EMAIL/SMTP_USERNAME 必须是完整邮箱地址")

        recipient_text = os.getenv("EMAIL_TO", "") or username
        recipients = tuple(
            address
            for _, address in getaddresses([recipient_text])
            if address and "@" in address
        )
        if not recipients:
            raise ValueError("EMAIL_TO 未包含有效的收件邮箱地址")

        try:
            port = int(os.getenv("SMTP_PORT", "465"))
        except ValueError as exc:
            raise ValueError("SMTP_PORT 必须是整数") from exc

        return cls(
            host=os.getenv("SMTP_HOST", "smtp.qq.com"),
            port=port,
            username=username,
            authorization_code=authorization_code,
            recipients=recipients,
            sender_name=os.getenv("EMAIL_SENDER_NAME", "GitHub Trending ACG 日报"),
        )


def build_message(
    *,
    settings: EmailSettings,
    report_date: date,
    repository_count: int,
    markdown: str,
    html: str,
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = (
        f"GitHub Trending ACG 日报 · {report_date.isoformat()} · "
        f"{repository_count} 个项目"
    )
    message["From"] = Address(
        display_name=settings.sender_name,
        addr_spec=settings.username,
    )
    message["To"] = ", ".join(settings.recipients)
    message.set_content(markdown)
    message.add_alternative(html, subtype="html")
    return message


def send_message(settings: EmailSettings, message: EmailMessage) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(
        settings.host,
        settings.port,
        timeout=30,
        context=context,
    ) as smtp:
        smtp.login(settings.username, settings.authorization_code)
        smtp.send_message(message)
