# Publication history sanitization

Prepared 25 November 2026 at the owner's request to exclude private operational
identifiers while preserving evidence of the system's development.

The candidate retains all 83 pre-publication implementation commits, including
33 merge commits and all eight branch tips. Author and committer identities,
original dates, parent relationships, code changes and tests are preserved. Local
safety stashes are private backups, not publication inputs.

Historical rollout/provenance documents now use neutral placeholders for operator
hosts, a private source path, a machine directory, a bot username and provider
request identifiers. A feature branch and its merge message use a neutral name.
Current code, configuration, prompts, workflows and deployment files are unchanged
from the verified pre-cleanup application. Evidence permalinks now target the
corresponding sanitized commits.

Commit hashes change when their contents or parents change. Signatures on changed
commits are removed because they would no longer validate; original signed objects
remain in the private backup. This is targeted identifier redaction, not a squash
of the development history. The [33 original PR descriptions](history/PULL_REQUESTS.md)
are retained as dated evidence with sanitized commit references. Native GitHub
PR records and CI logs stay private.

Validation covered all candidate history objects and the current source, with no
excluded identifiers found. The original GitHub inventory covered 33 PRs and 115
retained workflow runs (483 log files); 16 runs contained the branch alias. These
original records remain private rather than being copied into public CI history.
The candidate's ordinary gate passed 151 offline tests, lint, configuration,
generated workflow and distribution checks; secret scans found no credential.

## GitHub boundary

Original PR refs, cached diffs and CI metadata are outside ordinary Git branch
rewriting. To keep those identifiers out of public view, make this candidate the single
active public development repository and keep the original as a frozen private
archive. A one-time rename/replacement can preserve the canonical repository URL.
Future work uses the public repository directly; there is no separate publishing
branch, synchronization step or second active development repository. Preserve original
reviews and logs there for private reference. Do not claim that deleting a branch
or force-pushing main removes every original GitHub reference.

Before publication, verify every reachable object for the excluded identifiers,
run the ordinary quality and secret-scanning gates, and check all current evidence
links against rewritten commits. Push only candidate branches and objects. Do not
merge or mirror an old clone into the replacement repository; doing so can restore
the excluded history. No runtime credential or accounting state is part of this
source migration.
