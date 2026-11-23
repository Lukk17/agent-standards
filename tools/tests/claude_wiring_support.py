"""The Claude Code hook wiring of this repository, as the suites read it.

.claude/settings.json wires no hook itself. It names the repository's own
marketplace and switches on its hook plugins, so the wiring Claude Code runs
here is what those plugins carry in the committed
.claude-plugin/marketplace.json. Claude Code loads a relative-path plugin of a
marketplace added from a local folder in place, so CLAUDE_PLUGIN_ROOT is the
plugin's own folder in the repository.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from tests.conftest import REPO_ROOT

CLAUDE_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
MARKETPLACE_FILE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
HOOK_CATEGORY = "hook"
PLUGIN_ROOT_VARIABLE = "CLAUDE_PLUGIN_ROOT"
PROJECT_DIR_VARIABLE = "CLAUDE_PROJECT_DIR"


@dataclass(frozen=True, slots=True)
class Handler:
    """One command a hook plugin runs: its plugin, its event, its matcher group and the handler itself."""

    plugin: str
    folder: Path
    event: str
    matcher: str | None
    timeout: int | None
    command: str

    @property
    def label(self) -> str:
        return f"{self.plugin}-{self.event}-{self.command.split('/')[-1].split(' ;')[0].replace(' ', '_')}"


def settings() -> dict:
    return json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))


def marketplace() -> dict:
    return json.loads(MARKETPLACE_FILE.read_text(encoding="utf-8"))


def hook_plugins() -> dict[str, dict]:
    """Every hook plugin of the committed marketplace, by the id settings.json enables it under."""
    document = marketplace()

    return {f"{entry['name']}@{document['name']}": entry for entry in document["plugins"] if entry.get("category") == HOOK_CATEGORY}


def enabled_plugins() -> set[str]:
    """Every plugin id .claude/settings.json switches on."""
    return {plugin for plugin, enabled in settings().get("enabledPlugins", {}).items() if enabled is True}


def handlers() -> list[Handler]:
    """Every handler of every hook plugin .claude/settings.json switches on."""
    enabled = enabled_plugins()

    return [
        Handler(entry["name"], REPO_ROOT / entry["source"], event, group.get("matcher"), handler.get("timeout"), handler["command"])
        for plugin, entry in hook_plugins().items()
        if plugin in enabled
        for event, groups in entry["hooks"].items()
        for group in groups
        for handler in group["hooks"]
    ]


def wired(event: str, script: str | None = None) -> list[Handler]:
    """The handlers of one event, or only those that run one script."""
    return [handler for handler in handlers() if handler.event == event and (script is None or f"/{script} " in handler.command)]


def commands(event: str) -> list[str]:
    return [handler.command for handler in wired(event)]


def hook_environment(handler: Handler, project: Path, base: dict[str, str]) -> dict[str, str]:
    """The environment Claude Code gives a handler of a plugin loaded in place, for a session in project."""
    return {**base, PLUGIN_ROOT_VARIABLE: str(handler.folder), PROJECT_DIR_VARIABLE: str(project)}
