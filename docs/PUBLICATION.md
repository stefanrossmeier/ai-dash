# Publication readiness

Reviewed 25 November 2026; history assessment corrected after manual context
review. The application is suitable for evaluation as a small source reference,
with explicit alpha/single-operator limits. For a developer/architect portfolio,
preserve meaningful development history and review operational metadata selectively.
No credential finding requires a wholesale history replacement. The clean export
is an optional distribution path. Runtime image security and component licensing
remain separate release gates.

## Publication scope

| Deliverable | Assessment |
| --- | --- |
| Current application source and synthetic demonstration | Can be packaged for review through the checked clean export |
| Existing repository with Git/PR/Actions history | Valuable development evidence; selectively review low-sensitivity operational metadata and keep dated claims in context |
| Prebuilt application worker image | Not release-approved: component terms and inherited advisory backlog remain unresolved |
| Bare PyPI wheel as a complete product | Not supported: deployment also requires configuration, assets and workflows from the checkout |
| Hosted or multi-user service | Not established by the implementation, testing or licensing review |

The export is a local artifact. Producing it does not create a public repository,
change GitHub visibility, publish an image or approve an upstream license route.

## Source and account disclosures

The source/history scan was extended to all available branch/reflog and PR-head
refs. The GitHub surface review inspected all 30 PR/issue records, repository
comments and PR reviews. All 104 retained CI runs were downloaded: 296 log files,
about 2.65 MB, scanned with secret values redacted. No credential was detected in
these published-content surfaces. There were no repository release assets,
retained Actions artifacts or wiki to inspect at the time.

An initial regex pass flagged five CI runs for an operator-name match and two
for a home-path match. Manual review corrected those classifications: the former
were Git branch references such as an agent-named YouTube feature branch; the
latter were the Windmill API route `/users/setpassword`, incorrectly matched by a
case-insensitive `/Users/` filesystem pattern. These alerts do not establish
private filesystem or server-address disclosures and do not justify deleting those
CI runs. The earlier report overstated this concern.

Older Git documentation does retain actual SSH aliases, a machine/bot identifier,
a private source-registry home path and provider trace IDs. These are operational
metadata, not authentication credentials. They can be retained with the owner's
acceptance or selectively redacted. No destructive history rewrite, run deletion
or visibility change was performed.

