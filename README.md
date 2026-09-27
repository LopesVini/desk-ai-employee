# Milo

**The first sales hire that learns how your team sells.**

Teach Milo how your company sells. He researches each account with sources,
learns the rules your team confirms, and sends only the emails someone with
authority approved. He works where the team already talks: a text thread with
the owner and a group chat with the team. There is no new app to open. He
replies in the language people write to him (the examples below are the
Portuguese our first team uses).

Milo is an [OpenClaw 2.0](https://openclaw.ai) agent built on
[Plow's OpenClaw base](https://github.com/plow-pbc/plow-openclaw-agent) for the
AI Worth Using × OpenClaw 2.0 hackathon. MIT licensed.

## The job, end to end

1. **Learn the playbook.** The owner sends whatever exists: website, deck,
   PDF, a paragraph. Milo drafts a playbook with the offer, sale types, fit
   criteria, tone and a "never contact" list. Every line is tagged as
   *from your material*, *my inference* or *confirmed by you*. Nothing counts
   until the owner confirms it.
2. **Research an account, or a whole list.** "Olha a Acme pra gente." Milo
   returns a verdict (good fit, unsure or no fit), the reasons, each with a
   source, who decides at that company, and whether a contact was found or
   not. When there is a fit, a draft comes with it. For a pasted list,
   spreadsheet or screenshot, he triages every row and brings back the best
   ten. He says "I couldn't find it" instead of guessing.
3. **Turn a correction into a rule.** One teammate edits a draft: "don't cite
   the law in a first email". Milo asks whether that is a rule for every
   account of that type. Someone allowed to change the playbook confirms. On
   the *next, different* account, Milo applies the rule and says which rule
   he used and who confirmed it.
4. **Approve, then send.** An approver says "pode mandar". The first email a
   company ever sends through Milo goes to that approver as a test. After
   they confirm it arrived well, Milo sends from his own mailbox with the
   owner in copy, and reports what went out.
5. **Follow through.** A weekday morning summary lists what is waiting and on
   whom. Milo reminds the team when a follow-up is due, drafts replies when a
   lead answers, and keeps a status, an owner and a next step on every
   account.

## Multiplayer: roles that change what Milo does

The same "ok" means different things depending on who sent it.

| Role | Who | Can |
|---|---|---|
| Owner | installed Milo | confirm the playbook, add or remove approvers, turn sending on |
| Approver | added by the owner in the team group | approve a specific email version to a specific person, confirm rules |
| Teammate | anyone in the group | ask for research, correct drafts, propose rules |
| Lead | outside person | reply or ask to stop, never instruct Milo |

People are identified by the channel's sender id, never by a display name or
by what a message claims. When someone who is not an approver says "manda",
Milo thanks them, names who approves, and does not send.

## Why you can let it send

Sending is enforced by code, not only by the prompt. Every approval and every
send goes through `milo-envio`, a SQLite ledger (Python standard library only)
that the model calls as a single command:

- An approval is bound to the account, the version, the exact recipient and a
  hash of the subject and body. Change any of them and it is a new version
  that needs a new approval.
- At send time the ledger re-checks the approver, the text hash, the "never
  contact" list, the daily limit and whether that address already got a
  first contact. It reserves the send before calling the email API and
  records the provider's message id after.
- An ambiguous result (timeout, 5xx, "acceptance unknown") is marked
  *uncertain* and is never retried automatically.
- Sending is off until the owner turns it on, and the first send of each
  company is a test to the approver.
- Anyone who asks to stop goes on the "never contact" list for good.

The ledger has 87 unit tests, including a fake Plow email API for sent,
refused, uncertain and dropped-connection cases. `registro.md` is a readable
log generated from the database.

## What Milo will not do

- invent a fact, a contact or a decision-maker: facts need a source link, and
  guesses are labeled as hypotheses;
- send anything without a recorded approval, or retry an uncertain send;
- negotiate, promise delivery or close deals;
- pretend to be human: every first email says it comes from the company's AI
  assistant and how to opt out;
- treat a website, a file or a lead's email as instructions.

## How it is built

```text
owner DM ─┐
team group ├─► OpenClaw 2.0 on Plow (one container per company)
          │     prompt/MILO.md       role, rules, how to talk
          │     skills/              aprender-playbook · qualificar-conta
          │                          redigir-abordagem · executar-envio
          │                          acompanhar · pendencias
          │     cron                 morning summary, follow-up reminders
          ▼
/var/lib/plow/workspace/mesa/  (persistent volume)
  playbook.md   fontes/   contas/<account>.md   rascunhos/<account>-v<n>.txt
  envios.sqlite  ◄── milo-envio: approvals, sends, never-contact, config
```

- **State lives in files, not in the chat.** Conversations do not share
  memory; the playbook, account notes and immutable draft versions do. What
  the owner teaches in their DM holds in the group and after a restart.
- **Email** goes out through Plow's email line API from the agent's own
  address, with the owner in copy.
- **Web research** uses `skills/qualificar-conta/scripts/buscar.py` (search
  results are leads; Milo opens the page before stating anything).
- **Model and limits** are set in `boot/milo-config.js`: Claude Sonnet 5 with
  GLM 5.2 as fallback, a smaller declared context window so pruning starts
  early, and the `cron` tool enabled.

## Install

Install Milo from its [Agent Index page](https://aiworthusing.com/agent-index/milo).
Each company gets its own installation on its own Plow account. Then:

1. Text Milo and send your site or deck; confirm the playbook he proposes.
2. Ask him to create the team group with your teammates' numbers.
3. To let Milo send email, connect a Gmail account to your Plow account (it
   is placed in copy on every email), then tell Milo he can send.

## Develop and test

Docker with `linux/amd64` support is required.

```sh
docker build --platform linux/amd64 -t milo:dev .
python3 -m unittest discover -s tests/envio -p 'test_*.py'      # ledger and email sending
python3 -m unittest discover -s tests/rascunhos -p 'test_*.py'  # draft versioning
python3 -m unittest discover -s tests/busca -p 'test_*.py'      # web search parsing
```

`tests/cenarios/` runs Milo against scripted conversations and fictional desk
states without a phone line. It uses real model credits; see its README.

To run against a real line, install [plow-agents](https://github.com/plow-pbc/plow-agents),
sign in, mint a credential for a line, and run the image with a persistent
volume:

```sh
docker run -d --name milo --platform linux/amd64 \
  --env-file ./plow-credentials -v milo-state:/var/lib/plow milo:dev
```

Credentials and the volume hold private state; keep them out of Git.

## Known limits

- Replies from leads land in the owner's inbox (they are in copy), not in
  Milo's conversation. A teammate tells Milo "ele respondeu" and he takes it
  from there.
- Research uses public web pages only. When free search engines rate-limit,
  Milo tries likely official domains or asks for the site.
- People outside the owner join through the group Milo creates; they cannot
  start a direct thread with his line.
- One installation per company: roles organize a trusted team, they do not
  isolate hostile users from each other.

## License

MIT. See [LICENSE](LICENSE).
