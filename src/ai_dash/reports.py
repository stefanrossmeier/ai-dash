from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from ai_dash.models import Model, Settings


class Report(Model):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    title: str
    enabled: bool = True
    categories: list[str] = []
    source_ids: list[str] = []
    exclude_ids: list[str] = []
    slots: list[str]
    focus: str
    max_stories: int = Field(default=12, ge=1, le=30)
    max_paper_stories: int = Field(default=6, ge=0, le=30)
    max_per_source: int = Field(default=25, ge=1, le=100)
    send_empty: bool = False
    x_only: bool = False
    freshness_hours: int = Field(default=24, ge=1, le=168)


class Reports(Model):
    reports: list[Report]

    @model_validator(mode="after")
    def unique_reports(self):
        if len({r.id for r in self.reports}) != len(self.reports):
            raise ValueError("report IDs must be unique")
        for report in self.reports:
            Settings(sources=[], slots=report.slots)
            if report.x_only and len(report.slots) != 1:
                raise ValueError("X report must have exactly one daily slot")
        return self


def load_reports(path: Path) -> Reports:
    return Reports.model_validate(yaml.safe_load(path.read_text()))


def select_report(settings: Settings, reports: Reports, report_id: str) -> Settings:
    report = next((r for r in reports.reports if r.id == report_id), None)
    if report is None:
        raise ValueError(f"unknown report: {report_id}")
    by_id = {s.id: s for s in settings.sources}
    if set(report.source_ids + report.exclude_ids) - by_id.keys():
        raise ValueError("report references an unknown source ID")
    selected = []
    for source in settings.sources:
        include = source.category in report.categories or source.id in report.source_ids
        if not include or source.id in report.exclude_ids or source.kind == "manual":
            continue
        if report.x_only:
            if source.kind != "x" or source.id not in report.source_ids:
                raise ValueError("X report requires explicit X source IDs")
            selected.append(source.model_copy(update={"enabled": True}))
        elif source.kind != "x" and source.enabled:
            selected.append(source)
    if not selected:
        raise ValueError(f"report has no sources: {report_id}")
    if report.x_only and len(selected) > 3:
        raise ValueError("daily X watchlist is limited to three accounts")
    data = settings.model_dump()
    data.update(
        sources=[s.model_dump() for s in selected],
        slots=report.slots,
        report_id=report.id,
        report_title=report.title,
        editorial_focus=report.focus,
        max_stories=report.max_stories,
        max_paper_stories=report.max_paper_stories,
        max_per_source=report.max_per_source,
        x_enabled=report.x_only,
        x_retry_split=False,
        x_batch_size=3,
        send_empty=report.send_empty,
        freshness_hours=report.freshness_hours,
    )
    return Settings.model_validate(data)
