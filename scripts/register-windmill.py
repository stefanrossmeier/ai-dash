"""Upsert ONLY f/ai_dash definitions through the installed Windmill API.

Uses only the ai-dash runtime profile. No workspace-wide sync/deletion.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "workflows/windmill/f/ai_dash"


def should_enable(
    report: dict,
    enable_all: bool,
    selected: list[str],
    *,
    current_enabled: bool = False,
    disabled: list[str] | tuple[str, ...] = (),
) -> bool:
    if not report.get("enabled", True) or report["id"] in disabled:
        return False
    return enable_all or report["id"] in selected or current_enabled


def main():
    parser = argparse.ArgumentParser()
    runtime = Path(os.getenv("AI_DASH_RUNTIME", "/var/code/ai-dash-runtime"))
    parser.add_argument("--profile-file", type=Path, default=runtime / "windmill-profile.json")
    parser.add_argument(
        "--secrets-dir",
        type=Path,
        default=Path(os.getenv("AI_DASH_SECRETS_SOURCE", str(runtime / "secrets"))),
    )
    parser.add_argument(
        "--enable", action="store_true", help="Enable after independent bot preflight"
    )
    parser.add_argument(
        "--enable-report", action="append", default=[], help="Enable only the named report"
    )
    parser.add_argument(
        "--disable-report", action="append", default=[], help="Pause the named report"
    )
    args = parser.parse_args()
    if set(args.enable_report) & set(args.disable_report) or (args.enable and args.disable_report):
        raise ValueError("cannot enable and disable the same reports")
    configured = {
        r["id"]: r for r in yaml.safe_load((ROOT / "config/reports.yaml").read_text())["reports"]
    }
    if (set(args.enable_report) | set(args.disable_report)) - configured.keys():
        raise ValueError("unknown report requested for schedule enablement")
    profile = json.loads(args.profile_file.read_text())
    base = profile["remote"].rstrip("/") + "/api/w/" + profile["workspaceId"]

    def request(method, route, body=None, missing_ok=False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            base + route,
            data=data,
            method=method,
            headers={
                "Authorization": "Bearer " + profile["token"],
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                raw = response.read().decode()
                try:
                    return json.loads(raw)
                except ValueError:
                    return raw
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and missing_ok:
                return None
            raise RuntimeError(f"Windmill {method} {route} failed (HTTP {exc.code})") from None

    if args.enable or args.enable_report:
        # Read-only preflight using only ai-dash-owned credentials.
        secrets = args.secrets_dir
        token = (secrets / "telegram_token").read_text().strip()
        target = (secrets / "telegram_chat_id").read_text().strip()
        if not token or not target:
            raise ValueError("Independent AI Dash Telegram secrets are required")

        def telegram(method, body):
            req = urllib.request.Request(
                "https://api.telegram.org/bot" + token + "/" + method,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                value = json.load(urllib.request.urlopen(req, timeout=20))
            except Exception:
                raise RuntimeError("Telegram preflight failed (credentials omitted)") from None
            if not value.get("ok"):
                raise RuntimeError("Telegram preflight rejected")
            return value["result"]

        bot = telegram("getMe", {})
        chat = telegram("getChat", {"chat_id": target})
        member = telegram("getChatMember", {"chat_id": target, "user_id": bot["id"]})
        if chat.get("type") != "channel" or not member.get("can_post_messages"):
            raise ValueError("New bot needs Post Messages permission in the AI channel")
        print("Telegram preflight passed:", chat.get("title"), "via", bot["username"])

    if request("GET", "/folders/get/ai_dash", missing_ok=True) is None:
        request("POST", "/folders/create", {"name": "ai_dash", "summary": "Independent AI news"})
    path = "f/ai_dash/run_digest"
    metadata = yaml.safe_load((FOLDER / "run_digest.script.yaml").read_text())
    current = request("GET", "/scripts/get/p/" + path, missing_ok=True)
    script = dict(
        path=path,
        content=(FOLDER / "run_digest.sh").read_text(),
        language="bash",
        summary=metadata["summary"],
        description=metadata["description"],
        schema=metadata["schema"],
        tag="aidash",
        kind="script",
        lock="",
        timeout=3600,
    )
    if current:
        script["parent_hash"] = current["hash"]
    request("POST", "/scripts/create", script)
    # Retire the four old mixed schedules before installing source-based reports.
    for slot in ["0730", "1230", "1730", "2130"]:
        old_path = "f/ai_dash/digest_" + slot
        if request("GET", "/schedules/get/" + old_path, missing_ok=True) is not None:
            request("POST", "/schedules/setenabled/" + old_path, {"enabled": False})
    for definition in sorted(FOLDER.glob("*__flow/flow.yaml")):
        path = "f/ai_dash/" + definition.parent.name.removesuffix("__flow")
        flow = yaml.safe_load(definition.read_text())
        flow["path"] = path
        exists = request("GET", "/flows/get/" + path, missing_ok=True) is not None
        request("POST", "/flows/update/" + path if exists else "/flows/create", flow)
    for file in sorted(FOLDER.glob("*.schedule.yaml")):
        schedule = yaml.safe_load(file.read_text())
        path = "f/ai_dash/" + file.name.removesuffix(".schedule.yaml")
        current_schedule = request("GET", "/schedules/get/" + path, missing_ok=True)
        exists = current_schedule is not None
        report_id = schedule["script_path"].rsplit("/", 1)[-1]
        enabled = should_enable(
            configured[report_id],
            args.enable,
            args.enable_report,
            current_enabled=bool(current_schedule and current_schedule.get("enabled")),
            disabled=args.disable_report,
        )
        schedule.update(path=path, enabled=enabled)
        request("POST", "/schedules/update/" + path if exists else "/schedules/create", schedule)
        if exists:
            request("POST", "/schedules/setenabled/" + path, {"enabled": enabled})
        print(path, "enabled" if enabled else "disabled")
    print("Registered ai-dash only in workspace", profile["workspaceId"])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, StopIteration) as exc:
        raise SystemExit(f"Registration failed: {exc}") from None
