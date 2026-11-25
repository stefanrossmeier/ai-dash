# Contributing

AI Dash is a small single-operator reference application. Open a focused issue
for a bug or proposed change, using synthetic examples and redacted diagnostics.
Use the [security policy](SECURITY.md) for vulnerabilities and credential exposure.

Run the [quickstart](QUICKSTART.md), then `./scripts/check.sh`. Ordinary tests and
checks must not use real provider credentials, paid inference or Telegram sends.
Live checks need an explicit scope and an operator-owned deployment.

Keep retrieval/evidence, deterministic selection, model calls, persistence,
presentation and delivery responsibilities clear. Preserve original timestamps,
uncertainty, source provenance and strict model IDs. Persist before delivery and
never erase accounting/history to bypass a limit or recover from a failure.

For a behavioral change, add a focused regression that fails for the original
problem. Keep formatting/documentation-only changes small. Update the current
architecture/operation guide when its contract changes. Report slots come from
`config/reports.yaml`; regenerate matching Windmill definitions rather than
editing generated schedules independently.

Contribution commits should retain their real authorship. Proposed code is
reviewed under the repository's Apache-2.0 license. Third-party components retain
their own licenses and terms; see [notices](THIRD_PARTY_NOTICES.md).
