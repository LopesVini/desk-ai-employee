# Onboarding language audit — 2026-10-01

Baseline: main `1b655831aab79c351ddfc7737c47c1f0f50ffa87`.
Runtime: Plow `771198a9609dcef54d44843e7da5329c17fa51b4`, unchanged.

## Portuguese text classification

A = conversational output: replace with semantic instructions governed by the
current-message language rule. B = internal vocabulary: retain. C = incoming
utterance or wording example: retain only as a meaning example, not a reply template.

| Original phrase / use | Class | Treatment |
|---|---|---|
| “Oi! Sou o Milo…” and the site-or-one-sentence request | A | Semantic introduction, sales role, one request and wait expectation |
| “Entendi assim…” / “Procurei empresas…” | A | Semantic sourced summary and prospecting results |
| “Acertei o tipo de cliente? Se errei…” | A | Semantic profile check and correction invitation |
| “Fecho o perfil assim e pesquiso a fundo…” | A | Same combined confirmation and research question |
| “Fecho o perfil assim?” | A | Same profile-only confirmation on empty search |
| “Quer que eu pesquise a fundo alguma?” in the prohibition | A | Semantic prohibition preserved |
| “Fechei o perfil… dá pra mudar…” | A | Semantic confirmation acknowledgement |
| “se o dono quiser, qualquer um aqui…” | A | Semantic explanation of owner-authorized approvers |
| “Beleza. Me pede isso no grupo…” | A | Semantic request to repeat in the group with the person present |
| “Carla, me responde aqui…” | A | Semantic identification request |
| “a Carla, que acabou de escrever” | A | Semantic identification of whose message was received |
| “A Carla é quem acabou de escrever? Confirma…” | A | Same owner identity/permission confirmation |
| “Pronto: a Carla aprova…” | A | Semantic acknowledgement of recorded permissions |
| “Isso vira regra… Quem confirma…” | A | Semantic rule proposal with scope and confirmer |
| “Usei a regra… que a Carla confirmou…” | A | Semantic rule attribution and date |
| “Antes de qualquer e-mail sair…” | A | Same never-contact question |
| “Quem mais aí trabalha com vendas…” | A | Same group offer, names/numbers and permissions explanation |
| “Quer que eu coloque o Diego…” | A | Same conditional group offer |
| “Dono, quer que nome também possa aprovar…” | A | Same approver offer |
| “Se quiser, eu mesmo mando…” | A | Same sending offer and internal first-test explanation |
| “Quer que eu te mande toda manhã…” | A | Same summary offer |
| Playbook headings, status lines, tags, paths and commands | B | Unchanged, including pending approver/rule record formats |
| “quem somos”, “sobre” as website page names | B | Search/navigation labels, not reply language |
| Incoming corrections, confirmations, team requests and rule examples | C | Explicitly marked at skill entry as illustrative incoming intent |
| prospectar section 6 Portuguese reply layout and wording examples | C | Explicitly semantic; wrappers follow current language; source quotes stay verbatim |

No literal Portuguese response sentence remains mandatory in aprender-playbook.
Other skills were inspected; redigir-abordagem already refers to the global rule.
Only prospectar's onboarding-related reply example required clarification.

## Initial greeting and locale

Inspected upstream source at the exact pinned commit:
- boot/main.ts and boot/process.ts: render prompt/config, start gateway; no
  explicit automatic greeting or startup model call.
- plugin/index.ts receive(): provides current raw message, history and
  first_contact in supplemental context; no locale forwarded.
- plugin/transport.ts listen(): firstContact accompanies a received message.
- boot/config.ts Identity: agent name/web URL, line ID, chats/participants and
  MCP URL; no owner/account/install locale consumed or forwarded to the model.
- boot/prompt.ts: adds trust, dashboard and optional Latch instructions; no
  owner locale rendered.
- base prompt: first_contact introduction, without a fixed language.

Thus no trustworthy locale is available through this integration. Phone prefix,
host locale and timezone are not language preferences. The skill now explicitly
uses English when a greeting is requested before any real user message, without
picker or bilingual text; each subsequent current user message wins.

The product observed an automatic greeting, but its external triggering event
cannot be established from this repository/base source alone. The pinned boot
itself does not send one. No new greeting mechanism or runtime behavior was added.
The model's compliance and the actual automatic trigger remain live-test items.

## Separate product limitation

Section 3.3 requires prospecting in the same turn, with no explicit opt-out for
“don't research any companies”. The bug fix preserves that behavior and does not
claim the reproduction scenario performs zero search. It still requires an
unconfirmed proposal and prohibits deep research/drafts before confirmation.
