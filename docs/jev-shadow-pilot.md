# Jev shadow pilot: public claim support

This pilot starts from `main` at `b4ad7de4d494506d46bf4be4d297d5ca7e51c096`
(PR #14, #16 and #15). It evaluates evidence after Milo
has formed and saved a one-account verdict. It does not alter Milo's verdict,
draft, next action, approval, or sending. List triage and private CRM evidence
are outside this pilot. `prospectar` keeps its own cited-fact and onboarding
rules; this pilot does not add a call to that skill.

## Enable locally

The default is off. To opt into the shadow experiment in a test installation,
set `JEV_ENABLED=1`, `JEV_MODE=shadow` and `TYPESAFE_API_KEY` in that
installation's private runtime environment. `JEV_TIMEOUT_SECONDS` defaults to
2.5 and is capped at 5. No SDK or package installation is needed. Do not put
the key in this repository, a scenario fixture or the input JSON.

The `milo-jev-shadow` OpenClaw plugin observes changes to
`mesa/contas/<slug>.md` across a completed agent turn. When enabled, it starts
an independent post-step after the turn; Milo does not need to call a script.
The plugin config explicitly grants `hooks.allowConversationAccess`, which
OpenClaw requires for these two conversation lifecycle events in local plugins.
The post-step requires a saved `## Veredito` with `bom fit`, `incerto` or
`sem fit` and a numbered reason matched to a short literal public excerpt
and HTTPS URL in `## Fatos (com fonte)`. If none is eligible, it does nothing.
It writes a private temporary JSON input with this shape:

```json
{
  "account": "example-company",
  "verdict": "incerto",
  "claims": [
    {
      "claim": "A empresa opera três unidades no Rio.",
      "source_excerpt": "Operamos três unidades na cidade do Rio de Janeiro.",
      "source_url": "https://example.com/sobre",
      "source_type": "official_company_page",
      "attribution": "company"
    }
  ]
}
```

The post-step selects at most two factual claims and excerpts from the saved
card. It uses the existing input validation, keeps the network timeout bounded,
and records each account/verdict/claim/source combination once using a local
file lock and hashes in the shadow log. A repeated turn with the same evidence
does not call TypeSafe again. Failed calls are also recorded once; a later
retry requires a changed claim or source.
The `source_type` and `attribution` fields identify whether a passage comes
from the company's own page or a third party and whether it describes the
company, an individual, another entity or an unclear subject. They are
metadata supplied by Milo, not independently verified facts. The script also
accepts `search_snippet` for offline evaluation of a known weak-source case;
the live skill never sends a search snippet as evidence.
The script rejects oversized input and email addresses or phone numbers in
claims/excerpts. It sends only each claim, excerpt, source hostname and these
two metadata fields to
TypeSafe's direct `/v1/systemone` endpoint,
using the documented `jev-1.13.0` model and asking a Choice question with
`supported`, `contradicted`, `insufficient` and `wrong_entity`. The full source
URL, account identifier, verdict, contacts and playbook are not sent. Its
guardrails cannot prove that submitted text is public; the operator must check
that before enabling the pilot.

`/var/lib/plow/workspace/mesa/jev-shadow.jsonl` holds the local comparison
record with the existing Milo verdict, source hostname, hashes of the claim,
excerpt and URL, Jev's Choice distributions and confidence, model, HTTP status,
token usage,
duration, applied decision (`milo_unchanged`) and error status. The record
omits raw source text and the API key. The detached post-step has no path to
modify the account, response, drafts, approval, sending, or ledger. Its
stdout/stderr are suppressed. A timeout, unavailable API, missing key,
invalid response or missing log path leaves qualification unchanged.

The first full-turn smoke test before this hook took about 22 minutes in
prospecting and did not call Jev. That prospecting latency is tracked
separately; a short hook smoke should qualify an already named company.

## Compare OFF and shadow

Use the same PR #13 image, playbook snapshot, account inputs and source
material for both conditions. Label each claim independently as supported,
contradicted, insufficient or wrong entity. Start with the Prossigo cases of
weak sources and namesakes, plus the repository's `fit-sem-contato`, `decisor`
and `fit-com-rascunho` scenarios. Record Milo's verdict, the label, Jev's
distribution, time and token usage. A shadow run cannot establish that Jev
changes behavior; it tests whether its signal identifies Milo's mistakes.

Do not select a confidence threshold from a few examples. After collecting
more labeled cases, compare error detection at each review rate, calibration
within confidence bands, and performance on held-out Portuguese cases. Move
to an active gate only if it reduces unsupported claims without blocking a
material share of correct qualifications. Approval and sending always remain
with the existing ledger.

Provider contract: [TypeSafe's API reference](https://docs.typesafe.ai/api)
documents the endpoint, bearer authentication, Choice answer shape and token
usage. [Current models](https://docs.typesafe.ai/models) lists `jev-1.13.0`
at $0.042 per million input tokens, with output tokens free. The direct API
response does not document a billed-cost field; any cost calculated from token
usage and that list price is an estimate.
