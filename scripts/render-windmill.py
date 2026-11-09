"""Generate a separate flow/schedule for each source-based report."""

import argparse
from pathlib import Path

import yaml

from ai_dash.models import load_settings
from ai_dash.reports import load_reports, select_report

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
settings = load_settings(root / "config/sources.yaml")
reports = load_reports(root / "config/reports.yaml")
folder = root / "workflows/windmill/f/ai_dash"
expected = set()


def write(path, value):
    content = yaml.safe_dump(value, sort_keys=False, allow_unicode=True)
    if args.check:
        if not path.exists() or path.read_text() != content:
            raise SystemExit(f"Stale definition: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


for report in reports.reports:
    select_report(settings, reports, report.id)
    write(
        folder / f"{report.id}__flow/flow.yaml",
        dict(
            summary=report.title,
            description="Dedicated source-based AI report; persist before delivery.",
            value=dict(
                modules=[
                    dict(
                        id="report",
                        summary=report.title,
                        value=dict(
                            type="script",
                            path="f/ai_dash/run_digest",
                            tag_override="aidash",
                            input_transforms=dict(
                                report=dict(type="static", value=report.id),
                                example=dict(
                                    type="javascript", expr="String(flow_input.example ?? false)"
                                ),
                            ),
                        ),
                    )
                ]
            ),
            schema={
                "type": "object",
                "properties": {"example": {"type": "boolean", "default": False}},
                "required": [],
            },
        ),
    )
    for slot in report.slots:
        hour, minute = slot.split(":")
        path = folder / f"{report.id}_{hour}{minute}.schedule.yaml"
        expected.add(path)
        write(
            path,
            dict(
                summary=f"{report.title} {slot}",
                schedule=f"0 {int(minute)} {int(hour)} * * *",
                timezone=settings.timezone,
                enabled=False,
                script_path=f"f/ai_dash/{report.id}",
                is_flow=True,
                args={},
                no_flow_overlap=True,
            ),
        )
for path in folder.glob("*.schedule.yaml"):
    if path not in expected:
        if args.check:
            raise SystemExit(f"Obsolete schedule: {path.name}")
        path.unlink()
legacy = folder / "digest__flow/flow.yaml"
if legacy.exists() and not args.check:
    legacy.unlink()
    legacy.parent.rmdir()
