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


def _source_label(repo: TrendingRepository) -> str:
    return "ACG 新发现" if repo.source == "radar" else "GitHub Trending"


def _popularity_label(repo: TrendingRepository) -> str:
    if repo.source == "radar":
        return f"★ {repo.total_stars:,}"
    return f"今日 +{repo.stars_today:,}"


def _split_items(
    items: list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
) -> tuple[
    list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
    list[tuple[TrendingRepository, RepositoryDetails, ProjectBrief]],
]:
    trending = sorted(
        (item for item in items if item[0].source != "radar"),
        key=lambda item: item[0].stars_today,
        reverse=True,
    )
    radar = sorted(
        (item for item in items if item[0].source == "radar"),
        key=lambda item: item[0].total_stars,
        reverse=True,
    )
    ranked: list[
        tuple[TrendingRepository, RepositoryDetails, ProjectBrief]
    ] = []
    for index in range(max(len(trending), len(radar))):
        if index < len(trending):
            ranked.append(trending[index])
        if index < len(radar):
            ranked.append(radar[index])

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
                "今天的 Trending 与 ACG 雷达中，没有发现足够相关的 AI Agent、",
                "游戏、动画、视频、绘画、3D、语音或其他 ACG 创作项目。",
                "",
                "宁可少发，也不拿通用框架、数据库、金融或炒币项目凑数。",
                "",
                "---",
                "",
                "项目来自 GitHub Trending 与 GitHub Search；相关性由 AI 筛选。",
                "",
            ]
        )

    categories = Counter(brief.category for _, _, brief in items)
    dominant_category, dominant_count = categories.most_common(1)[0]
    featured, remaining = _split_items(items)
    hottest = featured[0][0]
    trending_count = sum(repo.source != "radar" for repo, _, _ in items)
    radar_count = len(items) - trending_count

    lines = [
        f"# GitHub Trending ACG 日报 · {report_date.isoformat()}",
        "",
        f"> 约 3 分钟读完 · Trending 精选 {trending_count} 个 · "
        f"ACG 新发现 {radar_count} 个",
        "",
        "## 今天先知道",
        "",
        f"- **主线：** {dominant_category} 项目最多，占 {dominant_count}/{len(items)}",
        f"- **最热：** [{hottest.full_name}]({hottest.url})，"
        f"{_popularity_label(hottest)}",
        "",
        f"## 今天只看这 {len(featured)} 个",
        "",
    ]

    for index, (repo, _, brief) in enumerate(featured, start=1):
        highlight = _compact_fragment(brief.highlights[0], 55)
        lines.extend(
            [
                f"### {index}. [{repo.full_name}]({repo.url}) · {brief.category}",
                "",
                f"> {_source_label(repo)} · {repo.history_label} · "
                f"{_popularity_label(repo)}",
                "",
                _compact(brief.summary, 65),
                "",
                f"- **能做什么：** {highlight}",
                f"- **提醒：** {_compact(brief.caveat, 60)}",
                "",
            ]
        )

    for source, title in (
        ("trending", "更多 GitHub Trending 精选"),
        ("radar", "更多 ACG 新发现"),
    ):
        source_items = [
            item
            for item in remaining
            if (item[0].source == "radar") == (source == "radar")
        ]
        if source_items:
            lines.extend([f"## {title}", ""])
        for repo, _, brief in source_items:
            language = repo.language or "未标注语言"
            lines.append(
                f"- **[{repo.full_name}]({repo.url})** · {brief.category} — "
                f"{_compact(brief.summary, 70)} "
                f"`{repo.history_label} · {language} · {_popularity_label(repo)}`"
            )
        if source_items:
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "项目来自 GitHub Trending 与 GitHub Search；相关性和简介由 AI 整理。",
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
    trending_count = sum(repo.source != "radar" for repo, _, _ in items)
    radar_count = len(items) - trending_count

    cards: list[str] = []
    for index, (repo, _, brief) in enumerate(featured, start=1):
        highlight = _compact_fragment(brief.highlights[0], 55)

        cards.append(
            f"""
            <section style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;
                            padding:18px 20px;margin:14px 0;">
              <div style="color:#6b7280;font-size:12px;margin-bottom:6px;">
                重点 {index} · {escape(_source_label(repo))} ·
                {escape(repo.history_label)} · {escape(brief.category)}
              </div>
              <h2 style="font-size:19px;line-height:1.35;margin:0 0 9px;">
                <a href="{escape(repo.url, quote=True)}"
                   style="color:#111827;text-decoration:none;">{escape(repo.full_name)}</a>
                <span style="color:#dc2626;font-size:13px;font-weight:500;margin-left:8px;">
                  {escape(_popularity_label(repo))}
                </span>
              </h2>
              <p style="color:#111827;font-size:15px;line-height:1.65;margin:0 0 10px;">
                {escape(_compact(brief.summary, 65))}
              </p>
              <p style="color:#374151;font-size:13px;line-height:1.55;margin:7px 0;">
                <strong>能做什么：</strong>{escape(highlight)}
              </p>
              <p style="color:#9a3412;font-size:13px;line-height:1.55;margin:7px 0 0;">
                <strong>提醒：</strong>{escape(_compact(brief.caveat, 60))}
              </p>
            </section>
            """
        )

    def quick_section(
        source_items: list[
            tuple[TrendingRepository, RepositoryDetails, ProjectBrief]
        ],
        title: str,
    ) -> str:
        if not source_items:
            return ""
        quick_items = "".join(
            f"""
        <div style="padding:12px 0;border-bottom:1px solid #f0f1f3;">
          <a href="{escape(repo.url, quote=True)}"
             style="color:#111827;font-weight:700;text-decoration:none;">
            {escape(repo.full_name)}
          </a>
          <span style="color:#6b7280;font-size:12px;margin-left:6px;">
            {escape(brief.category)} · {escape(repo.language or "未标注语言")}
            · {escape(repo.history_label)} · {escape(_popularity_label(repo))}
          </span>
          <div style="color:#4b5563;font-size:14px;line-height:1.55;margin-top:4px;">
            {escape(_compact(brief.summary, 70))}
          </div>
        </div>
        """
            for repo, _, brief in source_items
        )
        return f"""
        <section style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;
                        padding:6px 18px 4px;margin:20px 0;">
          <h2 style="font-size:18px;margin:14px 0 4px;">{escape(title)}</h2>
          {quick_items}
        </section>
        """

    remaining_trending = [
        item for item in remaining if item[0].source != "radar"
    ]
    remaining_radar = [
        item for item in remaining if item[0].source == "radar"
    ]
    quick_sections = (
        quick_section(remaining_trending, "更多 GitHub Trending 精选")
        + quick_section(remaining_radar, "更多 ACG 新发现")
    )

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
        <div style="color:#d1d5db;">
          {report_date.isoformat()} · 约 3 分钟读完 · Trending {trending_count}
          · ACG 新发现 {radar_count}
        </div>
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
          · {escape(_popularity_label(hottest))}
        </p>
      </section>
      <h2 style="font-size:18px;margin:22px 2px 10px;">今天只看这 {len(featured)} 个</h2>
      {"".join(cards)}
      {quick_sections}
      <footer style="color:#6b7280;font-size:12px;line-height:1.6;text-align:center;
                     padding:18px 10px;">
        项目来自 GitHub Trending 与 GitHub Search；相关性和简介由 AI 整理。
      </footer>
    </main>
  </body>
</html>
"""
