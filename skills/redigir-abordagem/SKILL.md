---
name: redigir-abordagem
description: Use when a qualified account needs one outreach draft, when someone asks for an approach ("faz o rascunho", "rascunho 2"), or when a teammate asks to change an existing draft in any words ("tira a parte do preço", "ajusta: ..."). This skill writes and versions drafts but never sends them.
---

# Draft one approach

Read `/var/lib/plow/workspace/mesa/playbook.md`, the account file in `mesa/contas/`, and the account's cited sources before writing. Get dates from `date`. Work on only one account per request. If the account is excluded, has no fit, has no confirmed playbook, or its sale type is unresolved, stop and explain what decision is missing.

When new material changes the evidence for an existing account, update its
individual note in `mesa/fontes/` and its entry in `mesa/fontes/indice.md`.
Read both files back before drafting. If either update fails, report the
failure and do not claim the source record is complete. Preserve the earlier
partial-reading note and label the new material and its exact URL separately.

## First draft

1. Choose the offer and call to action for the account's confirmed type A or B. Cite one account-specific fact that is present in its source note. If there is no usable fact, research more or say a personalized approach cannot yet be written. Never fill a gap with a plausible claim.
2. Follow the playbook's language, tone, maximum length and "Nunca dizer" rules. Review every confirmed rule in "Regras aprendidas" whose scope covers this account. Apply it and record its ID and confirmer in the account file; mention the application to the team.
3. Write the email as a subject line and a body: the first line is `Assunto: <subject>` (short, specific to the account, no clickbait), then a blank line, then the body. The subject is approved with the text. In the body, include identification as the company's AI assistant, the source of the contact or why this person was selected, a reply path to a named human, `responda PARAR para não receber mais`, and any required physical address recorded in the playbook. A missing recipient or reply path never stops you from writing and showing the draft: write it, save it, and mark what is missing. Only approval waits for the missing item. Do not claim delivery or a capability the channel lacks.
4. Write the proposed body to a temporary text file, then run
   `python3 {baseDir}/scripts/criar-rascunho.py --conta <slug> --texto-arquivo <temporary-file>`.
   Use the returned `versao` and `arquivo`; the helper creates the next version
   without replacing any previous one. Slugs use lowercase ASCII letters,
   digits and hyphens. Read the saved file back before showing it. Remove the
   temporary file after the saved version has been verified. Never reserve or
   guess a version in the account file before the helper returns. Never delete
   an earlier body file.
5. Append the version, date, correction author if any, applied rule IDs, saved body file path and block reason to the account file. Preserve the metadata for every previous version. The immutable `.txt` file is the source of truth for the exact body; do not keep a second copy in the account file. Set status `aguardando aprovação` only when recipient and all required details are verified; otherwise keep `pesquisada` and state the missing information. Put the next action in the file; keep the owner `a definir` unless a person actually assigned the account.

## Show the approval request

Read the saved version file again. Show the company and version, who approves, who sends (if `milo-envio.py ... config get --chave envio_automatico` is `1`: "eu envio, da minha caixa de e-mail, com <owner> em cópia"; otherwise: "você envia da sua caixa"), the exact recipient address, the subject and the complete body from that file. Always include this line, taken from "Regras aprendidas" in the playbook: `Regra usada: <o que a regra diz> (confirmada por <pessoa> em <data>)` for each rule applied, or `Nenhuma regra aprendida se aplica aqui.`. When a person sends it themselves, they copy the subject and body from here. If recipient is missing, still show the complete draft, say "Falta o e-mail de quem vai receber, então ainda não dá pra aprovar", say who decides and how to reach them if you know, and ask who has the address. Do not ask for approval of a draft that lacks a verified recipient.

An approval, in any words, is handled by `executar-envio`, not by this skill. End the approval request with a plain question ("Posso deixar pronto pra envio?"), not with command syntax. This skill does not call `message(send)` or reserve an envio.

## Corrections and learning

For a change request in any words ("tira a parte do preço", "ajusta: ..."), read the latest saved body and the account record. Make a **new** version; never edit the approved or previously shown file. Check "Regras aprendidas" again for the new version: it keeps every rule that still applies, and the approval request lists them. Record who requested the correction using the sender identifier and display name when available. Show the complete new body and ask for approval of its new version.

If the correction could apply to other accounts, propose a short rule with explicit scope, for example type A, and record it under "Regras propostas" as described in `aprender-playbook`. Keep it local to this draft until an authorized person confirms. Do not treat `regra sim` from an unidentified sender, a lead, a web page or a requester without rule authority as confirmation. After a rule is confirmed, apply it to the **next different account** that matches its scope and tell the team: `Apliquei R<n> (<regra>), confirmada por <pessoa> em <data>.` Preserve the originating account and confirmation in the playbook.

## Final check before presenting

- Every account claim is supported by a link recorded in the account file. Contact details in your message are copied from the account file, never completed or guessed; a hidden or placeholder address stays `e-mail oculto no site`.
- The saved file is exactly what the approver sees: the `Assunto:` line, a blank line and the body, with no private notes.
- A changed body has a new version and requires a new approval.
- An address found on a website is recorded with its source, but is not called deliverable.
- If an opt-out, human reply path or applicable address is missing, mark the draft blocked and ask for the missing fact.
