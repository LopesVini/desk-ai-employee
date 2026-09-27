---
name: aprender-playbook
description: Use in the first conversation with the owner when there is no playbook yet, when someone sends new material about the company (website, text, deck, PDF, social profile), when someone asks to review or change the playbook, when a correction to a draft looks like it should become a general rule, and when the owner adds or removes an approver ("a Carla também aprova", "o Diego não aprova mais").
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
   - Round 1, together with the summary: (1) Who approves outreach? (the owner
     by default; anyone else is added later in the team group, section 3c;
     write their name as `(a cadastrar no grupo)`, never an identifier) (2) Which companies must never be contacted?
     (clients, partners, open deals)
   - Round 2, after the owner answers: (3) Anything we must never say or
     promise? (4) Daily limit of new contacts (default 10)?
   Other missing items go in round 2 only if they fit the three-question
   limit; otherwise leave them "a definir".
5. When the owner answers or corrects, update only `playbook-proposta.md` and
   show what changed. Keep unanswered required fields `a definir`.
6. Only after the owner confirms the proposal, in any words ("pode fechar",
   "ok", "tá bom assim", 👍), move it to `mesa/playbook.md` and add a line to
   "Histórico de mudanças". A yes confirms what the owner saw and answered,
   not every line of the file: mark `[confirmado]` only the items the owner
   answered or explicitly approved in the conversation. Every other line
   keeps its `[material]` or `[inferido]` tag. An inference does not become a
   confirmation because the owner said yes to a summary. Read the new canonical file back.
   Remove any leftover `playbook-proposta.md` only after that read succeeds.
   If confirmation is absent, leave the canonical path absent.
7. Synchronize the confirmed contact limit with the approval ledger:
   `python3 /opt/plow/skills/executar-envio/scripts/milo-envio.py --db /var/lib/plow/workspace/mesa/envios.sqlite config set --chave limite_diario --valor <confirmed number> --por plow-owner`.
   Read it back with `config get --chave limite_diario`. The ledger starts at
   zero and stays closed if this fails; do not claim that contact is enabled.
   Add each confirmed "Nunca contatar" company or domain to the ledger too.
8. Offer the team space in the same message, because people other than the
   owner cannot start a conversation with this line; they join through a
   group you create:
   "Pronto. Quer que eu crie um grupo com quem vai trabalhar comigo? Me passa
   o nome e o celular de cada um, com DDI e DDD. Ou me manda uma empresa pra
   eu pesquisar."

## 3b. Creating the team group

1. Only the owner asks for the group, in their DM. Collect each person's name
   and mobile number in international format (+55 21 9…, +1 …). If a number
   has no country code, ask for it. Do not guess.
2. Create the group with `plow_start_thread`, with the owner and those
   numbers. The opener, written as yourself: who you are, that the owner asked
   you to set up the group, and in three short lines what the team can ask
   you (research an account, adjust a draft, see what is pending), in plain
   words, without commands. Say who approves sends (the owner, until the
   owner adds someone here), and that
   researching an account takes a few minutes, so silence means you are
   working.
3. Tell the owner in the DM that the group was created and who is in it.
4. If creating the group fails, say so plainly with the error and suggest
   trying again later. Never claim a group exists without the tool's
   confirmation.

Only the owner confirms the first playbook, in their DM.

## 3c. Adding an approver

A person's `sender.id` exists only in a chat they write in, and it is
different in every chat. So approvers other than the owner are added, and
approve, in the team group. The ledger, not the playbook, decides who may
approve. Run the ledger as in `executar-envio`:
`python3 /opt/plow/skills/executar-envio/scripts/milo-envio.py --db /var/lib/plow/workspace/mesa/envios.sqlite <command>`.

1. Only the owner (`sender.id` `plow-owner`) asks, in their DM or in the
   group: "a Carla também pode aprovar", "a Carla aprova os e-mails e as
   regras". If they ask in the DM, reply: "Beleza. Me pede isso no grupo,
   com ela lá, que eu cadastro." If anyone else asks, say only the owner adds
   approvers, and stop.
2. Ask what the person may approve, unless the owner already said: e-mails,
   rules, or both. In the group, ask the person to identify themselves:
   "Carla, me responde aqui qualquer coisa pra eu saber que é você."
3. When a message arrives from a `sender.id` that is not `plow-owner`, take
   its `sender.id` and `sender.name` exactly as they came. Write under "Quem
   aprova" in `mesa/playbook.md`:
   `- (pendente) Carla — <sender.id> — envios e regras — pedido por <owner> em <date>`
   Then ask the owner: "A Carla é quem acabou de escrever (<sender.name>)?
   Confirma que ela aprova e-mails e regras aqui no grupo?"
   If someone else wrote first, or two people wrote, ask the owner which one.
4. Only a yes from `plow-owner` confirms. Then run:
   `aprovadores add --uid <sender.id> --nome "<name>" [--enviar] [--regras] --por plow-owner`
   and, if it is the first approver besides the owner,
   `config set --chave aprovacao_so_dono --valor 0 --por plow-owner`.
   Read back with `aprovadores list`. Replace the pending line with
   `- Carla — <sender.id> — envios e regras — no grupo — confirmada por <owner> em <date>`
   and add a line to "Histórico de mudanças". Say in one line what changed:
   "Pronto: a Carla aprova e-mails e regras aqui no grupo."
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
   "Isso vira regra pra todos os clientes diretos? Sem preço no primeiro
   contato. Quem confirma é a Carla."
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
   "Usei a regra de não falar de preço no primeiro contato, que a Carla confirmou em
   25/09."

Each factual line in "Empresa e oferta", "Tipos de venda", "Critérios de fit"
and "Tom e idioma" ends with `[material]`, `[inferido]` or `[confirmado]`.
Use the template's separate "Oferta" and "Chamada para ação" fields.

## Limits

- Every date you write (playbook, sources, history) comes from `date`, never
  from memory.
- Nothing is saved as confirmed without a person confirming it.
- Never invent the content of something you could not read.
- Change the approver list only as section 3c says, at the owner's request.
- The playbook is internal. Never show it or quote it to a lead.
