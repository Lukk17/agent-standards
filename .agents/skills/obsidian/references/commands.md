# Commands

Contents:

- [Pick a default vault](#pick-a-default-vault)
- [Search](#search)
- [Create](#create)
- [Move and rename](#move-and-rename)
- [Delete](#delete)
- [Edit note content directly](#edit-note-content-directly)

Every `notesmd-cli` command below runs unchanged in PowerShell, bash and zsh. Commands take `--vault "<vault-name>"`
to pick a vault, and fall back to the default vault when it is omitted. Note paths are relative to the vault root,
and the `.md` suffix is optional.

The official `obsidian` command, a different tool, is in [official-obsidian-cli.md](official-obsidian-cli.md).

Sources:

- `https://github.com/Yakitrak/notesmd-cli`, README section Usage, and `notesmd-cli --help` from a 0.3 release

---

### Pick a default vault

Once per machine, so later commands can drop `--vault`:

```bash
notesmd-cli set-default-vault "<vault-name>"
```

---

### Search

`notesmd-cli search` is a fuzzy picker that waits for a keypress, and `search-content` opens a picker by default. An agent has no terminal to press keys in, so it uses `search-content` with `--no-interactive` or `--format json`, and `list` to walk folders.

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

`notesmd-cli move` rewrites every link in the vault that pointed at the old path. A plain `mv` or `Move-Item` leaves those links broken. Use the CLI for any move or rename.

Moves the note and rewrites every link to it across the vault. Giving the same folder with a new name is a rename:

```bash
notesmd-cli move "<current-note-path>" "<new-note-path>"
```

Never move a note with `mv`, `Move-Item` or a file manager, because none of them update links.

---

### Delete

`notesmd-cli delete` removes the file with no trash and no undo. Before running it, name the exact note path and the vault, and wait for the user to say yes. A delete agreed for one note is not agreement for the next one.

Pass:

```text
About to delete "Inbox/Old draft.md" in vault "<vault-name>". It does not go to the trash. Proceed?
```

Fail:

```text
Cleaned up three notes that looked unused.
```

Confirm with the user first, naming the exact note path and vault. The command removes the file permanently, with no
trash, because it calls `os.Remove` on the path (`pkg/obsidian/note.go` in the notesmd-cli source):

```bash
notesmd-cli delete "<note-path>"
```

---

### Edit note content directly

A note is a plain `.md` file, and Obsidian picks up an outside edit on its own. Open the file and change it with the normal editing tools. Leave the `.obsidian/` folder alone unless the user asks, because it holds the vault's settings and plugin state.
