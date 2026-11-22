from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Model):
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    name: str
    category: str
    url: str
    priority: Literal["P1", "P2"]
    kind: Literal["feed", "html", "hn", "hf_papers", "hf_models", "github", "x", "manual"]
    endpoint: str
    focus: str
    enabled: bool = True
    note: str = ""
    expand_roundups: bool = False
    article_paths: list[str] = []

    @field_validator("url", "endpoint")
    @classmethod
    def web_url(cls, value: str) -> str:
        if urlsplit(value).scheme not in {"https", "http"} or not urlsplit(value).hostname:
            raise ValueError("source URLs must use HTTP(S)")
        return value


class Settings(Model):
    timezone: str = "Europe/Berlin"
    slots: list[str] = ["07:30", "12:30", "17:30", "21:30"]
    freshness_hours: int = Field(default=24, ge=1, le=168)
    history_days: int = Field(default=14, ge=1)
    max_per_source: int = Field(default=25, ge=1, le=100)
    max_stories: int = Field(default=30, ge=1, le=60)
    max_paper_stories: int = Field(default=6, ge=0, le=60)
    min_score: int = Field(default=65, ge=0, le=100)
    min_impact: int = Field(default=60, ge=0, le=100)
    min_breadth: int = Field(default=45, ge=0, le=100)
    min_novelty: int = Field(default=40, ge=0, le=100)
    min_quality: int = Field(default=60, ge=0, le=100)
    min_tier: int = Field(default=3, ge=1, le=5)
    omit_delivered: bool = True
    x_batch_size: int = Field(default=5, ge=1, le=14)
    reject_routine_updates: bool = True
    ranking_batch_size: int = Field(default=150, ge=1, le=250)
    ranking_excerpt_chars: int = Field(default=1200, ge=200, le=3000)
    ranking_alias: str = "rank-cheap"
    # Optional per-report ranking prompt filename, resolved next to the default
    # editorial prompt. Lets a report replace the blog-calibrated prompt
    # wholesale instead of only appending focus text.
    ranking_prompt: str | None = None
    x_enabled: bool = False
    report_id: str = "legacy"
    report_title: str = "AI News"
    editorial_focus: str = "AI engineering developments"
    send_empty: bool = False
    example: bool = False
    request_timeout: int = Field(default=20, ge=1, le=60)
    workers: int = Field(default=5, ge=1, le=12)
    hydration_max_requests: int = Field(default=40, ge=0, le=100)
    hydration_timeout: int = Field(default=10, ge=1, le=30)
    sources: list[Source]

    @field_validator("timezone")
    @classmethod
    def timezone_exists(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @field_validator("slots")
    @classmethod
    def valid_slots(cls, slots: list[str]) -> list[str]:
        if not slots or len(set(slots)) != len(slots):
            raise ValueError("slots must be nonempty and unique")
        for slot in slots:
            datetime.strptime(slot, "%H:%M")
            if len(slot) != 5:
                raise ValueError("slots must be HH:MM")
        return slots

    @model_validator(mode="after")
    def unique_sources(self) -> Settings:
        if len({s.id for s in self.sources}) != len(self.sources):
            raise ValueError("duplicate source ids")
        return self


def load_settings(path: Path) -> Settings:
    return Settings.model_validate(yaml.safe_load(path.read_text()))


class Item(Model):
    id: str
    title: str = Field(min_length=1, max_length=500)
    url: str
    published_at: datetime
    source_id: str
    source: str
    category: str
    priority: Literal["P1", "P2"]
    text: str = Field(default="", max_length=12000)
    date_basis: Literal["publication", "submission", "curation", "repository_update"] = (
        "publication"
    )
    original_published_at: datetime | None = None
    discovered_via: str = ""

    @field_validator("url")
    @classmethod
    def web_url(cls, value: str) -> str:
        return Source.web_url(value)

    @field_validator("published_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("publication timestamp must be timezone-aware")
        return value


class Coverage(Model):
    source_id: str
    status: Literal[
        "ok", "empty", "unavailable", "undated", "disabled", "manual", "search_required"
    ]
    items: int = 0
    fresh: int = 0
    detail: str = ""


class Decision(Model):
    id: str
    technical: int = Field(ge=0, le=30)
    practical: int = Field(ge=0, le=30)
    novelty: int = Field(ge=0, le=20)
    impact: int = Field(ge=0, le=20)
    summary: str = Field(min_length=1, max_length=650)
    reason: str = Field(default="", max_length=400)

    @property
    def score(self) -> int:
        return self.technical + self.practical + self.novelty + self.impact


class Selection(Model):
    decisions: list[Decision]


class ImpactDecision(Model):
    rank_score: int = Field(ge=0, le=100)
    impact: int = Field(ge=0, le=100)
    breadth: int = Field(ge=0, le=100)
    novelty: int = Field(ge=0, le=100)
    quality: int = Field(ge=0, le=100)
    tier: int = Field(ge=1, le=5)
    change_type: Literal[
        "routine_update",
        "new_capability",
        "research_breakthrough",
        "substantive_analysis",
        "material_security",
        "other",
    ]
    event_key: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=180)


class EventGroup(Model):
    representative: str
    duplicates: list[str]


class Consolidation(Model):
    groups: list[EventGroup]


class Story(Model):
    item: Item
    score: int
    summary: str


class Artifact(Model):
    schema_version: int = 1
    report_id: str = "legacy"
    report_title: str = "AI News"
    send_empty: bool = False
    example: bool = False
    run_id: str
    created_at: datetime
    window_start: datetime
    window_end: datetime
    stories: list[Story]
    candidates: list[Item]
    coverage: list[Coverage]
    traces: list[dict]
    stats: dict[str, int]
    selection_log: list[dict] = []
    health_warnings: list[str] = []
