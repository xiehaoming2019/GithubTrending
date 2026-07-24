from __future__ import annotations

from collections import Counter
from datetime import date
from html import escape

from .models import ProjectBrief, RepositoryDetails, TrendingRepository


FEATURED_COUNT = 3


def _compact(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"


def _compact_fragment(text: str, limit: int) -> str:
    return _compact(text.rstrip("。；;，, "), limit)


def _split_items(
    items: list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
) -> tuple[
    list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
    list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
]:
    ranked = sorted(
        items,
        key=lambda item: item[0].stars_today,
        reverse=True,
    )
    featured: list[
        tuple[TrendingRepository, RepositoryDetails, ProjectBrief]
    ] = []
    featured_categories: set[str] = set()
    for item in ranked:
        category = item[2].category
        if category not in featured_categories:
            featured.append(item)
            featured_categories.add(category)
        if len(featured) == FEATURED_COUNT:
            break

    featured_names = {repo.full_name for repo, _, _ in featured}
    for item in ranked:
        if len(featured) == FEATURED_COUNT:
            break
        if item[0].full_name not in featured_names:
            featured.append(item)
            featured_names.add(item[0].full_name)

    featured_names = {repo.full_name for repo, _, _ in featured}
    remaining = [
        item
        for item in items
        if item[0].full_name not in featured_names
    ]
    return featured, remaining


def render_markdown(
    report_date: date,
    items: list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
) -> str:
    if not items:
        return "\n".join(
            [
                f"# GitHub Trending ACG 日报 · {report_date.isoformat()}",
                "",
                "> 今日没有项目达到 ACG / 创作者工具相关性标准",
                "",
                "## 今天不硬凑",
                "",
                "今天的 Trending 中，没有发现足够相关的 AI Agent、游戏、动画、",
                "视频、绘画、3D、语音或其他 ACG 创作项目。",
                "",
                "宁可少发，也不拿通用框架、数据库、金融或炒币项目凑数。",
                "",
                "---",
                "",
                "项目来自 GitHub Trending；相关性由 AI 与本地规则共同筛选。",
                "",
            ]
        )

    categories = Counter(brief.category for _, _, brief in items)
    dominant_category, dominant_count = categories.most_common(1)[0]
    featured, remaining = _split_items(items)
    hottest = featured[0][0]

    lines = [
        f"# GitHub Trending ACG 日报 · {report_date.isoformat()}",
        "",
        f"> 约 3 分钟读完 · 今日收录 {len(items)} 个项目",
        "",
        "## 今天先知道",
        "",
        f"- **主线：** {dominant_category} 项目最多，占 {dominant_count}/{len(items)}",
        f"- **最热：** [{hottest.full_name}]({hottest.url})，今日 +{hottest.stars_today:,} Stars",
        "",
        f"## 今天只看这 {len(featured)} 个",
        "",
    ]

    for index, (repo, _, brief) in enumerate(featured, start=1):
        highlight = _compact_fragment(brief.highlights[0], 55)
        lines.extend(
            [
                f"### {index}. [{repo.full_name}]({repo.url}) · "
                f"{brief.category} · 今日 +{repo.stars_today:,}",
                "",
                _compact(brief.summary, 65),
                "",
                f"- **亮点：** {highlight}",
                f"- **提醒：** {_compact(brief.caveat, 60)}",
                "",
            ]
        )

    if remaining:
        lines.extend(
            [
                "## 其余项目，一句话扫完",
                "",
            ]
        )
        for repo, _, brief in remaining:
            language = repo.language or "未标注语言"
            lines.append(
                f"- **[{repo.full_name}]({repo.url})** · {brief.category} — "
                f"{_compact(brief.summary, 70)} "
                f"`{language} · 今日 +{repo.stars_today:,}`"
            )
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "项目来自 GitHub Trending；相关性与简介由 AI 基于公开资料整理。",
            "",
        ]
    )
    return "\n".join(lines)


def render_email_html(
    report_date: date,
    items: list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
) -> str:
    if not items:
        return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>GitHub Trending ACG 日报 · {report_date.isoformat()}</title>
  </head>
  <body style="margin:0;background:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,
               'Segoe UI','PingFang SC','Microsoft YaHei',Arial,sans-serif;color:#111827;">
    <main style="max-width:680px;margin:0 auto;padding:24px 14px 40px;">
      <header style="background:#111827;color:#ffffff;border-radius:16px;padding:24px 22px;">
        <div style="color:#93c5fd;font-size:13px;letter-spacing:.08em;">ACG OPEN SOURCE DAILY</div>
        <h1 style="font-size:25px;line-height:1.3;margin:7px 0 4px;">
          GitHub Trending ACG 日报
        </h1>
        <div style="color:#d1d5db;">{report_date.isoformat()}</div>
      </header>
      <section style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;
                      padding:20px;margin:16px 0;">
        <h2 style="font-size:18px;margin:0 0 10px;">今天不硬凑</h2>
        <p style="color:#4b5563;font-size:15px;line-height:1.7;margin:0;">
          今天没有项目达到 ACG / 创作者工具相关性标准。宁可少发，
          也不拿通用框架、数据库、金融或炒币项目凑数。
        </p>
      </section>
    </main>
  </body>
