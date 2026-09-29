# Jev shadow pilot: reconciliation and first live attempt

Historical record. The direct TypeSafe experiment completed on 29 Sep 2026;
see [the newer evaluation](jev-shadow-evaluation-2026-09-29.md) for the current
provider and measured results.

## Vercel AI Gateway continuation (28 Sep 2026)

The TypeSafe organization lacked usable direct API credit, so the pilot now
uses Vercel AI Gateway's documented TypeSafe-compatible endpoint,
`POST https://ai-gateway.vercel.sh/typesafe/v1/systemone`, bearer
`AI_GATEWAY_API_KEY`, and model `typesafe-ai/jev`. The documented compatibility
preserves the existing Choice answer shape, including `choice`, `confidence`
and `probabilities`. Token usage uses `input_tokens`/`output_tokens`; Gateway
cost, when present, is `provider_metadata.gateway.cost`. The native
`/v1/evaluate` endpoint has a different response convention and was not used.
The local log stores only selected structured fields, not arbitrary Gateway
metadata or error bodies.

Before the new request, 33 search/qualification/Jev tests, 109 sending ledger
tests and 5 draft tests passed. A mocked transport test checked the Vercel URL,
model, bearer header and successful HTTP status. `git diff --check` passed and
the sending, prospecting, page-reader, prompt, Dockerfile and boot paths still
match `main` at `b4ad7de4d494506d46bf4be4d297d5ca7e51c096`.

The ten fictional labels remain coherent with the post-PR #15 citation and
qualification rules. Their `milo_rule` entries are expected behavior, not
observed Milo results. The `source_contradiction` case compares one claim to
one conflicting passage; it does not test reconciliation of two opened pages.

One controlled Gateway POST was attempted for `official_direct`. The key was
present in that process. The response was **HTTP 401** after **1,102 ms**;
there was no parsed Jev answer, usage or cost. The log recorded
`milo_unchanged`, and no retry or case experiment followed. The official
Gateway documentation classifies 401 as missing or invalid authentication;
the request used the documented endpoint and bearer-header form, but this
attempt alone cannot identify why the supplied nonempty credential was
rejected. The response body was neither logged nor exposed. The Vercel
experiment remains unmeasured and the result classification remains
**NO VALUE demonstrated yet**. Jev stays disabled by default and shadow-only.

### Follow-up after the owner replaced the Gateway key

Using the replacement key, authenticated `GET /v1/models` returned HTTP 200
and listed `typesafe-ai/jev` among 390 model IDs. One newly authorized
controlled Jev request then used the same first fictional case and returned
**HTTP 403** in **730 ms** at `2026-09-29T02:38:29Z`. The log retained
`milo_unchanged`. No Jev answer, probability, confidence, usage or cost was
returned to the pilot, and no OFF x SHADOW case batches were sent.

The authenticated catalog confirms the key works for model listing; it does
not establish permission to run evaluations. The tested request matches the
documented endpoint, bearer header and model ID. Vercel's HTTP documentation
describes 403 as insufficient permissions, but the precise cause of this
denial is not established. Possibilities to inspect in the owner's Vercel
team include evaluation/model access, routing or provider restrictions,
key budget and Gateway billing/credits. There was no retry. The new failed
attempt is recorded separately from the prior 401 in the ignored local log.

