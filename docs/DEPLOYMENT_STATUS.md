# Historical deployment evidence

This summarizes the 9–11 November 2026 rollout. Use
[current operations](archdoc/OPERATIONS.md) and [deployment](DEPLOYMENT.md) for
today's behavior. Operator hostnames, bot identities, machine identifiers,
provider generation IDs and private evidence locations are omitted from this
source-facing summary. Original detailed records remain in Git history.

## Initial rollout

The first mixed AI News edition persisted an immutable artifact before delivering
five Telegram messages, all with durable acknowledgements. It collected 743 dated
entries, including 119 within its then-current 24-hour window. Thirty selected
research papers exposed a source-balance problem; a configurable paper cap was
added without changing the delivered edition or its history.

Separate company, analysis, research/OSS and X reports replaced that mixed digest.
Source discovery and strict model-ID handling were repaired during acceptance.

## Retired paid X retrieval

An initial paid verification cost $1.03470405 and returned no validated structured
posts. Its schedule was paused. A separately authorized corrected verification cost
$0.060482, returned two validated posts and reused the saved response for its
delivery example. These are historical observations, not present pricing or
current provider guarantees.

Normal X retrieval now uses free Nitter RSS. The old paid implementation is
recoverable from Git history; private accounting evidence is retained independently.

## Runtime separation

The application moved to its own Windmill workspace, database, Compose project,
secrets and state on 11 November. Historical delivery records and X accounting
were preserved. The initial provider credential was separately stored but reused
an upstream account/key; separate files alone did not establish billing or
revocation isolation. Independently issued upstream keys are needed for that.

The deployment verified source collection and Telegram posting permission without
new paid inference or a verification send. Its dated checks passed 60 tests.
Later changes retired the copied provider services in favor of the separately
deployed authenticated LLM Gateway. These historical service counts and ports are
not the current topology.
