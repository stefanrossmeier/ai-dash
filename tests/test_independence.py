"""Guard deployment boundaries that previously coupled independently owned projects."""

import importlib.util
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_owns_its_database_network_and_provider_secret():
    text = (ROOT / "deploy/compose.ai-dash.yaml").read_text()
    compose = yaml.safe_load(text)
    assert compose["name"] == "ai-dash"
    assert "db" in compose["services"]
    assert "daily" not in text
    assert compose["networks"]["gateway"]["external"] is True
    assert "AI_DASH_GATEWAY_NETWORK" in compose["networks"]["gateway"]["name"]
    worker = compose["services"]["windmill_worker_aidash"]
    assert worker["environment"]["AI_DASH_GATEWAY_URL"] == "http://ai-dash-llm-gateway:8080"
    # The dedicated llm-gateway instance authenticates the project principal.
    assert (
        worker["environment"]["AI_DASH_GATEWAY_TOKEN_FILE"] == "/run/ai-dash-secrets/gateway_token"
    )
    assert worker["networks"] == ["default", "gateway"]
    mounts = str(worker.get("volumes"))
    assert "gateway.token" in mounts, worker.get("volumes")
    assert not any("openrouter" in mount for mount in worker["volumes"])
    assert not any("secrets:ro" in mount for mount in worker["volumes"])
    assert "ai_dash_x_gateway" not in compose["services"]
    assert "openrouter_api_key" not in str(worker)
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
                raise module.urllib.error.HTTPError(
                    request.full_url, 400, "Invalid login", {}, None
                )
            return Response("session-token")
        if route == "/users/setpassword":
            assert body["password"] != "changeme"
            initialized = True
        if route == "/workspaces/exists":
            return Response(False)
        if route == "/workspaces/create":
            assert body["id"] == "ai-dash"
            assert "username" not in body
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