Sources: [Vercel TypeSafe API](https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe),
[Vercel Evaluation API](https://vercel.com/docs/ai-gateway/modalities/evaluation),
[Vercel authentication](https://vercel.com/docs/ai-gateway/authentication-and-byok),
[Vercel 401 meaning](https://vercel.com/docs/ai-gateway/sdks-and-apis/openresponses).

Base: `main` at `b4ad7de4d494506d46bf4be4d297d5ca7e51c096` (PR #14, #16,
#15). Work branch: `codex/jev-shadow-pr15`. The older
`codex/jev-shadow-pilot` worktree remains intact and uncommitted.

## Scope decision

The pilot remains after the one-account verdict in `qualificar-conta`.
PR #15's `prospectar` is a fast triage that stores literal public quotations
without an account file or draft. Adding Jev there would expand the new
automatic path and duplicate its citation rule before showing a measured
benefit. A prospecting quotation can still be used as a labeled case.

Ported from the old worktree: the optional HTTP evaluator, the one-account
skill hook, local tests and pilot documentation. Adapted the hook to `ler.py`
and explicitly excluded `prospectar` and list triage. Added bounded
`source_type` and `attribution` fields to test weak sources and individual
stories; the original evaluator had no provenance field. Did not port the
old skill change verbatim or change any sending, onboarding, prospecting,
prompt, Docker or One Click Deploy code.

## Tests before the live attempt

- 31 search, `ler.py` and Jev tests passed before the request.
- 109 ledger tests passed, including the PR #14/#16 hardening tests.
- 5 draft versioning tests passed.
- `py_compile` and `git diff --check` passed.
- A diff against `main` showed no changes in the sending ledger and skill,
  `prospectar`, `ler.py`, prompt or Dockerfile.
- After improving HTTP error logging locally, 32 search, `ler.py` and Jev
  tests passed. No second live request was made.

## First live attempt

The ten fictional cases were labeled before the request; SHA-256 of
`tests/jev/cases.json` was
`fed231cd83cb1f3772f859c471c08b9d34cad8cfcbeb3b9de7714028d0cf78a0`.
The first case (`official_direct`) was sent in one real POST to the official
`/v1/systemone` endpoint using a key loaded only into that process. The
request returned `HTTPError` after 346 ms. The original adapter recorded the
error class but not the HTTP status, so its cause cannot be distinguished
from authentication, entitlement, validation or rate limiting. The request
produced no parsed Jev answer or usage record. The shadow path recorded
`milo_unchanged`. One real Jev request was attempted; no retry or other real
Jev request followed. Billed cost is unknown.

The adapter now records only an HTTP status code for a future attempt, with
no response body or credentials. A local test verifies that behavior. This
change cannot recover the status of the earlier request.

## OFF x SHADOW case register

The `OFF` column is the behavior required by the current Milo skills, **not
an observed result for these fictional inputs**. Existing PR #15 scenario
results did show Milo quoting a prospecting page while leaving employee count
unconfirmed, and refusing deep research when an inferred onboarding profile
had not been confirmed. No new Milo scenario was run for these ten inputs.

| Case | Expected evidence label | OFF rule | SHADOW observation |
|---|---|---|---|
| Official direct fact | supported | Cite opened page | HTTP error; no answer |
| Literal scoped year | supported | Preserve literal year | Not run |
| Weak aggregator | insufficient | Treat as lead, verify | Not run |
| Thin evidence | insufficient | Leave need unknown | Not run |
| Namesake | wrong_entity | Ask to disambiguate | Not run |
| Plausible inference | insufficient | Mark as hypothesis | Not run |
| Individual to company | insufficient | Do not generalize | Not run |
| Outreach readiness claim | insufficient | Contact remains unverified | Not run |
| Contradicted units | contradicted | Record contradiction | Not run |
| PR #15 prospecting quote | supported | Preserve literal citation | Not run |

No Jev confidence, probabilities, false-positive/negative rate or measured
incremental value are available. The planned experiment remains gated on a
successful single-request smoke test. No decision threshold can be calibrated
from this attempt.

## Current judgment

**NO VALUE demonstrated yet** means this run found no evidence of product
benefit, not that Jev cannot provide it. Keep the implementation shadow-only,
disabled by default, and off real users. Preserve the PR #14/#16 ledger
controls and PR #15 prospecting flow unchanged. The next investigation should
first determine the HTTP status on a separately authorized diagnostic retry;
only after a successful response should the pre-labeled cases be executed.
