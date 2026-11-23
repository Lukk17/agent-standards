---
name: obsidian
description: 'Obsidian vaults from a terminal with notesmd-cli: find a vault, search, move and delete notes. Use when the user says "search my notes" or "rename this note and fix the links". Not for note prose, use `markdown-writer`.'
metadata:
  version: "1.1.0"
---

# Obsidian

An Obsidian vault is an ordinary folder of Markdown files. Obsidian keeps one list of every vault it has opened in a file called `obsidian.json`, and `notesmd-cli` reads that list to find a vault by name. Everything below works on Windows, Linux and macOS, and the only thing that changes per platform is where that file lives and how the CLI is installed.

Written for notesmd-cli 0.3, measured on Windows 11 against a real vault list. The Linux and macOS paths are read from Obsidian's own help and from the notesmd-cli source, not measured on those systems.

| Task | Open |
|---|---|
| Finding the vault list, the open vault, and a vault's path on each platform | [vault-discovery.md](references/vault-discovery.md) |
| Installing notesmd-cli on Windows, Linux or macOS, or migrating from `obsidian-cli` | [install.md](references/install.md) |
| Search, create, move and rename with link updates, delete, and editing a note directly | [commands.md](references/commands.md) |
| Using the official `obsidian` command, which needs the app running | [official-obsidian-cli.md](references/official-obsidian-cli.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling work in a vault done | [checklist.md](references/checklist.md) |

---

### When not to activate

- Writing or polishing the prose inside a note meant for publishing, use `markdown-writer`
- Looking up how Obsidian or a plugin behaves when the vault itself cannot answer it, use `research`
- Scripting unrelated shell work that happens to live in a vault folder, use `bash` or `powershell`

---

### Rules

1. Read the vault list, never guess a path. Read `obsidian.json`, or ask `notesmd-cli list-vaults`, and use the entry the user named. `list-vaults` marks only the default vault, so the vault open in the app comes from the `open` flag in `obsidian.json`. Do not write a vault path into a script: resolve it at run time.
2. Use `notesmd-cli`, the tool formerly called `obsidian-cli`. It writes to disk directly and does not need Obsidian running. The official `obsidian` command does need the app running.
3. From an agent, search without a picker: `search-content` with `--no-interactive` or `--format json`, and `list` to walk folders, because an agent has no terminal to press keys in.
4. Move or rename a note with `notesmd-cli move`, which rewrites every link in the vault that pointed at the old path. A plain `mv` or `Move-Item` leaves those links broken.
5. Confirm with the user before any delete. `notesmd-cli delete` removes the file with no trash and no undo, so name the exact note path and the vault, and wait for the user to say yes. A delete agreed for one note is not agreement for the next one.
6. Edit note content directly when that is simpler, because a note is a plain `.md` file. Leave the `.obsidian/` folder alone unless the user asks.
