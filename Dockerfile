# Plow source: plow-pbc/plow-openclaw-agent at 7ce757a1745de286dd180c5c5182aca31eba8a75.
# Keep both the commit tag and the registry digest when updating this base.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-7ce757a1745de286dd180c5c5182aca31eba8a75@sha256:6e5e1a11a8c6e2ef6ecaa5e7b429e778a9a3befaf416a09922aaaa4a5b21d647

ENV AGENT_ID=milo \
    AGENT_NAME=Milo \
    AGENT_BLURB="A supervised B2B research SDR that learns your playbook, researches accounts, and drafts outreach for approval."

# Boot reads this file and renders it into the persistent workspace. Append to
# Plow's maintained instructions instead of replacing its chat and Latch rules.
USER root
COPY prompt/MILO.md /tmp/desk-milo.md
RUN printf '\n' >> /opt/plow/prompt/AGENTS.md \
    && cat /tmp/desk-milo.md >> /opt/plow/prompt/AGENTS.md \
    && rm /tmp/desk-milo.md

# OpenClaw loads skill directories from this inherited location. The initial
# directory contains documentation only; future skills need no boot changes.
COPY skills/ /opt/plow/skills/
COPY templates/ /opt/plow/templates/

# Boot regenerates openclaw.json on every start. Wrap the base's renderConfig
# with Milo's overrides (model, context window, pruning, heartbeat); see
# boot/milo-config.js. Fail the build if the base renames the function, so an
# update cannot silently drop the overrides.
COPY boot/milo-config.js /tmp/milo-config.js
RUN grep -q '^export function renderConfig(' /opt/plow/boot/config.js \
    && sed -i 's/^export function renderConfig(/function renderConfigBase(/' /opt/plow/boot/config.js \
    && cat /tmp/milo-config.js >> /opt/plow/boot/config.js \
    && rm /tmp/milo-config.js
USER node
