"""Guard deployment boundaries that previously coupled independently owned projects."""

import importlib.util
import json
from pathlib import Path

import httpx
import yaml
from fastapi.testclient import TestClient

from ai_dash import model_gateway as mg

ROOT = Path(__file__).resolve().parents[1]


def test_compose_owns_its_database_network_and_provider_secret():
    text = (ROOT / "deploy/compose.ai-dash.yaml").read_text()
    compose = yaml.safe_load(text)
    assert compose["name"] == "ai-dash"
    assert "db" in compose["services"]
    assert "daily" not in text
    assert "external:" not in text
    worker = compose["services"]["windmill_worker_aidash"]
    assert worker["environment"]["AI_DASH_GATEWAY_URL"] == "http://ai_dash_model_gateway:8080"
    assert not any("openrouter" in mount for mount in worker["volumes"])
    assert not any("secrets:ro" in mount for mount in worker["volumes"])
    for service in ("ai_dash_model_gateway", "ai_dash_x_gateway"):
        assert (
            "AI_DASH_SECRETS_SOURCE"
            in compose["services"][service]["volumes"][
                0 if service == "ai_dash_model_gateway" else 1
            ]
        )
    for service in compose["services"].values():
        for port in service.get("ports", []):
            assert port.startswith("127.0.0.1:")


def test_execution_and_registration_defaults_have_no_legacy_dependency():
    files = [
        "scripts/deploy-vps.sh",
        "scripts/register-windmill.py",
        "scripts/bootstrap-windmill.py",
        "workflows/windmill/f/ai_dash/run_digest.sh",
        "src/ai_dash/cli.py",
    ]
    for file in files:
        text = (ROOT / file).read_text()
        assert "daily-dash" not in text
        assert "daily_dash" not in text
        assert "18080" not in text
        assert ".config/windmill" not in text


def test_runtime_initialization_is_private_and_preserves_existing_credentials(tmp_path):
    spec = importlib.util.spec_from_file_location("init_runtime", ROOT / "scripts/init-runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runtime = tmp_path / "runtime"
    module.initialize(runtime)
    env = runtime / ".env"
    original = env.read_text()
    assert "POSTGRES_PASSWORD=" in original
    assert "@db:5432/windmill" in original
    assert env.stat().st_mode & 0o777 == 0o600
    module.initialize(runtime)
    assert env.read_text() == original


def test_ranking_uses_owned_config_validates_schema_and_attributes_to_ai_dash(monkeypatch):
    monkeypatch.setenv("AI_DASH_MODEL_GATEWAY_CONFIG", str(ROOT / "config/model-gateway.yaml"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    calls = []

    async def provider(**kwargs):
        calls.append(kwargs)
        return httpx.Response(
            200,
            json={
                "id": "owned-generation",
                "choices": [{"message": {"content": json.dumps({"decisions": []})}}],
                "usage": {"cost": 0.001, "prompt_tokens": 10, "completion_tokens": 2},
            },
        )

    monkeypatch.setattr(mg, "_post_openrouter", provider)
    client = TestClient(mg.app)
    payload = {
        "alias": "rank-cheap",
        "purpose": "independence-test",
        "messages": [{"role": "user", "content": "test"}],
        "response_schema": {
            "type": "object",
            "properties": {"decisions": {"type": "array"}},
            "required": ["decisions"],
        },
    }
    result = client.post("/v1/chat", json=payload)
    assert result.status_code == 200
    assert result.json()["model"] == "openai/gpt-6-luna"
    assert result.json()["generation_id"] == "owned-generation"
    assert calls[0]["headers"]["HTTP-Referer"].endswith("/ai-dash")
    assert calls[0]["payload"]["response_format"]["json_schema"]["strict"] is True
    payload["response_schema"]["required"] = ["missing"]
    assert client.post("/v1/chat", json=payload).status_code == 502
    count = len(calls)
    payload["alias"] = "unknown"
    assert client.post("/v1/chat", json=payload).status_code == 404
    assert len(calls) == count
    assert client.post("/v1/x-search", json={}).status_code == 404
    assert client.get("/health").status_code == 200
    assert len(calls) == count


def test_bootstrap_profile_permissions_and_first_run_password_change(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "bootstrap_windmill", ROOT / "scripts/bootstrap-windmill.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "secrets").mkdir()
    (tmp_path / ".env").write_text("AI_DASH_WINDMILL_PORT=18090\n")
    monkeypatch.setenv("AI_DASH_RUNTIME", str(tmp_path))
    calls = []
    initialized = False

    class Response:
        def __init__(self, value):
            self.value = value

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps(self.value).encode()

    def api(request, timeout):
        nonlocal initialized
        calls.append(request.full_url)
        body = json.loads(request.data)
        route = request.full_url.removeprefix("http://127.0.0.1:18090/api")
        if route == "/auth/login":
            if not initialized and body["password"] != "changeme":
                raise module.urllib.error.HTTPError(request.full_url, 400, "Invalid login", {}, None)
            return Response("session-token")
        if route == "/users/setpassword":
            assert body["password"] != "changeme"
            initialized = True
        if route == "/workspaces/exists":
            return Response(False)
        if route == "/workspaces/create":
            assert body["id"] == "ai-dash"
        if route == "/users/tokens/create":
            assert body["workspace_id"] == "ai-dash"
            return Response("own-api-token")
        return Response("ok")

    monkeypatch.setattr(module.urllib.request, "urlopen", api)
    module.main()
    profile = tmp_path / "windmill-profile.json"
    assert profile.stat().st_mode & 0o777 == 0o600
    assert json.loads(profile.read_text())["token"] == "own-api-token"
    assert (tmp_path / "secrets/windmill_admin_password").stat().st_mode & 0o777 == 0o600
    count = calls.count("http://127.0.0.1:18090/api/users/tokens/create")
    module.main()
    assert calls.count("http://127.0.0.1:18090/api/users/tokens/create") == count
