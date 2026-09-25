# Commands

Every `notesmd-cli` command below runs unchanged in PowerShell, bash and zsh. Commands take `--vault "<vault-name>"`
to pick a vault, and fall back to the default vault when it is omitted. Note paths are relative to the vault root,
and the `.md` suffix is optional.

Sources, fetched 2026-09-25:

- `https://github.com/Yakitrak/notesmd-cli`, README section Usage, and `notesmd-cli --help` from v0.3.7
- `https://help.obsidian.md/cli`, for the official `obsidian` command

---

### Pick a default vault

Once per machine, so later commands can drop `--vault`:

```bash
notesmd-cli set-default-vault "<vault-name>"
```

---

### Search

Search note content and print matches to standard output, the form an agent should use:

```bash
notesmd-cli search-content "<term>" --no-interactive
```

The same search as JSON, for a script to parse:

```bash
notesmd-cli search-content "<term>" --format json
```

List the files and folders under a vault folder:

```bash
notesmd-cli list "<folder>"
```

Print one note's content:

```bash
notesmd-cli print "<note-path>"
```

`notesmd-cli search`, with no term, is an interactive fuzzy picker over note names. Use it only in a terminal a person
is typing in.

---

### Create

Writes the file directly, without Obsidian running, and creates missing folders. An existing note is left unchanged
unless `--overwrite` or `--append` is given:

```bash
notesmd-cli create "<folder>/<note-name>" --content "<text>"
```

Add to the end of an existing note:

```bash
notesmd-cli create "<note-path>" --content "<text>" --append
```

When the name has no folder, the note goes to the folder set as the vault's default location for new notes, or to
the vault root.

---

### Move and rename

Moves the note and rewrites every link to it across the vault. Giving the same folder with a new name is a rename:

```bash
notesmd-cli move "<current-note-path>" "<new-note-path>"
```

Never move a note with `mv`, `Move-Item` or a file manager, because none of them update links.

---

### Delete

Confirm with the user first, naming the exact note path and vault. The command removes the file permanently, with no
trash, because it calls `os.Remove` on the path (`pkg/obsidian/note.go` in the notesmd-cli source):

```bash
notesmd-cli delete "<note-path>"
```

---

### The official obsidian command

Obsidian 1.12 added its own CLI, named `obsidian`. It is turned on in Settings, General, Command line interface,
which registers it on the `PATH`: a user `PATH` entry on Windows, a symlink at `/usr/local/bin/obsidian` on macOS,
and a copy at `~/.local/bin/obsidian` on Linux. It needs the Obsidian app running, and starts it if it is not.

Its equivalents use `name=value` parameters:

```bash
obsidian search query="<term>" format=json
```

```bash
obsidian move path="<current-note-path>" to="<new-note-path>"
```

Its `move` updates links only when the vault setting Automatically update internal links is on. Its `delete` sends
the file to the trash unless `permanent` is passed, and the confirm-before-delete rule applies to it the same way.
Prefer `notesmd-cli` when the app may not be running, such as on a server or in a scheduled job.