</html>
"""

    categories = Counter(brief.category for _, _, brief in items)
    dominant_category, dominant_count = categories.most_common(1)[0]
    featured, remaining = _split_items(items)
    hottest = featured[0][0]

    cards: list[str] = []
    for index, (repo, _, brief) in enumerate(featured, start=1):
        highlight = _compact_fragment(brief.highlights[0], 55)

        cards.append(
            f"""
            <section style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;
                            padding:18px 20px;margin:14px 0;">
              <div style="color:#6b7280;font-size:12px;margin-bottom:6px;">
                重点 {index} · {escape(brief.category)}
              </div>
              <h2 style="font-size:19px;line-height:1.35;margin:0 0 9px;">
                <a href="{escape(repo.url, quote=True)}"
                   style="color:#111827;text-decoration:none;">{escape(repo.full_name)}</a>
                <span style="color:#dc2626;font-size:13px;font-weight:500;margin-left:8px;">
                  今日 +{repo.stars_today:,}
                </span>
              </h2>
              <p style="color:#111827;font-size:15px;line-height:1.65;margin:0 0 10px;">
                {escape(_compact(brief.summary, 65))}
              </p>
              <p style="color:#374151;font-size:13px;line-height:1.55;margin:7px 0;">
                <strong>亮点：</strong>{escape(highlight)}
              </p>
              <p style="color:#9a3412;font-size:13px;line-height:1.55;margin:7px 0 0;">
                <strong>提醒：</strong>{escape(_compact(brief.caveat, 60))}
              </p>
            </section>
            """
        )

    quick_items = "".join(
        f"""
        <div style="padding:12px 0;border-bottom:1px solid #f0f1f3;">
          <a href="{escape(repo.url, quote=True)}"
             style="color:#111827;font-weight:700;text-decoration:none;">
            {escape(repo.full_name)}
          </a>
          <span style="color:#6b7280;font-size:12px;margin-left:6px;">
            {escape(brief.category)} · {escape(repo.language or "未标注语言")}
            · 今日 +{repo.stars_today:,}
          </span>
          <div style="color:#4b5563;font-size:14px;line-height:1.55;margin-top:4px;">
            {escape(_compact(brief.summary, 70))}
          </div>
        </div>
        """
        for repo, _, brief in remaining
    )
    quick_section = ""
    if remaining:
        quick_section = f"""
        <section style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;
                        padding:6px 18px 4px;margin:20px 0;">
          <h2 style="font-size:18px;margin:14px 0 4px;">其余项目，一句话扫完</h2>
          {quick_items}
        </section>
        """

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>GitHub Trending ACG 日报 · {report_date.isoformat()}</title>
  </head>
  <body style="margin:0;background:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,
               'Segoe UI','PingFang SC','Microsoft YaHei',Arial,sans-serif;color:#111827;">
    <main style="max-width:680px;margin:0 auto;padding:24px 14px 40px;">
      <header style="background:#111827;color:#ffffff;border-radius:16px;padding:24px 22px;">
        <div style="color:#93c5fd;font-size:13px;letter-spacing:.08em;">ACG OPEN SOURCE DAILY</div>
        <h1 style="font-size:25px;line-height:1.3;margin:7px 0 4px;">
          GitHub Trending ACG 日报
        </h1>
        <div style="color:#d1d5db;">{report_date.isoformat()} · 约 3 分钟读完</div>
      </header>
      <section style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:14px;
                      padding:15px 18px;margin:16px 0;">
        <p style="margin:0 0 6px;line-height:1.55;">
          <strong>今日主线：</strong>{escape(dominant_category)} 项目最多，
          占 {dominant_count}/{len(items)}
        </p>
        <p style="margin:0;line-height:1.55;">
          <strong>最热项目：</strong>
          <a href="{escape(hottest.url, quote=True)}" style="color:#1d4ed8;">
            {escape(hottest.full_name)}
          </a>
          · 今日 +{hottest.stars_today:,}
        </p>
      </section>
      <h2 style="font-size:18px;margin:22px 2px 10px;">今天只看这 {len(featured)} 个</h2>
      {"".join(cards)}
      {quick_section}
      <footer style="color:#6b7280;font-size:12px;line-height:1.6;text-align:center;
                     padding:18px 10px;">
        项目来自 GitHub Trending；相关性与简介由 AI 基于公开资料整理。
      </footer>
    </main>
  </body>
</html>
"""
