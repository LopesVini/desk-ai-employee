# Plow source: plow-pbc/plow-openclaw-agent at 771198a9609dcef54d44843e7da5329c17fa51b4.
# Keep both the commit tag and the registry digest when updating this base.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-771198a9609dcef54d44843e7da5329c17fa51b4@sha256:f1e7c421b97a80f1bd17015f96daceb965f350a241f7edc7e4d856a0e3a6f8f5

# The owner maintains the public description on the Agent Index. Omitting
# AGENT_BLURB keeps a fresh install from replacing that description.
ENV AGENT_ID=milo \
    AGENT_NAME=Milo \
    MILO_MESA=/var/lib/plow/workspace/mesa

# Boot reads this file and renders it into the persistent workspace. Append to
# Plow's maintained instructions instead of replacing its chat and Latch rules.
USER root
COPY prompt/MILO.md /tmp/desk-milo.md
# Fail the build if the prompt outgrows bootstrapMaxChars (boot/milo-config.js)
# minus the 8,000 chars the base may add for Latch: past that, OpenClaw cuts it.
RUN printf '\n' >> /opt/plow/prompt/AGENTS.md \
    && cat /tmp/desk-milo.md >> /opt/plow/prompt/AGENTS.md \
    && rm /tmp/desk-milo.md \
    && node -e 'const n=require("fs").readFileSync("/opt/plow/prompt/AGENTS.md","utf8").trimEnd().length; if(n>22000){console.error("AGENTS.md has "+n+" chars; limit 22000");process.exit(1)}'

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
