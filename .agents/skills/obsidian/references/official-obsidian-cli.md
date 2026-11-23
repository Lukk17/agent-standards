# The Official obsidian Command

The CLI Obsidian ships itself, a different tool from `notesmd-cli`. Open this when the user wants the official command, or when a move or a delete has to follow the app's own settings. The `notesmd-cli` commands are in [commands.md](commands.md).

Sources:

- `https://help.obsidian.md/cli`, for the official `obsidian` command

---

### The official obsidian command

Obsidian 1.12 added its own CLI, named `obsidian`. It is turned on in Settings, General, Command line interface, which registers it on the `PATH`: a user `PATH` entry on Windows, a symlink at `/usr/local/bin/obsidian` on macOS, and a copy at `~/.local/bin/obsidian` on Linux. It needs the Obsidian app running, and starts it if it is not.

Its equivalents use `name=value` parameters:

```bash
obsidian search query="<term>" format=json
```

```bash
obsidian move path="<current-note-path>" to="<new-note-path>"
```

Its `move` updates links only when the vault setting Automatically update internal links is on. Its `delete` sends the file to the trash unless `permanent` is passed, and the confirm-before-delete rule applies to it the same way. Prefer `notesmd-cli` when the app may not be running, such as on a server or in a scheduled job.
