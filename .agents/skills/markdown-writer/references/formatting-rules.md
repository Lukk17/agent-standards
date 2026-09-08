# Formatting Mechanics

The mechanical formatting rules in full, each with a passing and a failing form: code blocks, links, heading levels
and dividers, counts in badges, list markers, and line wrapping. Load this file when applying one of these rules or
when a draft breaks one and you need the exact repair.

---

### Format code blocks for copying

Put one runnable command in each fenced block, with the matching language tag. Do not put comment lines inside a
block, because the prose around it does the explaining and a pasted comment is noise. Do not chain commands with
`&&` unless the chain genuinely is the one command. Give a shell snippet in both flavours when readers use both, one
fence for bash and one for PowerShell, with the label in the prose above each.

Pass:

```bash
./gradlew bootRun
```

Fail:

```text
cd app && npm install && npm run dev
```

---

### Link every real path, once per mention

Wrap any concrete file or directory path in a link so the reader is one click from inspecting it, on every mention
rather than the first. Use plain link text, not backticked link text, because the double styling reads as noise.
Reserve backticks for a path or identifier that is not also a link. Skip linking for a generic location such as the
project root.

Pass:

```text
Server configuration lives in [config/server.yaml](config/server.yaml).
```

Fail:

```text
Server configuration lives in [`config/server.yaml`](config/server.yaml).
```

---

### Start sections at level 3 and divide them

Reserve level 1 for the document title, one per file, and skip level 2 entirely in human-facing documents. Level 1
and level 2 render heavy enough on most hosts to compete with the title. Sub-sections go to level 4 and deeper. Put a
horizontal rule before every section heading, including the first one after the title block, with one blank line
above and below it. Sub-headings get no rule.

Pass:

```text
---

### Quick start
```

Fail:

```text
## Quick start
```

---

### Keep changing numbers in badges only

A count that moves with project content belongs in a shields.io badge and nowhere else. Every count repeated in prose
or in a directory-tree comment is a future defect the next contributor will not think to update. Gesture at size with
a stable phrase instead.

Pass:

```text
The catalogue covers backend, frontend, infrastructure and tooling.
```

Fail:

```text
All 73 skills cover backend, frontend, infrastructure and tooling.
```

---

### Order lists with digits, never Roman numerals

Use Arabic digits for an ordered list. For sub-steps, use lowercase letters with a closing parenthesis or a nested
digit list. Roman numerals stop being readable past the fourth item, sort wrong in tools that do not know them, and
survive a diff badly.

Pass:

```text
1. Install the CLI
2. Authenticate
   a) Create a token
   b) Export it
```

Fail:

```text
i. Install the CLI
ii. Authenticate
```

---

### Do not hard-wrap, unless the project lints a line cap

Write each paragraph, list item and table row as one physical line and let the viewer soft-wrap it. Never break a
command, path or URL inside a fenced block, because a reader copies it and a break corrupts it. The one exception is
a project whose own lint enforces a maximum line length, such as this repository at 120 characters. Wrap to the cap
there and nowhere else, and never rewrap a file the project does not lint.

Pass:

```text
The worker polls the queue every 200ms and leases a batch of jobs for the duration of its visibility timeout.
```

Fail:

```text
The worker polls the queue every 200ms and leases a
batch of jobs for the duration of its visibility
timeout.
```

---

