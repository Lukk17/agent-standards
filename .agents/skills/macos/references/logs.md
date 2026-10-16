# The Unified Log

Read this when you need evidence for a failure on a Mac: a crash, a job that would not start, a permission denial, a slow login. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Source: the `log(1)` man page as shipped with Xcode 27.2 beta 2, read through `https://keith.github.io/xcode-man-pages/log.1.html` on 2026-10-13. Options move between releases, so confirm with `man log` on the machine.

---

### Bounded queries

Always bound a query by time and by a predicate. The unified log holds a very large volume of messages.

The last hour for one process:

```bash
log show --last 1h --predicate 'process == "<ProcessName>"' --style compact
```

One subsystem, errors and faults only:

```bash
log show --last 30m --predicate 'subsystem == "<com.example.subsystem>" and (messageType == error or messageType == fault)' --style compact
```

A fixed window:

```bash
log show --start '<YYYY-MM-DD HH:MM:SS>' --end '<YYYY-MM-DD HH:MM:SS>' --predicate 'process == "<ProcessName>"'
```

Follow live while reproducing a problem, stopped with Ctrl+C:

```bash
log stream --predicate 'process == "<ProcessName>"' --style compact
```

1. `--last` takes `num[s|m|h|d]` or `boot`, and the current page also lists `--last24`, `--today` and `--yesterday`.
2. Info and debug messages are hidden unless asked for with `--info` and `--debug`.
3. `--style json` or `ndjson` gives machine readable output.
4. Messages often show `<private>` in place of values, by design. Do not try to disable that redaction, it protects the owner's data.

---

### Other sources

| What | Where |
|---|---|
| Crash and hang reports | `~/Library/Logs/DiagnosticReports` and `/Library/Logs/DiagnosticReports`, also in the Console app |
| An app's own log files | `~/Library/Logs/<App>`, see [paths.md](paths.md) |
| A launchd job's output | wherever its `StandardOutPath` and `StandardErrorPath` point, see [launchd.md](launchd.md) |
| A complete archive for a bug report | `log collect --last <time> --output <file>.logarchive`. The man page says "Some commands require root privileges", and the archive can hold private data, so the owner runs it and decides where it goes |

---

### Reading honestly

The first error around the symptom is usually the cause, and later ones are consequences. Quote the timestamp, process, subsystem and message when reporting, and correlate a message with a symptom or a time before blaming it.
