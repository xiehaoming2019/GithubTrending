from __future__ import annotations

import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import date
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import getaddresses
from html import escape


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
        return cls._from_env("EMAIL_TO", "GitHub Trending ACG 日报")

    @classmethod
    def alert_from_env(cls) -> EmailSettings | None:
        return cls._from_env("ALERT_EMAIL_TO", "GitHub Trending ACG 告警")

    @classmethod
    def _from_env(
        cls,
        recipient_variable: str,
        default_sender_name: str,
    ) -> EmailSettings | None:
        username = os.getenv("QQ_EMAIL") or os.getenv("SMTP_USERNAME", "")
        authorization_code = os.getenv("QQ_SMTP_AUTH_CODE") or os.getenv(
            "SMTP_PASSWORD",
            "",
        )
        if not username or not authorization_code:
            return None
        if "@" not in username:
            raise ValueError("QQ_EMAIL/SMTP_USERNAME 必须是完整邮箱地址")

        recipient_text = os.getenv(recipient_variable, "") or username
        recipients = tuple(
            address
            for _, address in getaddresses([recipient_text])
            if address and "@" in address
        )
        if not recipients:
            raise ValueError(f"{recipient_variable} 未包含有效的收件邮箱地址")

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
            sender_name=os.getenv("EMAIL_SENDER_NAME", default_sender_name),
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


def build_failure_message(
    *,
    settings: EmailSettings,
    report_date: date,
    failure_context: str,
    run_url: str = "",
) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = (
        f"[失败告警] GitHub Trending ACG 日报 · {report_date.isoformat()}"
    )
    message["From"] = Address(
        display_name=settings.sender_name,
        addr_spec=settings.username,
    )
    message["To"] = ", ".join(settings.recipients)

    run_line = f"\n运行详情：{run_url}" if run_url else ""
    plain = (
        f"GitHub Trending ACG 日报任务未完成。\n\n"
        f"日期：{report_date.isoformat()}\n"
        f"说明：{failure_context}{run_line}\n\n"
        "请打开 GitHub Actions 查看失败步骤和日志。"
    )
    run_html = (
        f'<p><a href="{escape(run_url, quote=True)}">打开 GitHub Actions 运行详情</a></p>'
        if run_url
        else ""
    )
    html = f"""<!doctype html>
<html lang="zh-CN">
  <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',
               'PingFang SC','Microsoft YaHei',Arial,sans-serif;color:#111827;">
    <main style="max-width:640px;margin:24px auto;padding:22px;
                 border:1px solid #fecaca;border-radius:14px;background:#fff7f7;">
      <h1 style="font-size:22px;color:#b91c1c;margin-top:0;">日报任务失败</h1>
      <p><strong>日期：</strong>{report_date.isoformat()}</p>
      <p style="line-height:1.7;">{escape(failure_context)}</p>
      {run_html}
      <p style="color:#6b7280;font-size:13px;">请检查失败步骤和日志后再重新运行。</p>
    </main>
  </body>
</html>
"""
    message.set_content(plain)
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
