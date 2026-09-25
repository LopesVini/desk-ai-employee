---
name: aprender-playbook
description: Use in the first conversation with the owner when there is no playbook yet, when someone sends new material about the company (website, text, deck, PDF, social profile), when someone asks to review or change the playbook, and when a correction to a draft looks like it should become a general rule.
---

# Learn the playbook

The playbook is how this company sells. You build it from whatever the owner
already has, ask only what the material does not answer, and change it only
with confirmation. It lives at `/var/lib/plow/workspace/mesa/playbook.md`.

## 1. First conversation (no playbook yet)

1. Check whether `/var/lib/plow/workspace/mesa/playbook.md` exists. If it
   does, you are not onboarding: go to section 3 or 4.
2. Create the desk if it is missing: `mesa/`, `mesa/fontes/`, `mesa/contas/`.
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
4. Add a line to `mesa/fontes/indice.md`:
   `- <date> — <what it is> — sent by <person> — <link or file> — <what you took from it>`

## 3. Proposing the playbook

1. Draft the playbook with the template below. For every statement, mark
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
   - Round 1, together with the summary: (1) Who approves outreach? (name and
     phone number or email) (2) Which companies must never be contacted?
     (clients, partners, open deals)
   - Round 2, after the owner answers: (3) Anything we must never say or
     promise? (4) Daily limit of new contacts (default 10)?
   Other missing items go in round 2 only if they fit the three-question
   limit; otherwise leave them "a definir".
5. When the owner answers or corrects, update the draft and show what changed.
6. When the owner confirms, save `mesa/playbook.md`, mark confirmed items
   `[confirmado]`, and add a line to "Histórico de mudanças".
7. Close with one line on how to start: "Pronto. Me manda uma empresa pra
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

## Playbook template

```markdown
# Playbook — <empresa>
Última atualização: <data> por <pessoa>
Fontes: ver fontes/indice.md

## Empresa e oferta
- O que vendemos: ...
- Para quem resolve o quê: ...
- Diferenciais que podemos citar: ...
- O que NÃO podemos prometer: ...

## Tipos de venda
### Tipo A — <nome>
- Perfil ideal: ...
- Quem decide: ...
- Oferta e chamada para ação: ...
### Tipo B — <nome>
- Perfil ideal: ...
- Quem decide: ...
- Oferta e chamada para ação: ...

## Critérios de fit
- Bom fit quando: ...
- Descartar quando: ...
- Sinais de prioridade: ...
- Pede julgamento humano: ...

## Tom e idioma
- Idioma das abordagens: ...
- Tom: ...
- Tamanho máximo do primeiro e-mail: ...
- Exemplos aprovados: ...

## Regras de contato
- Limite de novas abordagens por dia: 10
- Remetente e assinatura: Milo, assistente de IA da <empresa>
- Respostas vão para: <e-mail de um humano>
- Endereço físico (só pilotos nos EUA): ...
- Envio de teste feito: não

## Nunca contatar
- <empresa ou domínio> — <motivo>

## Nunca dizer
- ...

## Quem aprova
- Envios: <nome> — <telefone ou e-mail>
- Regras do playbook: <nome> — <telefone ou e-mail>

## Regras aprendidas
- (nenhuma ainda)

## Histórico de mudanças
- <data> — <mudança> — pedida por <pessoa> — confirmada por <pessoa>
```

Each line in "Empresa e oferta", "Tipos de venda", "Critérios de fit" and
"Tom e idioma" ends with `[material]`, `[inferido]` or `[confirmado]`.

## Limits

- Every date you write (playbook, sources, history) comes from `date`, never
  from memory.
- Nothing is saved as confirmed without a person confirming it.
- Never invent the content of something you could not read.
- Never change the approver list outside the owner's DM.
- The playbook is internal. Never show it or quote it to a lead.
