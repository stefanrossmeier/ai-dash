# Security policy

Report vulnerabilities through GitHub private vulnerability reporting when that
route is enabled. If it is unavailable, contact the maintainer through the
[GitHub profile](https://github.com/stefanrossmeier) to arrange a private channel
before sharing sensitive details. Never post credentials, private runtime files,
channel destinations or full production artifacts in public issues.

Include the source revision, affected component and a minimal reproduction using
synthetic credentials/data. If a real credential was exposed, revoke it through
its issuer first; deleting a file or changing repository visibility does not
invalidate it.

The current application is an alpha reference for a trusted single operator.
There is no LTS, response-time guarantee, multi-tenant sandbox or automatic
security approval for downstream deployments. Model output and source content
remain untrusted. Provider inference can cost money; use an owned authenticated
gateway with durable accounting and explicit policy.

Keep secrets, SQLite/artifacts, Windmill profiles, backups and gateway state outside
public source. Use TLS for authenticated traffic across untrusted networks. The
current worker template runs as root and its upstream base includes multiple
language runtimes/tools; it needs a separate image-level assessment. A clean
Python dependency scan does not establish a clean container image.

See [publication readiness](docs/PUBLICATION.md) for the dated scan scope and
remaining release gates. No container is represented as security-approved by the
source license or by an offline test pass.
