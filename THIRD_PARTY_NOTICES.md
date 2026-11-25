# Third-party notices and deployment licensing

AI Dash's application source is provided under the [Apache 2.0 license](LICENSE).
This statement does not relicense external software, source publications,
inference services, APIs or container components.

## Application provenance

The impact-ranking design in `src/ai_dash/ranking.py` is adapted from the
Apache-2.0 [DailyDash](https://github.com/stefanrossmeier/daily-dash) project by
Stefan Rossmeier. AI Dash owns its implementation and runtime; it does not import
another application's checkout or private configuration.

Source registries identify public publishers, repositories and social accounts.
Their names, content and trademarks retain their owners' rights. A public feed
or API endpoint is not blanket permission to republish full articles or offer a
commercial content service. Review the source/service terms for the intended use.

## Python distributions

Runtime and development dependencies are resolved in `uv.lock`. They are external
distributions, not vendored or relicensed by this repository. Retain their license
files when redistributing an environment or binary artifact. The application
wheel's Apache-2.0 metadata covers the authored application distribution.

## Windmill and container images

The default deployment uses Windmill v1.775.1 and extends its prebuilt Community
Edition image. That release's [license](https://github.com/windmill-labs/windmill/blob/v1.775.1/LICENSE)
distinguishes Apache-licensed components, AGPL-licensed source and proprietary
features. Its prebuilt CE distribution has additional conditions on modification,
wrapping, resale and managed-service use. It is not an Apache-only base image.

The Dockerfile in this repository extends that prebuilt image. No upstream
agreement establishing image modification/redistribution rights was supplied in
this review. Resolve that deployment/distribution route before publishing a
derived image or offering a managed service. An upstream-approved agreement and
a verified AGPL-only source build are distinct possible routes; neither is
established by this notice or by a successful build.

PostgreSQL, the operating system, language runtimes, tools and an independently
deployed LLM Gateway retain their own licenses. This source export contains none
of their binaries. A source release does not approve the runtime image's licensing
or security posture.
