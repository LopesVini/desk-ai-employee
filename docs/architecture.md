# Architecture

Desk is the product and future web interface. Milo is its main AI employee;
his current pilot role is a supervised B2B research SDR. The upstream runtime
stays independent of this sales workflow. OpenClaw is the runtime for the
hackathon's 2.x stack; the selected upstream image pins release `2026.9.4`.
Plow supplies the
hosted phone line, identity, chat transport, owner trust context, and Latch
connection. The existing Plow channel handles multiple people and separate
conversation sessions. This is the project's initial multiplayer foundation,
not a Desk account or tenant model.

This repository owns the image pin, Milo's pilot prompt, skills, templates and
approval ledger. The official base owns boot, OpenClaw configuration, Plow/Latch
integration, chat and email routing, state in `/var/lib/plow`, and Agent Index
registration and usage reporting when `AGENT_ID` is configured. Boot renders
`AGENTS.md` into the state workspace and recreates runtime config; do not edit
those generated files for durable behavior. Desk appends to the inherited
prompt so upstream operational instructions remain intact.

The company-specific desk lives under `/var/lib/plow/workspace/mesa/` on the
persistent volume. Skills in `/opt/plow/skills/` read and write that desk;
templates in `/opt/plow/templates/` define its human-readable files. The
SQLite ledger in `skills/executar-envio/` records approvals and reservations,
but the model still has direct tools. The current skill therefore uses human
sending until channel identity, delivery and bypass risks are resolved.

The future Desk web UI may use a different interface from OpenClaw Control UI.
Voice and retro/pixel art presentation are possible later additions. Nothing
in this variant implements them or depends on them.

Jev may later provide optional evaluation of small, typed, frequent decisions.
It is never Milo's main reasoning system: the main LLM interprets, plans, and
generates; Jev judges; code enforces rules and permissions; OpenClaw executes;
humans participate when needed. No Jev integration is included here.

A future Desk interface may show `idle`, `working`, `waiting_external`,
`needs_approval`, `completed`, and `failed`. These are product states to design
later, not states exposed by this image. Adding them should preserve the
upstream conversation and persistence contracts.

## Base update

Review [Plow's variant instructions](https://github.com/plow-pbc/plow-openclaw-agent#building-a-variant-image),
its boot and release notes, then choose a published `base-<full source commit>`
tag and verify its digest and `linux/amd64` support. Update the `FROM` line
with both values. Build and run the credential-free probe before testing a
real Plow line. A newer GitHub commit does not imply its image is published.
