---
name: obsidian
description: 'Working with Obsidian vaults from a terminal on Windows, Linux and macOS: finding which vaults exist and which one is open from the obsidian.json vault list, installing notesmd-cli (the project formerly named obsidian-cli), and searching, creating, moving with link updates, and deleting notes. Use when you say "find my Obsidian vault", "search my notes", "create a note in Obsidian", "rename this note and fix the links", "move this note to another folder", "delete that note", or "install obsidian-cli". Not for writing the prose inside a note that a person will publish, use `markdown-writer`, and not for researching a tool behaviour the vault does not answer, use `research`.'
---

# Obsidian

An Obsidian vault is an ordinary folder of Markdown files. Obsidian keeps one list of every vault it has opened in a
file called `obsidian.json`, and `notesmd-cli` reads that list to find a vault by name. Everything below works on
Windows, Linux and macOS, and the only thing that changes per platform is where that file lives and how the CLI is
installed.

Baseline: notesmd-cli v0.3.7, verified on Windows 11 against a real vault list. The Linux and macOS paths are read
from Obsidian's own help and from the notesmd-cli source, not measured on those systems.

| Task | Open |
|---|---|
| Finding the vault list, the open vault, and a vault's path on each platform | [vault-discovery.md](references/vault-discovery.md) |
| Installing notesmd-cli on Windows, Linux or macOS, or migrating from `obsidian-cli` | [install.md](references/install.md) |
| Search, create, move and rename with link updates, delete, and the official `obsidian` CLI | [commands.md](references/commands.md) |

---

### When to activate

- Locating an Obsidian vault on disk, or working out which vault is currently open
- Searching note names or note content in a vault
- Creating a note, or appending to one, from a script or an agent
- Moving or renaming a note so every link pointing at it follows
- Deleting a note
- Installing `notesmd-cli`, or replacing an old `obsidian-cli` install

---

### When not to activate

- Writing or polishing the prose inside a note meant for publishing, use `markdown-writer`
- Looking up how Obsidian or a plugin behaves when the vault itself cannot answer it, use `research`
- Scripting unrelated shell work that happens to live in a vault folder, use `bash` or `powershell`

---

### Read the vault list, never guess a path

A machine often has several vaults, and a guessed path writes a note into the wrong one. Read `obsidian.json`, or ask
`notesmd-cli list-vaults`, and use the entry the user named. `list-vaults` marks only the default vault, so finding
the vault open in the app needs a direct read of the `open` flag in `obsidian.json`. Do not write a vault path into a
script: resolve it at run time. The per-platform locations and the exact commands are in
[vault-discovery.md](references/vault-discovery.md).

Pass:

```text
Read obsidian.json, two vaults registered, one marked open. Asked which one before creating the note.
```

Fail:

```text
Created the note under Documents because vaults usually live there.
```

---

### Use the CLI the project now ships

The tool formerly called `obsidian-cli` was renamed to `notesmd-cli` in v0.3.0, because Obsidian released an
official CLI of its own. Old install commands for `obsidian-cli` point at a retired name. `notesmd-cli` writes to
disk directly and does not need Obsidian running. The official `obsidian` command does need the app running, and is
covered in [commands.md](references/commands.md).

---

### Prefer non-interactive commands from an agent

`notesmd-cli search` is a fuzzy picker that waits for a keypress, and `search-content` opens a picker by default. An
agent has no terminal to press keys in, so it uses `search-content` with `--no-interactive` or `--format json`, and
`list` to walk folders.

---

### Move with the CLI, not with the file manager

`notesmd-cli move` rewrites every link in the vault that pointed at the old path. A plain `mv` or `Move-Item`
leaves those links broken. Use the CLI for any move or rename.

---

### Confirm with the user before any delete

`notesmd-cli delete` removes the file with no trash and no undo. Before running it, name the exact note path and the
vault, and wait for the user to say yes. A delete agreed for one note is not agreement for the next one.

Pass:

```text
About to delete "Inbox/Old draft.md" in vault "<vault-name>". It does not go to the trash. Proceed?
```

Fail:

```text
Cleaned up three notes that looked unused.
```

---

### Edit note content directly when that is simpler

A note is a plain `.md` file, and Obsidian picks up an outside edit on its own. Open the file and change it with the
normal editing tools. Leave the `.obsidian/` folder alone unless the user asks, because it holds the vault's settings
and plugin state.

---

### Related skills

- `markdown-writer` owns the prose and formatting of a note meant for a human audience
- `research` owns checking current tool behaviour against the vendor page
- `bash` and `powershell` own any script that wraps these commands

---

### Checklist

- [ ] The vault came from `obsidian.json` or `list-vaults`, not from a guessed path
- [ ] `notesmd-cli` was used, not the retired `obsidian-cli` name
- [ ] Searches from an agent used `--no-interactive` or `--format json`
- [ ] Every move or rename went through `notesmd-cli move`
- [ ] Every delete was confirmed by the user with the exact path and vault named
- [ ] No vault path was hardcoded into a script or a committed file
