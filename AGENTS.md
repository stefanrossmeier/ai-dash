# Repository instructions

Read [the repository map](docs/archdoc/REPO_MAP.md) and
[architecture](docs/archdoc/ARCHITECTURE.md) before changing system behavior.
Use [interfaces](docs/archdoc/API_SURFACE.md) for CLI, configuration and integration
contracts, and [operations](docs/archdoc/OPERATIONS.md) for deployment, diagnosis
and recovery. Update the relevant guide when a contract or boundary changes.
The [evolution guide](docs/EVOLUTION.md) distinguishes historical behavior from
current guarantees. Follow [CONTRIBUTING.md](CONTRIBUTING.md) for checks.

Commits must retain the actual contributor's authorship. Configure and verify the
intended author and committer before pushing; do not inherit an unrelated identity.
Do not rewrite historical authorship to attribute another person's work to the owner.

AI Dash is an independent project. Its runtime, deployment, Windmill instance,
database, model gateway, model configuration, secrets and application state must
not depend on another project's checkout, services, volumes, network or CLI profile.

Keep credentials, private paths, account/channel identifiers and raw runtime evidence
out of source and documentation. Ordinary checks use synthetic inputs, no paid
inference and no Telegram sends. Live operations require an explicitly authorized
operator-owned target. Never clear ledgers or delivery history to bypass limits.
