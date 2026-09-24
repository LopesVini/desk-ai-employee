# Plow source: plow-pbc/plow-openclaw-agent at 7ce757a1745de286dd180c5c5182aca31eba8a75.
# Keep both the commit tag and the registry digest when updating this base.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-7ce757a1745de286dd180c5c5182aca31eba8a75@sha256:6e5e1a11a8c6e2ef6ecaa5e7b429e778a9a3befaf416a09922aaaa4a5b21d647

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
USER node
