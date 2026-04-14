### Agent Standards

---

### Overview

This repository serves as a centralized source of truth for AI coding agent instructions, skills, and configuration. By utilizing this repository, you ensure that Claude Code, Kilo Code, and OpenCode all follow the exact same standards and workflows across every project in your organization.

---

### Project Integration via Git Selective Checkout

To import these standards into a new project without overwriting your project's existing files, we use Git Selective Checkout. This approach extracts only the required AI folders and template files directly into your project root.

To protect the central repository, we configure the remote as a read-only source in your local project by setting the push URL to an invalid address. This ensures you can pull updates from the central repository, but Git will block any accidental pushes of your project-specific changes back to the global standards.

#### Step 1: Initial Setup in a New Project

Run these commands in the root of your target project to add the remote, disable pushing, and extract the specific payload files into your workspace:

```bash
git remote add agent-standards https://github.com/Lukk17/agent-standards
git remote set-url --push agent-standards no_push
git fetch agent-standards
git checkout agent-standards/main -- .agents .claude kilo.jsonc.example opencode.json.example AGENTS.md.example
git commit -m "Import central agent-standards (.agents and .claude)"
```

#### Step 2: Pulling Future Updates

When the central standards repository is updated, pull the latest files into your local project by running:

```bash
git fetch agent-standards
git checkout agent-standards/main -- .agents .claude
git commit -m "Update AI standards from central repository"
```

---

### Folder Structure

The repository is organized into specific directories designed to be natively read by your AI agents without requiring complex path configurations.

#### Skills

`.claude/skills/`
The universal skills directory. Place all raw SKILL.md files here. Claude Code, OpenCode, and Kilo Code are all hardcoded to natively scan this specific directory for compatibility. 

#### Implementation Standards and Rules

`.agents/standards/`
Contains markdown files with your organizational implementation rules, architecture guidelines, and coding standards.

#### Claude specific

`.claude/`
Contains basic setup files for Claude Code, such as settings.json and CLAUDE.md.

#### Templates

`kilo.jsonc.example`
Template configuration for Kilo Code workspace rules.


`opencode.json.example`
Template configuration for OpenCode workspace rules.


`AGENTS.md.example`
Template Markdown file for shared memory of repo for various coding agents.

---

### Usage with Claude Code

Claude Code runs natively with the files provided in this repository. 

Skills placed in the .claude/skills/ directory are automatically discovered. No custom mapping is required in your settings.json.

To link your project root AGENTS.md file to Claude Code, ensure your .claude/CLAUDE.md file contains the following relative path directive:

```markdown
@../AGENTS.md
```

---

### Usage with Kilo Code

Kilo Code reads the AGENTS.md file in your project root automatically.

Kilo Code also natively scans the .claude/skills/ directory. You do not need to translate skills or map custom paths for them to work.

To load your implementation standards into Kilo Code, copy the kilo.jsonc.example template to kilo.jsonc. It is pre-configured to point to the standards directory:

```json
{
  "instructions": [
    "./.agents/standards/*.md"
  ]
}
```

---

### Usage with OpenCode

OpenCode relies on its own configuration to discover workspace rules, but it automatically discovers skills placed in the .claude/skills/ directory via its native Claude compatibility scanner.

To link your centralized rules, copy the opencode.json.example template to opencode.json. It is pre-configured to inject the standards into the agent prompts:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": [
    "./.agents/standards/*.md"
  ]
}
```

---

### Managing MCP Servers

The Model Context Protocol allows your AI agents to connect to external tools like databases, GitHub, and local file systems.

The official registry for discovering and managing these servers is located at the Model Context Protocol Registry:  
https://registry.modelcontextprotocol.io/

To use an MCP server from the registry in Claude Code, you run the mcp add command followed by the server package name. For example, to add the official filesystem server:

```bash
claude mcp add @modelcontextprotocol/server-filesystem
```

This will automatically update your .claude/settings.json file with the server configuration.