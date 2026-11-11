"""Initialize only ai-dash's Windmill instance and private operator profile."""

from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.request
from pathlib import Path


def private_write(path: Path, content: str):
    with open(path, "w", opener=lambda p, f: os.open(p, f, 0o600)) as file:
        file.write(content)
    path.chmod(0o600)


def main():
    runtime = Path(os.getenv("AI_DASH_RUNTIME", "/var/code/ai-dash-runtime"))
    env = dict(
        line.split("=", 1)
        for line in (runtime / ".env").read_text().splitlines()
        if line and not line.startswith("#")
    )
    remote = "http://127.0.0.1:" + env.get("AI_DASH_WINDMILL_PORT", "18090")
    token = ""

    def request(method, route, body=None):
        req = urllib.request.Request(
            remote + "/api" + route,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read().decode()
            try:
                return json.loads(raw)
            except ValueError:
                return raw

    password_file = runtime / "secrets/windmill_admin_password"
    if not password_file.exists():
        private_write(password_file, secrets.token_urlsafe(36))
    password = password_file.read_text().strip()
    try:
        token = request(
            "POST", "/auth/login", {"email": "admin@windmill.dev", "password": password}
        )
    except urllib.error.HTTPError as exc:
        if exc.code not in {400, 401}:
            raise
        token = request(
            "POST", "/auth/login", {"email": "admin@windmill.dev", "password": "changeme"}
        )
        request("POST", "/users/setpassword", {"password": password})
    if not request("POST", "/workspaces/exists", {"id": "ai-dash"}):
        request(
            "POST",
            "/workspaces/create",
            {"id": "ai-dash", "name": "AI Dash", "username": "ai_dash"},
        )
    profile_file = runtime / "windmill-profile.json"
    if not profile_file.exists():
        api_token = request(
            "POST", "/users/tokens/create", {"label": "ai-dash-deploy", "workspace_id": "ai-dash"}
        )
        private_write(
            profile_file,
            json.dumps(
                {
                    "name": "ai-dash-local",
                    "remote": remote,
                    "workspaceId": "ai-dash",
                    "token": api_token,
                }
            )
            + "\n",
        )
    print("Independent Windmill ready:", remote, "workspace ai-dash")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"Windmill bootstrap failed (HTTP {exc.code}; credentials omitted)"
        ) from None
