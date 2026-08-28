# syntax=docker/dockerfile:1

FROM node:24-trixie-slim

LABEL org.opencontainers.image.source="https://github.com/Lukk17/agent-standards" \
      org.opencontainers.image.title="agent-standards-sandbox" \
      org.opencontainers.image.description="Throwaway sandbox that installs every supported agent CLI and asserts what each one discovers."

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        git \
        jq \
        python3 \
        shellcheck \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash sandbox \
    && mkdir -p /work \
    && chown sandbox:sandbox /work

USER sandbox

ENV HOME=/home/sandbox \
    NPM_CONFIG_PREFIX=/home/sandbox/.npm-global \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false \
    PATH=/home/sandbox/.npm-global/bin:/usr/local/bin:/usr/bin:/bin \
    AGENT_STANDARDS_REPO=/repo \
    SANDBOX_PROJECT=/work/project \
    SANDBOX_BARE=/work/bare

RUN npm install --global --loglevel=error \
        @anthropic-ai/claude-code@2.1.250 \
        @openai/codex@0.150.1 \
        opencode-ai@1.18.25 \
        @kilocode/cli@7.5.5 \
        @github/copilot@1.0.81

COPY --chown=sandbox:sandbox entrypoint.sh setup-project.sh setup-global.sh verify-project.sh verify-global.sh /sandbox/

RUN chmod +x /sandbox/*.sh

WORKDIR /work

ENTRYPOINT ["/sandbox/entrypoint.sh"]
CMD ["/sandbox/verify-project.sh"]
