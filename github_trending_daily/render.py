from __future__ import annotations

from collections import Counter
from datetime import date

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

