from __future__ import annotations

from collections import Counter
from datetime import date
from html import escape

from .models import ProjectBrief, RepositoryDetails, TrendingRepository


def render_markdown(
    report_date: date,
    items: list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
) -> str:
    if not items:
        raise ValueError("Cannot render an empty report")

    categories = Counter(brief.category for _, _, brief in items)
    category_line = " · ".join(f"{name} {count}" for name, count in categories.most_common())
    top = sorted(items, key=lambda item: item[0].stars_today, reverse=True)[:3]
    top_line = "、".join(repo.full_name for repo, _, _ in top)
    ai_count = sum(brief.generated_by_ai for _, _, brief in items)

    lines = [
        f"# GitHub Trending 中文日报 · {report_date.isoformat()}",
        "",
        f"> 今日收录 {len(items)} 个项目；AI 解读 {ai_count} 个。数据来自 GitHub Trending 与公开仓库资料。",
        "",
        "## 今日速览",
        "",
        f"- **热度头条：** {top_line}",
        f"- **分类分布：** {category_line}",
        f"- **今日总新增 Star：** {sum(repo.stars_today for repo, _, _ in items):,}",
        "",
        "## 项目新闻",
        "",
    ]

    for repo, details, brief in items:
        meta = [
            repo.language or "语言未标注",
            f"{repo.total_stars:,} Stars",
            f"今日 +{repo.stars_today:,}",
            f"{repo.forks:,} Forks",
        ]
        if details.license_name:
            meta.append(details.license_name)

        lines.extend(
            [
                f"### {repo.rank}. [{repo.full_name}]({repo.url})",
                "",
                f"**一句话：** {brief.summary}",
                "",
                f"**它解决什么：** {brief.problem}",
                "",
                "**核心特点：**",
                "",
                *[f"- {highlight}" for highlight in brief.highlights],
                "",
                f"**适合谁：** {'、'.join(brief.target_users)}",
                "",
                f"**为什么今天值得关注：** {brief.why_trending}",
                "",
                f"**需要注意：** {brief.caveat}",
                "",
                f"**分类：** {brief.category}",
                "",
                f"**数据：** {' · '.join(meta)}",
                "",
            ]
        )
        if details.homepage:
            lines.extend([f"**项目主页：** {details.homepage}", ""])

    lines.extend(
        [
            "---",
            "",
            "本日报由自动化程序生成。数字来自抓取和 GitHub API；AI 只负责解释性文字。",
            "",
        ]
    )
    return "\n".join(lines)


def render_email_html(
    report_date: date,
    items: list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
) -> str:
    if not items:
        raise ValueError("Cannot render an empty email")

    categories = Counter(brief.category for _, _, brief in items)
    category_line = " · ".join(
        f"{escape(name)} {count}"
        for name, count in categories.most_common()
    )
    top = sorted(items, key=lambda item: item[0].stars_today, reverse=True)[:3]
    top_line = "、".join(escape(repo.full_name) for repo, _, _ in top)
    total_today = sum(repo.stars_today for repo, _, _ in items)

    cards: list[str] = []
    for repo, details, brief in items:
        meta = [
            repo.language or "语言未标注",
            f"{repo.total_stars:,} Stars",
            f"今日 +{repo.stars_today:,}",
            f"{repo.forks:,} Forks",
        ]
        if details.license_name:
            meta.append(details.license_name)

        highlights = "".join(
            (
                '<li style="margin:6px 0;color:#374151;line-height:1.65;">'
                f"{escape(highlight)}</li>"
            )
            for highlight in brief.highlights
        )
        homepage = ""
        if details.homepage:
            safe_homepage = escape(details.homepage, quote=True)
            homepage = (
                '<a style="color:#2563eb;text-decoration:none;margin-left:12px;" '
                f'href="{safe_homepage}">项目主页</a>'
            )

        cards.append(
            f"""
            <section style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;
                            padding:22px;margin:18px 0;">
              <div style="color:#6b7280;font-size:13px;margin-bottom:7px;">
                #{repo.rank} · {escape(brief.category)}
              </div>
              <h2 style="font-size:20px;line-height:1.35;margin:0 0 12px;">
                <a href="{escape(repo.url, quote=True)}"
                   style="color:#111827;text-decoration:none;">{escape(repo.full_name)}</a>
              </h2>
              <p style="color:#111827;font-size:16px;line-height:1.7;margin:0 0 15px;">
                <strong>一句话：</strong>{escape(brief.summary)}
              </p>
              <p style="color:#374151;line-height:1.7;margin:0 0 12px;">
                <strong>它解决什么：</strong>{escape(brief.problem)}
              </p>
              <div style="color:#111827;font-weight:700;margin-top:12px;">核心特点</div>
              <ul style="padding-left:20px;margin:6px 0 14px;">{highlights}</ul>
              <p style="color:#374151;line-height:1.7;margin:8px 0;">
                <strong>适合谁：</strong>{escape("、".join(brief.target_users))}
              </p>
              <p style="color:#374151;line-height:1.7;margin:8px 0;">
                <strong>为何值得关注：</strong>{escape(brief.why_trending)}
              </p>
              <p style="background:#fff7ed;color:#9a3412;border-radius:8px;
                        line-height:1.65;padding:10px 12px;margin:14px 0;">
                <strong>注意：</strong>{escape(brief.caveat)}
              </p>
              <div style="color:#6b7280;font-size:13px;border-top:1px solid #f0f1f3;
                          padding-top:12px;margin-top:14px;">
                {escape(" · ".join(meta))}{homepage}
              </div>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>GitHub Trending 中文日报 · {report_date.isoformat()}</title>
  </head>
  <body style="margin:0;background:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,
               'Segoe UI','PingFang SC','Microsoft YaHei',Arial,sans-serif;color:#111827;">
    <main style="max-width:760px;margin:0 auto;padding:28px 16px 44px;">
      <header style="background:#111827;color:#ffffff;border-radius:16px;padding:28px 24px;">
        <div style="color:#93c5fd;font-size:13px;letter-spacing:.08em;">DAILY OPEN SOURCE</div>
        <h1 style="font-size:28px;line-height:1.3;margin:8px 0 4px;">
          GitHub Trending 中文日报
        </h1>
        <div style="color:#d1d5db;">{report_date.isoformat()} · 今日收录 {len(items)} 个项目</div>
      </header>
      <section style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:14px;
                      padding:18px 20px;margin:18px 0;">
        <p style="margin:0 0 8px;line-height:1.65;"><strong>热度头条：</strong>{top_line}</p>
        <p style="margin:0 0 8px;line-height:1.65;"><strong>分类分布：</strong>{category_line}</p>
        <p style="margin:0;line-height:1.65;"><strong>今日总新增 Star：</strong>{total_today:,}</p>
      </section>
      {"".join(cards)}
      <footer style="color:#6b7280;font-size:12px;line-height:1.6;text-align:center;
                     padding:18px 10px;">
        数字来自 GitHub Trending 与公开仓库资料；AI 只负责解释性文字。
      </footer>
    </main>
  </body>
</html>
"""
