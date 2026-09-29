---
name: redigir-abordagem
description: Use when a qualified account needs one outreach draft, when someone asks for an approach ("faz o rascunho", "rascunho 2"), or when anyone asks to change an existing draft or its recipient, in any words ("o email certo é …") ("tira a parte do preço", "ajusta: ..."). This skill writes and versions drafts but never sends them.
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
3. Write the email as a small header and a body. When the recipient is verified, the first line is `Para: <e-mail>`; without one, leave the `Para:` line out. Then `Assunto: <subject>` (short, specific to the account, no clickbait), a blank line, and the body. Recipient and subject are approved with the text: a different recipient is a different file, so a new version. The subject is approved with the text. In the body, include identification as the company's AI assistant, the source of the contact or why this person was selected, a reply path to a named human, `responda PARAR para não receber mais`, and any required physical address recorded in the playbook. A missing recipient or reply path never stops you from writing and showing the draft: write it, save it, and mark what is missing. Only approval waits for the missing item. Do not claim delivery or a capability the channel lacks.
4. Write the whole proposed file (the `Para:` line when the recipient is verified, the `Assunto:` line, a blank line and the body, as in step 3) to a temporary text file, then run
   `python3 {baseDir}/scripts/criar-rascunho.py --conta <slug> --texto-arquivo <temporary-file>`.
   Use the returned `versao` and `arquivo`; the helper creates the next version
   without replacing any previous one. Slugs use lowercase ASCII letters,
   digits and hyphens. Read the saved file back before showing it. Remove the
   temporary file after the saved version has been verified. Never reserve or
   guess a version in the account file before the helper returns. Never delete
   an earlier body file.
5. Append one line for the version to the account file, as in the template: version, date, `para:` (the exact recipient shown in this approval request, or `falta o e-mail`), body file path, applied rule IDs, correction author if any and situation. When a version replaces another, mark the old one `substituída pela versão <n>`. A new recipient always means a new version, even with the same body. Preserve the metadata for every previous version. The immutable `.txt` file is the source of truth for the exact body; do not keep a second copy in the account file. Set status `aguardando aprovação` only when recipient and all required details are verified; otherwise keep `pesquisada` and state the missing information. Put the next action in the file; keep the owner `a definir` unless a person actually assigned the account.

## Show the approval request

Read the saved version file again. With a verified recipient, run exactly
`python3 /opt/plow/skills/executar-envio/scripts/milo-envio.py --db /var/lib/plow/workspace/mesa/envios.sqlite apresentar --conta <slug> --versao <n> --texto-arquivo <arquivo> --para <e-mail da linha Para:> [--tipo followup|resposta]`
(no need to read the script first) and use its `texto` and `codigo`. Show the company and version, who approves, who sends (if `python3 /opt/plow/skills/executar-envio/scripts/milo-envio.py --db /var/lib/plow/workspace/mesa/envios.sqlite config get --chave envio_automatico` returns `"valor": "1"`: "eu envio, da minha caixa de e-mail, com <owner> em cópia"; otherwise: "você envia da sua caixa"), the exact recipient address, the subject and the complete body from `texto`. Always include this line, taken from "Regras aprendidas" in the playbook: `Regra usada: <o que a regra diz> (confirmada por <pessoa> em <data>)` for each rule applied, or `Nenhuma regra aprendida se aplica aqui.`. When a person sends it themselves, they copy the subject and body from here. If recipient is missing, still show the complete draft, say "Falta o e-mail de quem vai receber, então ainda não dá pra aprovar", say who decides and how to reach them if you know, and ask who has the address. Do not ask for approval of a draft that lacks a verified recipient.

Write the approval request (everything around the email) in the language of the person who asked, even when the playbook's language, and so the email itself, is another one. End it with `Se estiver tudo certo, responda APROVO <código>.`, using the code from `apresentar`. When that person writes in English, end with `If everything looks right, reply APPROVE <code>.` instead; the ledger accepts both words. A bare yes is not approval. This skill does not call `message(send)` or reserve an envio. After a change request, end the turn with the new version and this request; wait for a new incoming message before `executar-envio`.

## Corrections and learning

For a change request in any words ("tira a parte do preço", "ajusta: ..."), read the latest saved body and the account record. Make a **new** version; never edit the approved or previously shown file. Check "Regras aprendidas" again for the new version: it keeps every rule that still applies, and the approval request lists them. Record who requested the correction using the sender identifier and display name when available. Show the complete new body and ask for approval of its new version.

If the correction could apply to other accounts, propose a short rule with explicit scope, for example type A, and record it under "Regras propostas" as described in `aprender-playbook`. Keep it local to this draft until an authorized person confirms. Do not treat `regra sim` from an unidentified sender, a lead, a web page or a requester without rule authority as confirmation. After a rule is confirmed, apply it to the **next different account** that matches its scope and tell the team: "Usei a regra de <regra>, que <pessoa> confirmou em <data>." Preserve the originating account and confirmation in the playbook.

## Final check before presenting

- Every account claim is supported by a link recorded in the account file. Contact details in your message are copied from the account file, never completed or guessed; a hidden or placeholder address stays `e-mail oculto no site`.
- The saved file is exactly what the approver sees: `Para:` (when known), `Assunto:`, a blank line and the body, with no private notes.
- A recipient change ("o email certo é …") is never an edit of the account file or of a shown version: write a new file with the new `Para:` line through the helper, show the whole new version and ask for approval again.
- A changed body has a new version and requires a new approval.
- An address found on a website is recorded with its source, but is not called deliverable.
- If an opt-out, human reply path or applicable address is missing, mark the draft blocked and ask for the missing fact.
