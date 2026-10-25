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
    OPENCODE2_PREFIX=/home/sandbox/.opencode-v2 \
    SANDBOX_MCP_GUARD_LOG=/tmp/sandbox-mcp-guard.log \
    PATH=/home/sandbox/.mcp-guard:/home/sandbox/.local/bin:/home/sandbox/.npm-global/bin:/usr/local/bin:/usr/bin:/bin \
    AGENT_STANDARDS_REPO=/repo \
    SANDBOX_PROJECT=/work/project \
    SANDBOX_BARE=/work/bare

RUN npm install --global --loglevel=error \
        @anthropic-ai/claude-code@2.1.250 \
        @openai/codex@0.150.1 \
        opencode-ai@1.18.25 \
        @kilocode/cli@7.5.5 \
        @github/copilot@1.0.103

# OpenCode 2.x is a separate package that also owns the opencode binary name,
# so it gets its own prefix and reaches PATH only as the opencode2 wrapper.
# Its postinstall script picks the native binary, so scripts stay enabled.
RUN npm install --global --prefix /home/sandbox/.opencode-v2 --loglevel=error \
        @opencode/cli@2.0.28

COPY --chown=sandbox:sandbox entrypoint.sh setup-project.sh setup-global.sh verify-project.sh verify-global.sh \
     lib-opencode2.sh opencode2.sh mcp-guard.sh mock-model.mjs /sandbox/

# docker, npx and uvx are the only launchers the shipped MCP blocks use. The
# guard stands first on PATH under all three names, so no agent CLI can start
# a real MCP server, pull an image or download a package during a run.
RUN chmod +x /sandbox/*.sh \
    && mkdir -p /home/sandbox/.local/bin /home/sandbox/.mcp-guard \
    && ln -s /sandbox/opencode2.sh /home/sandbox/.local/bin/opencode2 \
    && for launcher in docker npx uvx; do ln -s /sandbox/mcp-guard.sh "/home/sandbox/.mcp-guard/${launcher}"; done

WORKDIR /work

ENTRYPOINT ["/sandbox/entrypoint.sh"]
CMD ["/sandbox/verify-project.sh"]
