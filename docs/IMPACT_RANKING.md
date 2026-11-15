# AI impact ranking v2

The first repair recovered missing articles but still scored technical usefulness
too generously. The 15 November research edition included Codex 0.169.0 (61) and
0.168.0 (58), primarily interface and workflow updates. The old 55-point additive
policy let such niche utility compensate for low ecosystem impact.

The new policy adapts DailyDash Top News' joint impact/breadth judgment to AI news.
DailyDash is a development reference only: this implementation, model gateway,
configuration, credentials and deployment remain fully owned by AI Dash.

## Model and cost structure

The model remains `openai/gpt-6-luna`, the same GPT-6 variant used by DailyDash.
The owned gateway now explicitly requests `reasoning.effort=low`, excludes returned
reasoning text, and allows 32,768 output tokens per request. There are at most two
provider attempts, with no automatic model fallback.

All evidenced candidates are evaluated in bounded batches of up to **150**; there
is no global first-N truncation of the pool at ranking time. Each candidate supplies
only an opaque slot, headline, timestamp basis and **1,200-character facts excerpt**.
Publisher identity, URL, source priority and full bodies are withheld from scoring.
The keyed response must evaluate every exact slot, without unknown or missing slots.
The model returns dimensions and a short rationale, not a summary for every rejected item.

Only qualifying events enter global consolidation. Paper/story caps and a soft
publisher-diversity preference then apply. Only the final shortlist receives
35–65 word summaries from the larger available evidence. An entirely rejected
pool produces no consolidation or summarization request.

## Publication policy

All dimensions use an absolute 0–100 scale. Let `H` be the harmonic mean of
`impact` and `breadth`, or zero if both are zero:

```
score = 0.65 * H(impact, breadth)
      + 0.15 * rank_score
      + 0.10 * novelty
      + 0.10 * quality
```

Every condition must hold:

| Gate | Minimum |
|---|---:|
| Composite score: company / analysis / X | 65 |
| Composite score: research & OSS | 60 |
| Impact | 60 |
| Breadth | 45 |
| Novelty | 40 |
| Evidence quality | 60 |
| Tier | 3 of 5 |

`routine_update` is ineligible even if other fields are inflated. The harmonic
mean and independent floors prevent a high generic priority or utility judgment
from rescuing a narrow, low-impact update.

The prompt anchors side-chat tabs, model pickers, resize handles, spinners,
compatibility patches and ordinary CLI release notes at tier 1–2. It applies the
same standard to Codex, Claude Code, Cursor and other tools. No product or version
is blacklisted. A genuine broad capability release or documented critical security
incident can qualify. A vague “security fix” without scope or consequences does
not automatically become a high-impact security story.

Major model/open-weight releases, substantial measured changes in inference
economics or capability, consequential research and decision-changing original
analysis can qualify. Small benchmark deltas, metadata pushes, rediscovered model
cards, niche demos and routine patch notes normally do not. There is no minimum
number of stories and no backfill from below the gates.

## Diagnostics and validation

Each ranking log records all model dimensions, tier, change type, event identity,
short rationale, deterministic composite score, explicit rejection reasons and
the `ai-impact-v2` policy version. Gateway traces record actual model, effort,
latency, attempts and usage. Pipeline stats count ranked and policy-rejected items.
A completely evaluated but rejected pool is an ordinary quiet edition, not a
collection outage. Existing source failures and missing evidence remain health warnings.

Regression coverage includes inflated routine scores, asymmetric impact/breadth,
novelty and evidence floors, eligible critical security/capability changes, exact
slot validation, 372-candidate batching without truncation, bounded source-neutral
inputs, summary generation only for finalists, invalid summaries, model settings,
and preserved multipart delivery/history.

Calibration replays real saved candidates separately from six explicitly synthetic
positive/negative controls. The evaluation never writes application history,
sends Telegram messages, or retrieves X. Controls are test data and never news.
Evaluation artifacts and complete provider traces are private operational evidence.

The initial 70-point gate retained only five of 372 real candidates. Reviewing
borderline results showed it also removed concrete inference improvements such as
production compiler throughput gains. The final thresholds therefore use 65 for
general reports and 60 for research, retaining the independent materiality floors
and routine-update veto. Threshold comparison reused the same semantic decisions;
it did not generate additional model requests or impose a publication quota.

The final replay retained 11 of 372 real candidates before event consolidation and
delivery-history dedupe. Both Codex 0.169.0 and 0.168.0 were classified as routine
updates at approximately 35 points and rejected. All three positive and three
negative synthetic controls passed. Three low-effort GPT-6 Luna calls evaluated
378 total candidates in batches of 150/150/78 at a reported cost of $0.03021489.
This is calibration evidence, not a guarantee of subjective ranking quality or
the number of messages in a future edition. The compact public result is in
[calibration evidence](evidence/impact-ranking-calibration-2026-11-15.json).
