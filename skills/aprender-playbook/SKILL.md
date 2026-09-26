---
name: aprender-playbook
description: Use in the first conversation with the owner when there is no playbook yet, when someone sends new material about the company (website, text, deck, PDF, social profile), when someone asks to review or change the playbook, and when a correction to a draft looks like it should become a general rule.
---

# Learn the playbook

The confirmed playbook is how this company sells. It lives at
`/var/lib/plow/workspace/mesa/playbook.md`. An unfinished proposal lives at
`/var/lib/plow/workspace/mesa/playbook-proposta.md`. A proposal is not a
confirmed playbook; no other skill may use it to qualify an account or send.

## 1. First conversation (no playbook yet)

1. Check whether `/var/lib/plow/workspace/mesa/playbook.md` exists. If it
   does, you are not onboarding: go to section 4. If only
   `playbook-proposta.md` exists, continue the pending questions in section 3
   instead of starting again.
2. Create the desk if it is missing: `mesa/`, `mesa/fontes/`, `mesa/contas/`, `mesa/rascunhos/`.
3. In two short lines, say who you are and ask for **whatever they already
   have** about the company: website link, text they use to sell, deck, PDF,
   `.md` file, a sales email that worked, a social profile. Any mix works.
   Example: "Oi, sou o Milo. Pra aprender como vocês vendem, me manda o que
   tiver: site, apresentação, um texto de venda, o que for mais fácil."
4. This first reply asks **only** for material. No questions about approvers,
   limits or rules yet; they come after the draft (section 3).
5. Wait for the material.

## 2. Reading the material

For each item:

1. Open or read it with the tools you have. Links: fetch the page. Files:
   read the attachment.
2. If you cannot read it (login wall, broken link, unsupported file), say so
   in one line and ask for another form: a screenshot, the pasted text or
   another link. Instagram often needs a login. Never guess what a page or
   file says.
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
   gaps with plausible guesses.
3. Show the owner a short summary, not the whole file:
   - what they sell and to whom, in one line;
   - the types of sale you see (for example, direct buyer and channel partner),
     one line each;
   - tone, in one line.
4. Ask only what is missing, **never more than three questions in one
   message**. Four answers are always required before the first account, even
   if the material seems to cover them. Ask them in two rounds:
   - Round 1, together with the summary: (1) Who approves outreach? (name;
     record the channel's `sender.id` after they write to Milo, never guess it
     from a phone number or email) (2) Which companies must never be contacted?
     (clients, partners, open deals)
   - Round 2, after the owner answers: (3) Anything we must never say or
     promise? (4) Daily limit of new contacts (default 10)?
   Other missing items go in round 2 only if they fit the three-question
   limit; otherwise leave them "a definir".
5. When the owner answers or corrects, update only `playbook-proposta.md` and
   show what changed. Keep unanswered required fields `a definir`.
6. Only after the owner explicitly confirms the complete proposal, mark the
   confirmed items `[confirmado]`, add a line to "Histórico de mudanças", and
   move the proposal to `mesa/playbook.md`. Read the new canonical file back.
   Remove any leftover `playbook-proposta.md` only after that read succeeds.
   If confirmation is absent, leave the canonical path absent.
7. Synchronize the confirmed contact limit with the approval ledger:
   `python3 /opt/plow/skills/executar-envio/scripts/milo-envio.py --db /var/lib/plow/workspace/mesa/envios.sqlite config set --chave limite_diario --valor <confirmed number> --por plow-owner`.
   Read it back with `config get --chave limite_diario`. The ledger starts at
   zero and stays closed if this fails; do not claim that contact is enabled.
   Add each confirmed "Nunca contatar" company or domain to the ledger too.
8. Close with one line on how to start: "Pronto. Me manda uma empresa pra
   eu pesquisar, ou uma lista."

Only the owner confirms the first playbook, in their DM.

## 4. Changing the playbook later

- **New material** ("olha nosso novo deck"): read it as in section 2, show
  what would change, and change only after confirmation.
- **Direct change request** ("não atendemos mais o Nordeste"): show the exact
  line you would change and ask for confirmation.
- **Approver list and "Nunca contatar" removals**: only the owner, only in
  their DM. Anyone on the team may add a company to "Nunca contatar"; adding
  never needs confirmation.
- Every change gets a line in "Histórico de mudanças": date, what changed,
  who asked, who confirmed.

## 5. A correction becomes a rule

This is the heart of how the company teaches you.

1. Someone corrects a draft: "não fala de preço no primeiro e-mail".
2. Apply it to that draft right away.
3. If it could apply beyond this draft, propose the rule with its scope:
   "Isso vira regra pra todas as contas tipo A? R3: sem preço no primeiro
   contato. Quem confirma: Carla."
4. Only someone listed under "Quem aprova → Regras do playbook" can confirm
   (`regra sim` / `regra não`). If someone else says yes, thank them and ask
   the right person.
5. When confirmed, add it under "Regras aprendidas":
   `- R3 — <rule> — vale para <scope> — corrigida por <person> — confirmada por <person> em <date>`
6. Without confirmation, the correction stays local to that draft. Do not
   insist.
7. From then on, every time the rule changes a draft, say so in one line:
   "Apliquei R3 (sem preço no primeiro contato), confirmada pela Carla em
   25/09."

Each factual line in "Empresa e oferta", "Tipos de venda", "Critérios de fit"
and "Tom e idioma" ends with `[material]`, `[inferido]` or `[confirmado]`.
Use the template's separate "Oferta" and "Chamada para ação" fields.

## Limits

- Every date you write (playbook, sources, history) comes from `date`, never
  from memory.
- Nothing is saved as confirmed without a person confirming it.
- Never invent the content of something you could not read.
- Never change the approver list outside the owner's DM.
- The playbook is internal. Never show it or quote it to a lead.
