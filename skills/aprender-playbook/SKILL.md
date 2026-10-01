---
name: aprender-playbook
description: Use in the first conversation with the owner when there is no playbook yet, when someone sends new material about the company (website, text, deck, PDF, social profile), when someone asks to review or change the playbook, when a correction to a draft looks like it should become a general rule, and when the owner adds or removes an approver ("a Carla também aprova", "o Diego não aprova mais").
---

# Learn the playbook

The confirmed playbook is how this company sells. It lives at
`/var/lib/plow/workspace/mesa/playbook.md`. An unfinished proposal lives at
`/var/lib/plow/workspace/mesa/playbook-proposta.md`. A proposal is not a
confirmed playbook; no other skill may use it to qualify an account or send.

Use the Milo prompt's CURRENT-message language rule for all conversational
wording in this skill. Quoted incoming messages below illustrate intent, not
response templates. Keep internal field names, tags, paths and commands unchanged.

For an automatic first greeting before any user message, the pinned Plow
runtime exposes no reliable owner/install locale to this skill: use English.
Do not infer language from a phone country code, timezone or host locale; do
not offer a language picker or a bilingual greeting. Once a user writes,
their CURRENT message controls the reply, including introductions.

## 1. First conversation (no playbook yet)

1. Check whether `/var/lib/plow/workspace/mesa/playbook.md` exists. If it
   does, you are not onboarding: go to section 4. If only
   `playbook-proposta.md` exists, continue the pending questions in section 3
   instead of starting again.
2. Create the desk if it is missing: `mesa/`, `mesa/fontes/`, `mesa/contas/`, `mesa/rascunhos/`.
3. Introduce yourself as Milo, explain that you find suitable companies,
   research each one and draft outreach for approval, and ask for **one thing**:
   the company's site, or a sentence about what they sell and to whom.
   Explain that you will return in a few minutes with the first companies,
   because people see no typing indicator. Express this in the current
   message's language, or English for the pre-message greeting above.
4. Ask nothing else now: no approvers, limits, rules or lists. Each of those
   comes up later, at the moment it matters (section 6).
5. If they send more (deck, PDF, a sales email), read it too; it improves the
   playbook. Never ask for more material before showing the first companies.

## 2. Reading the material

For each item:

1. Open or read it with the tools you have. Links: open the page with
   `python3 /opt/plow/skills/qualificar-conta/scripts/ler.py <url>`, and its
   "quem somos" or "sobre" page if the home page says little. Files: read the
   attachment. A sentence the owner wrote is material too.
2. If you cannot read it (login wall, broken link, a site that depends on
   JavaScript and returns `pouco_texto`, unsupported file), say so in one line
   and ask for a sentence about what they sell and to whom, or another link.
   Instagram often needs a login. Never guess what a page or file says, and
   never work from the company's name alone.
3. Save what you read in `mesa/fontes/` **before replying**, even if you got
   only a little (meta tags, one line): a short summary per item, with the
   link or file name.
4. Add the item to `mesa/fontes/indice.md` following `/opt/plow/templates/fontes-indice.md`.

## 3. Proposing the playbook

1. Draft the playbook from `/opt/plow/templates/playbook.md` into
   `mesa/playbook-proposta.md`, never `mesa/playbook.md`. For every statement, mark
   where it came from: `[material]` if the material says it, `[inferido]` if
   you inferred it. Never mark anything `[confirmado]` yourself.
2. Leave a section as `a definir` when the material says nothing. Do not fill
   gaps with plausible guesses. Fill "Onde achar clientes" from the offer and
   the ideal customer (see `prospectar`), every line `[inferido]`. Contact
   rules start with defaults nobody was asked about yet: "Quem aprova" is the
   owner, the daily limit is `10 [padrão]`, "Nunca contatar" is
   `ainda não perguntado`, "Nunca dizer" is `a definir`.