GitHub documents that making a repository public exposes its retained Actions
[history and logs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
A strict policy of withholding historical operator information would require
more than current-file cleanup. That is a privacy choice, not a requirement to
hide ordinary engineering iteration. A new repository from the clean export is
available for minimal-disclosure distribution; retaining this repository's
meaningful history is preferable when architectural evolution is part of its
purpose. Any chosen redaction needs to account for old PR references as well as
Git branches, and should avoid destroying useful review context unnecessarily.

This inspection did not establish an exposed provider credential or account
compromise. It is not an audit of every external service, host session or unrelated
repository. Private audit exports and raw production artifacts remain outside the
clean source candidate.

## History as engineering evidence

The history records a progression from 9 to 25 November 2026, including evidence
hydration, runtime separation, paid-search experiments, free RSS retrieval,
request identity/recovery and community-specific ranking. Those transitions and
their regression fixes are useful evidence of operating and improving a system.
A clean snapshot loses much of that evidence.

Reviewers can reasonably question earlier claims that exceeded the implementation:
the old X budget reserved zero while describing spending headroom, early gateway
idempotency used a new UUID per call, and successful runs/tests did not establish
that readers received useful stories. Some editorial changes were explicit
requirement changes; others fixed defects. Preserve that distinction. Dated
statements about free X editions also need the current clarification that RSS
collection is free while inference can cost money.

The appropriate response is a concise, evidenced evolution narrative linking the
problem, observation, changed decision, validation and remaining limit. Do not
rewrite old defects out of existence or present old claims as current guarantees.
Squashing routine fixups may improve readability, but flattening the whole history
would remove useful evidence. Owner-only instructions, including fixed commit
identity requirements, also need review before inviting public contributors.

## Runtime image evidence

Trivy 0.76.2 scanned the existing Linux/amd64 application image, with checksum
verification of the scanner download. The scanned image was
`sha256:95634ba216f497654b10b45f15558339c2718227f2f1a0e05614a7bd92f31610`.
It was Debian 13.6 and configured to run as root. No live container, package or
service was changed during this scan.

The raw scan reported 7,589 package/advisory matches: 28 critical, 1,112 high,
4,515 medium, 1,882 low and 52 unknown. These are scanner matches, not a count of
exploitable application flaws. `linux-libc-dev` alone accounted for 4,898 matches;
kernel-header package matches do not establish that the host runs a vulnerable
kernel. Go toolchain binaries and shared package variants also repeat findings.
Deduplicating advisory/package/version tuples leaves 7,092 records, including
the header records. Excluding that package leaves 2,194 unique tuples, including
25 critical and 462 high scanner ratings. Exclusion is classification, not a
patched-package claim or a blanket dismissal.

Examples requiring image-level review include the installed Brotli library and
GLib, with Debian fixes available. The Debian
[Brotli advisory](https://security-tracker.debian.org/tracker/CVE-2026-111497)
lists `1.1.0-2+deb13u1` as fixed; the image held `1.1.0-2+b7`.
The [GLib advisory](https://security-tracker.debian.org/tracker/CVE-2026-58016)
also illustrates why scanner severity is not enough: its described trigger is
D-Bus introspection XML, whose reachability from this application was not shown.
The application requests identity encoding and rejects compressed source responses;
that constraint does not update the image's libraries or cover unrelated tools.

The four language-package Python matches were in Windmill's bundled pip/setuptools
runtimes, not the project's `.venv` dependencies. The earlier 33-distribution PyPI
audit found no known dependency advisory; its clean result never covered the OS
or bundled tools. Raw image results and disclosure inventories are private audit
evidence, not silently suppressed scanner exceptions.

Before releasing an image, choose a permitted runtime base/build route, reduce
unneeded components, upgrade reviewable packages and scan the exact replacement.
Record affected paths, fixed versions and any justified reachability dispositions;
validate non-root execution, resources, egress and functional behavior. Do not
label the current image hardened or use a broad ignore file to obtain a green scan.
Component-term questions are detailed in [third-party notices](../THIRD_PARTY_NOTICES.md).

## Clean source candidate

`publication-files.txt` selects current code, config, prompts, synthetic tests,
workflows, public-facing docs and the compact dated ranking calibration. It omits
owner-specific `AGENTS.md`, the private portfolio review, raw production snapshots,
dated operational dossiers and every Git/PR/Actions history. Historical files
remain in the operational checkout and its private history.

After committing the reviewed source, use a reviewed Gitleaks installation:

```sh
python3 scripts/export-public-source.py \
  --revision HEAD \
  --gitleaks /absolute/path/to/gitleaks \
  --output /absolute/output/ai-dash-source.tar.gz
```

The exporter reads only the selected committed revision. It rejects private paths
and links, requires a passing redacted secret scan and refuses to overwrite an
archive or receipt. The archive has no Git database. Its sidecar receipt records
the source revision, archive hash and per-file hashes; retain it for review.

Ordinary source-distribution builds also exclude the owner instructions and dated
operational dossiers. The quality gate inspects the actual source/wheel archives,
rejects members outside `publication-files.txt` and checks license metadata/files.
This closes a separate packaging gap: the earlier default source distribution
included the operational review and production snapshot even when source files
contained no credentials. Do not release an artifact that bypasses this gate.

Unpack the candidate in a fresh directory and run [the quickstart](../QUICKSTART.md)
and `./scripts/check.sh`. Verify local Markdown links, included license metadata,
file hashes and the absence of excluded histories/runtime data. A source candidate
does not contain provider credentials or require any inference/delivery to verify.
The synthetic example must not be presented as real news or a model-quality test.

Before actual publication, choose the destination and update repository URLs if
different, add an accurate short description/topics, enable appropriate private
security reporting and review the final candidate. Preserve contributor authorship.
No public repository, registry release or managed service was created by this review.
