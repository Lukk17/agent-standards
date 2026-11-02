# Git Configuration

Contents:

- [Essential configuration](#essential-configuration)
- [Useful aliases](#useful-aliases)
- [Ignore patterns](#ignore-patterns)
- [Line endings, symlinks and case](#line-endings-symlinks-and-case)

The configuration a developer sets once per machine or per repository: identity, defaults, aliases, ignore patterns, line endings, symlinks and case. Load this file when setting up a new machine or repository, not during day-to-day work.

---

### Essential configuration

```bash
# User identity
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Default branch name
git config --global init.defaultBranch main

# Pull behavior (rebase instead of merge)
git config --global pull.rebase true

# Push behavior (push current branch only)
git config --global push.default current

# Auto-correct typos
git config --global help.autocorrect 1

# Better diff algorithm
git config --global diff.algorithm histogram

# Color output
git config --global color.ui auto
```

---

### Useful aliases

```bash
# Add to ~/.gitconfig
[alias]
    co = checkout
    br = branch
    ci = commit
    st = status
    unstage = reset HEAD --
    last = log -1 HEAD
    visual = log --oneline --graph --all
    amend = commit --amend --no-edit
    wip = commit -m "WIP"
    undo = reset --soft HEAD~1
    contributors = shortlog -sn
```

---

### Ignore patterns

```gitignore
# Dependencies
node_modules/
vendor/

# Build outputs
dist/
build/
*.o
*.exe

# Environment files
.env
.env.local
.env.*.local

# IDE
.idea/workspace.xml
.idea/shelf/
.idea/modules/
.idea/compiler.xml
.idea/libraries/
.idea/dataSources*
.idea/aws.xml
.idea/sonarlint.xml
.idea/git_toolbox_*.xml
.idea/developer-tools.xml
*.iml
!.idea/<project>.iml
!<python-module>.iml
.vscode/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Test coverage
coverage/

# Cache
.cache/
*.tsbuildinfo
```

The `.idea/` lines ignore only the machine-local and regenerated files. The rest of `.idea/` is committed, and which
file falls on which side is owned by `jetbrains-ide-ops`, so check its version-control reference before changing them.

---

### Line endings, symlinks and case

These three settings decide whether one checkout looks the same on Windows, macOS and Linux. The repository owns the line-ending policy through a committed `.gitattributes`. The other two are probed by Git when the clone is made, so set them at clone time rather than by editing them later. The quotes below are from [git-config](https://git-scm.com/docs/git-config) and [gitattributes](https://git-scm.com/docs/gitattributes).

Line endings. Commit a `.gitattributes` at the root whose first line is `* text=auto eol=lf`, and add one line per exception, such as `*.ps1 text eol=crlf` or `*.bat text eol=crlf` where the project wants Windows endings for those. With `text=auto`, "Git decides by itself whether the file is text or binary". The attribute wins over each developer's `core.autocrlf`, because "If the text attribute is unspecified, Git uses the core.autocrlf configuration variable". Leave `core.autocrlf` unset or `false` on a machine that works in repositories with a `.gitattributes`, and read where a stray value comes from before blaming a file:

```bash
git config --show-origin --get core.autocrlf
```

After adding or changing `.gitattributes`, renormalise the files already in the index and commit the result on its own:

```bash
git add --renormalize .
```

Symlinks. With `core.symlinks` false, "symbolic links are checked out as small plain files that contain the link text". Git probes the filesystem at clone time and may set it false. On Windows a symlink checks out as a plain file unless Developer Mode is on, or Git runs elevated, and the setting is true before the clone. A repository that commits symlinks says so in its contributing guide and is cloned with the setting on:

```bash
git clone -c core.symlinks=true <url>
```

Case. `core.ignoreCase` is set by Git, never by hand: `git clone` and `git init` "will probe and set core.ignoreCase true if appropriate when the repository is created", and "Modifying this value may result in unexpected behavior". Windows and macOS volumes are case insensitive by default, so two paths that differ only in case collide on checkout there, and a rename that only changes case has to go through Git rather than the file manager:

```bash
git mv readme.md README.md
```

Pass:

```text
.gitattributes committed with * text=auto eol=lf, *.ps1 text eol=crlf. core.autocrlf unset. Cloned with core.symlinks=true.
```

Fail:

```text
Told every Windows developer to set core.autocrlf true, and renamed Readme.md to README.md in Explorer.
```
