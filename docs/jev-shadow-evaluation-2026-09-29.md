# Jev direct TypeSafe: labeled shadow evaluation

Base: `main` at `b4ad7de4d494506d46bf4be4d297d5ca7e51c096`.
Work branch: `codex/jev-shadow-pr15` (uncommitted, unpushed).
The older Jev worktree remains preserved. No deployment or user enablement.

## Provider and local gate

The current [TypeSafe API reference](https://docs.typesafe.ai/api) documents
`POST https://api.typesafe.ai/v1/systemone`, Bearer authentication, a
`model`/`state`/`questions` request, Choice `choice`/`probabilities`/`confidence`
answers and `usage.input_tokens`/`usage.output_tokens`. The current
[model list](https://docs.typesafe.ai/models) includes pinned `jev-1.13.0`
and lists $0.042 per million input tokens, with output tokens free. The API
does not document a billed-cost field. The existing compact claim schema and
parser were retained; only the provider URL, model, environment variable,
provider-specific tests and local experiment output paths changed.

Before any live call, 33 Jev/search/qualification tests passed, as did syntax
and diff checks. Earlier on this branch, 109 ledger and 5 draft tests passed;
those paths are unchanged by this provider switch. The sending, prospecting,
page-reader, prompt, Dockerfile and boot paths still match `main` exactly.

The ten fictional cases and expected labels were fixed before this run.
SHA-256 of `tests/jev/cases.json`:
`fed231cd83cb1f3772f859c471c08b9d34cad8cfcbeb3b9de7714028d0cf78a0`.
Their OFF column describes the current Milo **rule**, not a measured Milo
response to these fictional inputs. Every source URL uses `example.com`;
this tests interpretation of supplied excerpts, not independent page reading.

## Controlled call and OFF x SHADOW cases

The first controlled call (`official_direct`) returned HTTP 200, `supported`,
416 ms, 509 input tokens and 54 output tokens. Only after that success did
the runner send the remaining nine cases in five batches. All six direct
requests returned HTTP 200 and recorded `decision_applied=milo_unchanged`.
No error or fallback occurred in this run. The output of Jev was not shown
to Milo or used for any decision.

Probability below means the returned probability of **Jev's selected label**.
Latency is for the API request; paired cases share one request and its latency.

| Case | Expected | Milo OFF rule | Jev | P(selected) / confidence | Exact label | Incremental signal vs Milo | Request latency | Request usage; estimated cost |
|---|---|---|---|---|---|---|---:|---:|
| Official direct fact | supported | Cite the opened page | supported | 1.00 / 1.00 | correct | Not measured | 416 ms | 509/54; $0.000021378 |
| Literal scoped year | supported | Preserve year and attribution | supported | 0.86 / 0.81 | correct | Not measured | 411 ms | 781/108; $0.000032802 |
| Weak aggregator | insufficient | Treat as a lead, verify | contradicted | 0.70 / 0.60 | **incorrect** | No: overstates conflict | 411 ms | 781/108; $0.000032802 |
| Thin evidence | insufficient | Leave need unknown | insufficient | 1.00 / 1.00 | correct | Not measured | 296 ms | 761/109; $0.000031962 |
| Namesake | wrong_entity | Disambiguate entity | wrong_entity | 1.00 / 1.00 | correct | Not measured | 296 ms | 761/109; $0.000031962 |
| Plausible inference | insufficient | Keep as hypothesis | insufficient | 0.96 / 0.95 | correct | Not measured | 295 ms | 762/111; $0.000032004 |
| Individual to company | insufficient | Do not generalize testimony | insufficient | 1.00 / 1.00 | correct | Not measured | 295 ms | 762/111; $0.000032004 |
| Outreach readiness | insufficient | Do not infer verified contact | insufficient | 1.00 / 1.00 | correct | Not measured | 391 ms | 756/111; $0.000031752 |
| Conflicting passage | contradicted | Record contradiction | contradicted | 1.00 / 1.00 | correct | Not measured | 391 ms | 756/111; $0.000031752 |
| PR #15 prospect quote | supported | Preserve literal citation | supported | 0.67 / 0.56 | correct | Not measured | 333 ms | 514/54; $0.000021588 |

The full four-option probability distributions are in the ignored local
`tests/jev/results/direct-jev-shadow.jsonl`; the runner's per-case summary is
`tests/jev/results/direct-experiment.json`. These results contain only
synthetic inputs and selected structured fields, not credentials or raw
excerpts. Both files are local and ignored by Git.

## Counts, latency and cost

| Request cases | Latency | Input / output tokens | Estimated cost (USD) |
|---|---:|---:|---:|
| Official direct fact | 416 ms | 509 / 54 | $0.000021378 |
| Literal year + weak aggregator | 411 ms | 781 / 108 | $0.000032802 |
| Thin evidence + namesake | 296 ms | 761 / 109 | $0.000031962 |
| Plausible inference + individual | 295 ms | 762 / 111 | $0.000032004 |
| Outreach readiness + conflicting passage | 391 ms | 756 / 111 | $0.000031752 |
| PR #15 prospect quote | 333 ms | 514 / 54 | $0.000021588 |
| **Total** | **2,142 ms** | **4,083 / 547** | **$0.000171486** |

Mean latency was **357 ms per API request** (six requests). The estimate
multiplies 4,083 input tokens by the published $0.042/M rate; it is not a
billing record. Usage and latency are per request, so paired cases share the
values shown in both rows above; repeated figures must not be summed as
per-case costs.

Exact four-class accuracy: **9/10 (90%)**. If `supported` is treated as the
positive class, there were **0 false supports among seven negative cases**
and **0 rejected supports among three positive cases**. One negative case was
misclassified within the negative group: the weak aggregator was labeled
`contradicted` rather than `insufficient`. Jev did not catch an **observed**
Milo error because the OFF rule was not executed for these synthetic cases.

## Judgment and smallest next step

**USEFUL OBSERVER, provisionally**, for classifying supplied public excerpts:
the model worked through the direct API, returned distributions and got nine
of ten pre-labeled examples right at low measured latency and estimated cost.
Its incremental value over Milo's current behavior remains **unproven**.
The overstatement on the weak aggregator and the lower confidence on a correct
PR #15 quote argue against using any threshold or decision gate from this set.
The contradiction case uses one conflicting excerpt, not two opened pages;
the outreach case tests evidence support, not real contact readiness.

The smallest next step is a **read-only replay of completed Milo qualifications**:
select ten real, public, non-sensitive claim/excerpt pairs, preserve Milo's
actual OFF statements, have a human label evidence support independently,
then compare Jev shadow results against actual Milo errors. Require evidence
of incremental catches with acceptable false alarms before considering an
internal shadow rollout. No model answer should enter qualification, draft,
approval, sending, playbook or ledger in that next step.
