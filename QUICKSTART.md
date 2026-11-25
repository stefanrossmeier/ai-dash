# Key-free quickstart

This local path validates configuration and shows a synthetic briefing without
accounts, provider keys, Windmill, Docker, inference or Telegram delivery.
Use Python 3.12 and `uv` on macOS or Linux. Start in a repository checkout or an
unpacked clean source export.

```sh
uv sync --frozen --no-editable
uv run --no-sync ai-dash validate
uv run --no-sync python scripts/example-report.py
./scripts/check.sh
```

The example is clearly labeled synthetic. It renders an in-memory artifact and
does not collect news, open a state database or call an external service. It
demonstrates the message format, not model quality or real developments.

The quality gate reinstalls the current application without editable path hooks,
then checks formatting, tests, config, generated workflows and source/wheel builds.
The wheel contains Python code; normal deployment also needs the checkout's
configuration, assets and workflow definitions. A bare `pip install` is not a
complete runnable installation.

For real use, review [deployment](docs/DEPLOYMENT.md),
[operations](docs/archdoc/OPERATIONS.md), [security](SECURITY.md) and
[component licensing](THIRD_PARTY_NOTICES.md). Manual `preview` can incur inference
cost; `run` can post to Telegram. `collect` uses source networking. None of those
live operations is part of this quickstart.
