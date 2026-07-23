from __future__ import annotations

import json
import os
import re
from typing import Any

from .http_client import post_json
from .models import ProjectBrief, RepositoryDetails, TrendingRepository


SYSTEM_PROMPT = """你是一名严谨的中文开源技术日报编辑。
只能根据提供的 GitHub 项目资料写作，不得虚构功能、数字、发布日期或采用情况。
表达简洁、具体，避免营销口吻。项目资料不足时明确说“资料中未说明”。
只返回一个 JSON 对象，不要使用 Markdown 代码围栏。字段必须是：
summary: 中文一句话介绍；
problem: 它解决的问题；
highlights: 2 到 3 条核心特点的字符串数组；
target_users: 1 到 3 类适用人群的字符串数组；
why_trending: 为什么今天值得关注，只能根据今日新增 Star、项目活跃度和资料进行谨慎判断；
caveat: 一个需要注意的点；
category: 一个简短分类，如 AI、开发工具、前端、基础设施、数据、学习资源、其他。
"""


def fallback_brief(
    repo: TrendingRepository,
    details: RepositoryDetails,
) -> ProjectBrief:
    description = repo.description or "项目页面暂未提供简介"
    highlights = []
    if repo.language:
        highlights.append(f"主要使用 {repo.language} 开发")
    if details.topics:
        highlights.append(f"主题包括：{'、'.join(details.topics[:4])}")
    if details.license_name:
        highlights.append(f"许可证：{details.license_name}")
    if not highlights:
        highlights.append("需要阅读 README 进一步确认核心能力")

    caveat = "当前为规则生成的基础摘要，建议结合 README 判断成熟度。"
    if details.archived:
        caveat = "仓库已归档，不建议直接用于新的生产项目。"

    return ProjectBrief(
        summary=description,
        problem=f"该项目围绕“{description}”提供开源实现或相关资源。",
        highlights=highlights[:3],
        target_users=["希望了解或试用该项目方向的开发者"],
        why_trending=f"今日新增约 {repo.stars_today:,} 个 Star，进入 GitHub Trending。",
        caveat=caveat,
        category=_guess_category(repo, details),
        generated_by_ai=False,
    )


def _guess_category(repo: TrendingRepository, details: RepositoryDetails) -> str:
    haystack = " ".join(
        [repo.description, repo.full_name, *details.topics]
    ).lower()
    if any(word in haystack for word in ("ai", "agent", "llm", "model")):
        return "AI"
    if any(word in haystack for word in ("frontend", "react", "vue", "web ui")):
        return "前端"
    if any(word in haystack for word in ("database", "data", "analytics")):
        return "数据"
    if any(word in haystack for word in ("server", "cloud", "infra", "kubernetes")):
        return "基础设施"
    if any(word in haystack for word in ("awesome", "tutorial", "learning", "course")):
        return "学习资源"
    return "开发工具"


class OpenAISummarizer:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def summarize(
        self,
        repo: TrendingRepository,
        details: RepositoryDetails,
    ) -> ProjectBrief:
        if not self.enabled:
            return fallback_brief(repo, details)

        source = {
            "repository": repo.full_name,
            "description": repo.description,
            "language": repo.language,
            "total_stars": repo.total_stars,
            "forks": repo.forks,
            "stars_today": repo.stars_today,
            "topics": details.topics,
            "license": details.license_name,
            "created_at": details.created_at,
            "updated_at": details.updated_at,
            "pushed_at": details.pushed_at,
            "open_issues": details.open_issues,
            "archived": details.archived,
            "readme_excerpt": details.readme[:8_000],
        }
        payload = {
            "model": self.model,
            "instructions": SYSTEM_PROMPT,
            "input": json.dumps(source, ensure_ascii=False),
            "reasoning": {"effort": "low"},
            "text": {"verbosity": "low"},
        }
        response = post_json(
            f"{self.base_url}/responses",
            payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        data = _parse_json_response(_response_text(response))
        return ProjectBrief(
            summary=_string(data, "summary", repo.description),
            problem=_string(data, "problem", "资料中未说明"),
            highlights=_strings(data.get("highlights"), ["资料中未说明"])[:3],
            target_users=_strings(data.get("target_users"), ["开发者"])[:3],
            why_trending=_string(
                data,
                "why_trending",
                f"今日新增约 {repo.stars_today:,} 个 Star。",
            ),
            caveat=_string(data, "caveat", "仍需结合项目文档评估。"),
            category=_string(data, "category", _guess_category(repo, details)),
            generated_by_ai=True,
        )


def _response_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    parts: list[str] = []
    for item in response.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    if not parts:
        raise ValueError("OpenAI response did not contain output text")
    return "\n".join(parts)


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("AI summary must be a JSON object")
    return data


def _string(data: dict[str, Any], key: str, fallback: str) -> str:
    value = data.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _strings(value: Any, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    result = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return result or fallback

