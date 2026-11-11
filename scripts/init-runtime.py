"""Create ai-dash's private runtime configuration once; never copy another project's env."""

import os
import secrets
from pathlib import Path


def initialize(runtime: Path):
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    (runtime / "secrets").mkdir(mode=0o700, exist_ok=True)
    env = runtime / ".env"
    if not env.exists():
        password = secrets.token_hex(32)
        content = (
            "WM_IMAGE=ghcr.io/windmill-labs/windmill:1.775.1\n"
            f"POSTGRES_PASSWORD={password}\n"
            f"DATABASE_URL=postgres://postgres:{password}@db:5432/windmill\n"
            "AI_DASH_WINDMILL_PORT=18090\n"
            "AI_DASH_MODEL_PORT=18082\n"
            "AI_DASH_X_PORT=18081\n"
        )
        with open(env, "x", opener=lambda p, f: os.open(p, f, 0o600)) as file:
            file.write(content)
    print("Independent runtime configuration ready:", runtime)


if __name__ == "__main__":
    initialize(Path(os.getenv("AI_DASH_RUNTIME", "/var/code/ai-dash-runtime")))
