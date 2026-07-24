from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TrendingRepository:
    rank: int
    full_name: str
    url: str
    description: str = ""
    language: str = ""
    total_stars: int = 0
    forks: int = 0
    stars_today: int = 0


@dataclass(slots=True)
class RepositoryDetails:
    topics: list[str] = field(default_factory=list)
    license_name: str = ""
    created_at: str = ""
    updated_at: str = ""
    pushed_at: str = ""
    open_issues: int = 0
    homepage: str = ""
    archived: bool = False
    default_branch: str = ""
    readme: str = ""


@dataclass(slots=True)
class ProjectBrief:
    summary: str
    problem: str
    highlights: list[str]
    target_users: list[str]
    why_trending: str
    caveat: str
    category: str
    generated_by_ai: bool = False


@dataclass(slots=True)
class InterestMatch:
    repository: str
    score: int
    category: str
    reason: str
    generated_by_ai: bool = False
