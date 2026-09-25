# Desk · Milo

Desk is a future product interface for AI employees. Milo is its first AI
employee. For the current pilot, he is a supervised B2B research SDR. This
repository remains a thin variant of [Plow's OpenClaw agent](https://github.com/plow-pbc/plow-openclaw-agent).
See [architecture](docs/architecture.md).

The Dockerfile pins Plow source commit
`7ce757a1745de286dd180c5c5182aca31eba8a75` to published image digest
`sha256:6e5e1a11a8c6e2ef6ecaa5e7b429e778a9a3befaf416a09922aaaa4a5b21d647`.
That base runs OpenClaw `2026.9.4`. The [upstream variant guidance](https://github.com/plow-pbc/plow-openclaw-agent#building-a-variant-image)
defines the inherited boot, skills path, Plow integration, and Agent Index
reporting. Milo adds a prompt, five task skills, three file templates and a
local SQLite approval ledger. The Dockerfile leaves `AGENT_ID` unset: setting it registers an Agent
Index listing and starts periodic usage reports, so choose an ID only when
ready to claim that identity. No credential belongs in the image or Git.

## Current pilot boundary

Milo can learn a playbook from provided material, research one account using
sources he can read, create a versioned outreach draft, track corrections and
confirmed rules, and summarize pending work. These are development capabilities
until they pass a full conversation test on the intended line. The `milo-envio`
ledger has local unit coverage; its identity and channel behavior still need
live validation. Automatic external email is disabled in the current skill.
An authorized person receives the exact approved body and sends it from their
own mailbox, then confirms the action for the ledger. Neither an email address
found online nor a Plow `messageId` proves delivery.

The persistent desk is `/var/lib/plow/workspace/mesa/`. It contains the
company's playbook, source notes, account files, versioned draft bodies, and
`envios.sqlite`. Keep it on the installation's private volume and out of Git.
Skill instructions live in `skills/`, templates in `templates/`, and the
ledger contract in [milo-envio](docs/milo-envio.md).

## Build and check locally

Docker with `linux/amd64` support is required. These checks need no Plow
credentials and do not contact a live line:

```sh
docker build --platform linux/amd64 -t desk-milo:local .
docker run --rm --platform linux/amd64 --network none desk-milo:local /opt/plow/probe
docker run --rm --platform linux/amd64 --network none desk-milo:local \
  sh -c 'grep -q "You are Milo" /opt/plow/prompt/AGENTS.md && test -f /opt/plow/boot/main.js && test -f /opt/plow/skills/redigir-abordagem/SKILL.md && test -f /opt/plow/templates/playbook.md'
python3 -m unittest discover -s tests/envio -p 'test_*.py' -q
```

To test an actual conversation later, install [plow-agents](https://github.com/plow-pbc/plow-agents),
sign in, select a line, and mint local credentials as documented by Plow.
The commands below require an authorized line and are intentionally not part
of the credential-free checks:

```sh
plow-agents login
plow-agents lines
plow-agents mint LINE_UID
docker volume create desk-milo-state
docker run --rm --name desk-milo --platform linux/amd64 \
  --env-file ./plow-credentials \
  -v desk-milo-state:/var/lib/plow desk-milo:local
```

`plow-credentials` and the persistent volume contain sensitive state. The
generated file is ignored by Git and Docker build. On first contact, text the
selected line as its owner and verify Milo replies. Keep the same volume on
later runs; deleting it loses sessions, checkpoints, and any Agent Index key.
The Plow line's agent name must also be configured as Milo if you want the
runtime identity and first-contact name to match this prompt.

## Future release through Plow

Once local conversation testing and an Agent Index ID decision are complete,
build and push to a registry you control, then deploy the immutable digest to
the chosen line. These are future steps, not performed by this repository:

```sh
plow-agents image build REGISTRY/REPOSITORY:TAG
plow-agents image push REGISTRY/REPOSITORY:TAG
plow-agents deploy REGISTRY/REPOSITORY@sha256:DIGEST --line LINE_UID
```

Plow must be able to pull the published image. Use the digest printed by the
push command. Review the current [Plow instructions](https://github.com/plow-pbc/plow-openclaw-agent#run-it)
before release, particularly Agent Index reporting requirements for hosting.

MIT licensed; see [LICENSE](LICENSE).
