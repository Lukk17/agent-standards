# syntax=docker/dockerfile:1

FROM node:24-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ca-certificates \
        git \
        jq \
        python3 \
        shellcheck \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash harness \
    && mkdir -p /work \
    && chown harness:harness /work

USER harness

ENV HOME=/home/harness \
    NPM_CONFIG_PREFIX=/home/harness/.npm-global \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false \
    PATH=/home/harness/.npm-global/bin:/usr/local/bin:/usr/bin:/bin \
    AGENT_STANDARDS_REPO=/repo \
    HARNESS_PROJECT=/work/project

RUN npm install --global --loglevel=error \
        @anthropic-ai/claude-code \
        @openai/codex \
        opencode-ai \
        @kilocode/cli \
        @github/copilot

COPY --chown=harness:harness entrypoint.sh setup-project.sh verify.sh /harness/

RUN chmod +x /harness/*.sh

WORKDIR /work

ENTRYPOINT ["/harness/entrypoint.sh"]
CMD ["/harness/verify.sh"]