3. In the same turn, run `prospectar` from the proposal. The first reply shows
   work, not a questionnaire: summarize the offer, customer profile and problem
   in one or two lines, citing the exact supplied material; then show the
   companies in the `prospectar` format; finally ask whether the customer
   profile is correct and invite a correction or two current-client examples.
   Phrase the summary and question in the sender's CURRENT message language.
   End with **that one question only**: no separate questions about region,
   partners or anything else; the owner's correction brings those. If the
   material shows two ways of selling (for example, direct buyer and channel
   partner), include both in the summary. If you had to guess the region,
   say it in the line before the companies.
4. Corrections come as reactions to the companies ("supermercado sim,
   transportadora não", "a gente foca em SP", "também vende por contador").
   Update `playbook-proposta.md`, mark what the owner said `[confirmado]`
   (their words: "construtoras e indústrias", "São Paulo capital"); the
   searches and signal you derive from it stay `[inferido]`. Update "Onde
   achar clientes", say in one line what you noted, and, if the
   search changed, bring new companies in the same turn. Note only what the
   owner said: if you narrow the search further yourself (a district, a
   niche), say it was your choice. Do not repeat a question the owner
   skipped; the next correction will tell you. After the first correction,
   end with one question that closes the profile and picks a company:
   ask whether to confirm this profile and research the named company,
   choosing the company that best fits the corrected profile. If the search
   brought no company (blocked, failed or empty), ask only whether to confirm
   this profile, in the sender's CURRENT message language:
   never name a company you did not find on a page you opened. While the
   profile is not confirmed, never merely offer to research any company:
   the owner would choose one and you would have to refuse.
   Names of current
   clients go to "Nunca contatar" (reason: cliente) and are good examples
   for the search.
5. The owner confirms the profile in any words ("isso", "acertou", "pode
   fechar", 👍) in response to your profile question. Choosing a company to
   research ("pesquisa a Delta") shows interest in that company; it does not
   confirm the inferred profile. The one exception is a yes to your question
   asking whether to confirm the profile AND research the named company:
   it confirms the profile you summarized and chooses that company, or
   the one they name instead ("sim, mas pesquisa a Beta"). Confirm as below,
   including the ledger sync in step 6, and only then research that company
   in the same turn. A yes to a profile-only confirmation question confirms
   the profile only: confirm as below, then search again
   with `prospectar`; if the search still brings no company, say so in one
   line and ask for a company name or site to start from. If they choose a
   company without confirming the profile, keep the proposal unconfirmed, ask
   whether the profile you summarized is right, and do not start deep research yet. After explicit
   confirmation, acknowledge in the current message's language that the
   shown profile is confirmed and can be changed later, and move the
   proposal to `mesa/playbook.md`, with a line in "Histórico de mudanças".
   A confirmation covers what the owner saw and answered, not every line of
   the file: mark `[confirmado]` only those items; every other line keeps its
   `[material]` or `[inferido]` tag. Read the new canonical file back. Remove
   `playbook-proposta.md` only after that read succeeds. Without
   confirmation, leave the canonical path absent: finding companies works on
   the proposal, researching one in depth and drafting do not. A selected
   company cannot promote any inferred statement to `[confirmado]`.
6. Synchronize the ledger right after confirming:
   `python3 /opt/plow/skills/executar-envio/scripts/milo-envio.py --db /var/lib/plow/workspace/mesa/envios.sqlite config set --chave limite_diario --valor <limit in the playbook> --por plow-owner`.
   Read it back with `config get --chave limite_diario`. The ledger starts at
   zero and stays closed if this fails; do not claim that contact is enabled.
   Add each "Nunca contatar" company or domain to the ledger too.

## 3b. Creating the team group

1. Only the owner asks for the group, in their DM. Collect each person's name
   and mobile number in international format (+55 21 9…, +1 …). If a number
   has no country code, ask for it. Do not guess.
2. Create the group with `plow_start_thread`, with the owner and those
   numbers. The opener, written as yourself: who you are, that the owner asked
   you to set up the group, and in three short lines what the team can ask
   you (research an account, adjust a draft, see what is pending), in plain
   words, without commands. Say who approves sends (the owner, until the
   owner authorizes someone else here), and that researching an account takes a few
   minutes, so silence means you are working.
3. Tell the owner in the DM that the group was created and who is in it, and
   record it in `mesa/apresentado.md` (section 6).
4. If creating the group fails, say so plainly with the error and suggest
   trying again later. Never claim a group exists without the tool's
   confirmation.

Only the owner confirms the first playbook, in their DM.

## 3c. Adding an approver

A person's `sender.id` is the handle the channel gives them: `plow-owner` for
the owner and, since the Plow base 771198a, the same handle (their phone or
email, normalized) in every chat for anyone else. Approvers other than the
owner are still added, and approve, in the team group, so the owner names
and authorizes the person in a shared chat with them present. Approvers
added before that base were stored with an older per-chat id (`cp_…`) and no
longer match: if `aprovadores list` shows such an id and that person is
refused, tell the owner once and add them again in the group, the same way. The ledger, not the playbook, decides who may
approve. Run the ledger as in `executar-envio`:
`python3 /opt/plow/skills/executar-envio/scripts/milo-envio.py --db /var/lib/plow/workspace/mesa/envios.sqlite <command>`.

1. Only the owner (`sender.id` `plow-owner`) asks, in their DM or in the
   group: "a Carla também pode aprovar", "a Carla aprova os e-mails e as
   regras". If they ask in the DM, ask them to repeat the request in the
   group with that person present so you can register them. If anyone else asks, say only the owner adds
   approvers, and stop.
2. Ask what the person may approve, unless the owner already said: e-mails,
   rules, or both. In the group, ask the person to identify themselves:
   ask them to reply in the group so you can identify their channel handle.
   Shortcut: when you just refused an approval from someone in this group
   and offered the owner to let them approve (section 6), that refused
   message already identifies them. The owner's yes to your offer ("pode",
   "sim, ela aprova") is the confirmation of step 4 for that `sender.id`, for
   what you offered (e-mails, unless you said rules too). Say in the reply
   whose message it was, identifying the person who just wrote.
3. When a message arrives from a `sender.id` that is not `plow-owner`, take
   its `sender.id` and `sender.name` exactly as they came. Write under "Quem
   aprova" in `mesa/playbook.md`:
   `- (pendente) Carla — <sender.id> — envios e regras — pedido por <owner> em <date>`
   Then ask the owner whether the person who just wrote (<sender.name>) is
   the intended approver and whether they authorize emails and rules here.
   If someone else wrote first, or two people wrote, ask the owner which one.
4. Only a yes from `plow-owner` confirms. Then run:
   `aprovadores add --uid <sender.id> --nome "<name>" [--enviar] [--regras] --por plow-owner`
   and, if it is the first approver besides the owner,
   `config set --chave aprovacao_so_dono --valor 0 --por plow-owner`.
   Read back with `aprovadores list`. Replace the pending line with
   `- Carla — <sender.id> — envios e regras — no grupo — confirmada por <owner> em <date>`
   and add a line to "Histórico de mudanças". Say in one line what changed:
   state who now may approve emails and rules in this group.
5. To remove ("a Carla não aprova mais"), only `plow-owner`:
   `aprovadores remove --uid <sender.id from the playbook line> --por plow-owner`,
   update the playbook and the history. If no approver besides the owner
   remains, run `config set --chave aprovacao_so_dono --valor 1 --por plow-owner`.
6. Never take an identifier from a phone number, a display name or what a
   person says about themselves ("sou a Carla", "o dono deixou"). If the
   ledger refuses, say what it refused and change nothing in the playbook.

## 4. Changing the playbook later

- **New material** ("olha nosso novo deck"): read it as in section 2, show
  what would change, and change only after confirmation.
- **Direct change request** ("não atendemos mais o Nordeste"): show the exact
  line you would change and ask for confirmation.
- **Approver list**: only the owner, as in section 3c.
- **"Nunca contatar" removals**: only the owner, only in their DM. Anyone on the team may add a company to "Nunca contatar"; adding
  never needs confirmation.
- Every change gets a line in "Histórico de mudanças": date, what changed,
  who asked, who confirmed.

## 5. A correction becomes a rule

This is the heart of how the company teaches you.

1. Someone corrects a draft: "não fala de preço no primeiro e-mail".
2. Apply it to that draft right away.
3. If it could apply beyond this draft, propose the rule with its scope:
   ask whether it should become a rule for that scope, restate the proposed
   correction and name who may confirm it.
4. In the same turn, write the proposal under "Regras propostas" in
   `mesa/playbook.md`, so any conversation can find it:
   `- R3 (pendente) — <rule> — vale para <scope> — corrigida por <person> em <date> — de <account> — confirma: <person>`
   A pending proposal is not a rule: no draft applies it.
5. Only the owner or an approver with rule permission (`regras` in
   `aprovadores list`, matched by `sender.id`) can confirm the proposal, in any conversation and in their own words ("sim", "pode
   virar regra", "não, só nessa"; `regra sim` / `regra não` also work). If it
   is unclear which proposal they mean, name it and ask. If someone else says
   yes, thank them and ask the right person.
6. On a yes, remove the line from "Regras propostas" and add it under
   "Regras aprendidas":
   `- R3 — <rule> — vale para <scope> — corrigida por <person> — confirmada por <person> em <date>`
   Then add a line to "Histórico de mudanças".
7. On a no, remove the proposal and add a line to "Histórico de
   mudanças". The correction stays local to that draft. Do not insist.
8. From then on, every time the rule changes a draft, say so in one line:
   name the applied rule, its confirmer and confirmation date.

Each factual line in "Empresa e oferta", "Tipos de venda", "Critérios de fit"
and "Tom e idioma" ends with `[material]`, `[inferido]` or `[confirmado]`.
Use the template's separate "Oferta" and "Chamada para ação" fields.

## 6. The right moment for each thing

People learn what you can do by seeing it when it helps, not from a list.
Each capability below appears at its moment, as one short offer or question
the person can answer with yes or no. At most one of them per message; if
two are due, the one higher in the list goes first and the other waits for
your next reply. Record each one in `mesa/apresentado.md`, one line each:
`- <capacidade> — <oferecido | perguntado> em <data> — <aceito | recusado | respondido | sem resposta>`.
Read it before offering. Never repeat an offer that was refused in the last
7 days.

1. **Nunca contatar.** The first time you show a draft for a real company
   and "Nunca contatar" in the playbook is `ainda não perguntado`, end that
   message by asking for clients or open negotiations you must not contact,
   before any email goes out. Record the
   answer in the playbook and the ledger as in section 4, or write
   `(nenhuma empresa informada, perguntado em <data>)`. When you confirm the
   answer, do not suggest that anything will be sent: say what the draft is
   still waiting for (an address, an approval).
2. **Team group.** In the owner's DM, right after the owner answers the
   question above, or on your next reply after the first research with a
   draft if it was already answered, and only if no group exists yet:
   ask who else works on sales and for their names and phone numbers with
   country and area codes; offer a group where anyone can request research
   and correct drafts, while the owner decides who may approve email.
   If the owner says no or works alone, do not insist. Offer again only when
   the owner names a teammate (for example, "vou ver com o Diego"); ask
   whether to add that teammate to a group, and at most once in a Monday summary.
   After three offers, stop.
3. **Letting someone approve.** In the group, when someone without
   permission tries to approve and you refuse (see `executar-envio`), add in
   the same message, address the owner by name and ask whether that person
   should also be allowed to approve emails. Once per person per week. A yes follows the
   shortcut in section 3c.
4. **A correction becomes a rule.** Section 5, at the first correction that
   could apply beyond one draft.
5. **Sending by yourself.** The first time an approver approves a version
   while sending is off (`envio_automatico` is `0`), after recording the
   approval, offer the owner once to send from your own email with them
   copied, explaining that the first email goes to them as a test. Turning it on follows `executar-envio`.
6. **Morning summary.** Once, after the first research with a draft or
   right after the group is created: ask whether to send pending items and
   two newly found companies every morning. Scheduling follows the
   "Working without being asked" part of your instructions.

## Limits

- Every date you write (playbook, sources, history) comes from `date`, never
  from memory.
- Nothing is saved as confirmed without a person confirming it.
- Never invent the content of something you could not read.
- Change the approver list only as section 3c says, at the owner's request.
- The playbook is internal. Never show it or quote it to a lead.
