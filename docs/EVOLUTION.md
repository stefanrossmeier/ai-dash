# System evolution and evidence

This guide keeps earlier claims in context without removing development history.
The linked commits establish changes in implementation; they do not establish
unrecorded human approval, production security or comprehensive source coverage.
Current behavior is described in [architecture](archdoc/ARCHITECTURE.md),
[interfaces](archdoc/API_SURFACE.md) and [operations](archdoc/OPERATIONS.md).

## From collection to evidence-aware briefings

The [initial application](https://github.com/stefanrossmeier/ai-dash/commit/99a8966a4872b2043995aeab58f43d2f8d9256af) collected dated public material and
produced Telegram briefings. Subsequent [evidence hydration](https://github.com/stefanrossmeier/ai-dash/commit/3dd5ebd593d13ec4a1cb9b0967f60b6af3eb7b54) and
[impact ranking](https://github.com/stefanrossmeier/ai-dash/commit/be84c7975c9f3054b1c8654572bf8571714713e9) added article context, explicit admission gates
and event selection. This made the selection inspectable; it did not make source
claims factual. The [independent runtime work](https://github.com/stefanrossmeier/ai-dash/commit/8f688a48d6d36133fb8764e3759a3da4800657c8) separated application
ownership from other projects. The later [dedicated gateway integration](https://github.com/stefanrossmeier/ai-dash/commit/aefe997d942098fc8980644747026958fc86ee5e)
separated provider execution and accounting from news selection.

## Claims, corrections and current limits

| Topic | Historical problem or changed requirement | Correction and evidence | Current limit |
| --- | --- | --- | --- |
| Paid X spending | The [nominal USD 0.60 budget](https://github.com/stefanrossmeier/ai-dash/commit/f8b150960ff27eaf9e023166cb24e5afddc0ab36) provisionally reserved zero for a request; it could not prove a hard spending ceiling. | [Paid retrieval and its local budget were removed](https://github.com/stefanrossmeier/ai-dash/commit/7f85c92a0327ed08a4732e7802aa14070b929949); `tests/test_pipeline.py::test_x_rss_only_and_never_paid` prevents that fallback. | Free RSS retrieval does not mean a free briefing. Ranking, consolidation and summaries use inference. Gateway policy/accounting is external; this application does not promise its own hard inference cost cap. |
| Inference recovery | The first gateway client generated a new UUID per call despite an idempotency claim. | [Payload-derived identity](https://github.com/stefanrossmeier/ai-dash/commit/d29da01cda83f522663fde4e4801fb2d5195df26) was then [scoped to a logical run](https://github.com/stefanrossmeier/ai-dash/commit/4a1982d679a36ae11bb1d152c38f05c917a3340d); [authenticated durable recovery](https://github.com/stefanrossmeier/ai-dash/commit/cd2815aba4f78be27f22572c04cf360a2e52054a) added explicit recovery. See `tests/test_gateway_client.py`. | Recover with the same logical run and payload. A newly rebuilt request with changed data is a different request, even if it concerns the same news. Unknown outcomes do not justify spending again. |
| Multiple X slots | A once-daily guard survived the move to three slots. Repetition policy also changed. | [The stale guard was removed](https://github.com/stefanrossmeier/ai-dash/commit/55cd130fef7342667edd6b045ae121c693b95ff9); [overlap was deliberately accepted](https://github.com/stefanrossmeier/ai-dash/commit/246c247a5063d19f3fc831556e5262564b0f6667). | Repeated X and YouTube items across rolling windows are intentional. Feed truncation can still hide items. |
| Windows and failed delivery | A fixed lookback did not fit uneven report cadence; buffered news could become stale after delivery failure. | [Cadence windows and fresh-only delivery](https://github.com/stefanrossmeier/ai-dash/commit/a0f4c84225b20a7f7768ea5b823e5fb8d50c1eb6); regression coverage in `tests/test_cadence.py` and `tests/test_fresh_delivery.py`. | No durable discovery backlog. Discarding unsent parts preserves audit history but does not recover each story individually. |
| Reddit relevance | A successful job could reject every community story under a blog-oriented policy. The 25 November investigation found 18 ranked posts and no admitted stories. | [Community-specific ranking](https://github.com/stefanrossmeier/ai-dash/commit/f3204568256d05f8cafe3918a1854ad8b27d375b) preserves discussion evidence and attributed claims; `tests/test_community_policy.py` covers its contract. The authorized live example then selected eight stories and received two Telegram acknowledgements. | One successful example is evidence of that run only. Ranking remains subjective; quality and source availability require ongoing observation. |
| Publication packaging | Default source builds included dated operational dossiers even without exposed credentials. | [Explicit archive checks](https://github.com/stefanrossmeier/ai-dash/commit/2fc1a22d034f10aa671ceb4501b76f3d8350bd35) restrict distributable paths and verify license files. | Git/PR/Actions history remains separate from an archive. Inspect actual release artifacts and historical metadata before publication. |

## What a green result establishes

Offline regressions test bounded contracts using synthetic inputs. They do not
establish today's source availability, real-world ranking quality, delivery to a
person's device or immunity to credential exposure. Windmill completion means the
job completed, not that stories qualified. Telegram acknowledgement means an API
accepted a message part, not that a reader received a notification.

`ai-dash status` separates selection outcome, selected count and delivery state
for each latest persisted edition. It exposes acknowledged/total parts, uncertainty,
partial delivery and quiet editions. Smoke checks print these as diagnostics
separately from infrastructure readiness. Inspect Windmill failures and private
collection checkpoints too: failure before persistence leaves the previous edition
as the latest one. A quiet edition warrants editorial inspection when unexpected;
it is neither automatically a broken system nor proof that nothing happened.

## Remaining engineering work

The [publication review](PUBLICATION.md) records inherited image advisories,
root worker execution and unresolved upstream image modification/distribution
terms. The current deployment is a trusted single-operator reference; this guide
does not close those image-release gates. There is no per-story acknowledgement
mapping, end-to-end backup/restore drill, built-in separate operator alert channel
or agreed service-level objective. Architecture-significant historical rationale
has not been reconstructed into accepted ADRs.

The contributor instructions now preserve real authorship and route maintainers
to the architecture documents. Meaningful commits, PR discussions and CI history
are retained. Old operational metadata needs a deliberate privacy decision;
ordinary fixes and requirement changes are useful engineering evidence.
