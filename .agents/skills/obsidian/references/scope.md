# Scope

Companion reference for the [obsidian](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Locating an Obsidian vault on disk, or working out which vault is currently open
- Searching note names or note content in a vault
- Creating a note, or appending to one, from a script or an agent
- Moving or renaming a note so every link pointing at it follows
- Deleting a note
- Installing `notesmd-cli`, or replacing an old `obsidian-cli` install
- The user says "find my Obsidian vault", "search my notes", "rename this note and fix the links", "install obsidian-cli", "create a note in Obsidian", "move this note to another folder" or "delete that note"

The skill covers working with Obsidian vaults from a terminal on Windows, Linux and macOS: finding vaults from `obsidian.json`, installing notesmd-cli, and searching, creating, moving with link updates and deleting notes.

---

### When not to activate

- Writing or polishing the prose inside a note meant for publishing, use `markdown-writer`
- Looking up how Obsidian or a plugin behaves when the vault itself cannot answer it, use `research`
- Scripting unrelated shell work that happens to live in a vault folder, use `bash` or `powershell`

---

### Related skills

- `markdown-writer` owns the prose and formatting of a note meant for a human audience
- `research` owns checking current tool behaviour against the vendor page
- `bash` and `powershell` own any script that wraps these commands
