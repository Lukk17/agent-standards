# Scope

Companion reference for the [powershell](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing a `.ps1`, `.psm1`, or `.psd1` file.
- Turning a loose script into an advanced function or a module.
- Fixing a script that keeps running after a cmdlet or a native command failed.
- Adding parameter validation, `-WhatIf` support, or comment-based help.
- Writing Pester tests or clearing PSScriptAnalyzer findings.
- Making a Windows-only script run on Linux or macOS.
- The user says "write a PowerShell script for this", "my script ignores when git fails", "turn this into a proper cmdlet" or "add Pester tests for this module".

---

### When not to activate

- Writing POSIX shell scripts, use `bash`.
- Writing the CI workflow YAML that invokes the script, use `deployment-patterns`.
- Writing the container image the script runs in, use `docker-patterns`.
- Configuring Windows hosts at fleet scale, use `ansible`.
- Choosing exception types and error-handling architecture, use `coding-standards`.

---

### Related skills

- `bash` for the same standards on POSIX shells.
- `observability-and-logging` for the readiness banner and the logging conventions it follows.
- `deployment-patterns` for the CI workflow that runs PSScriptAnalyzer and Pester.
- `docker-patterns` when the script runs inside a container.
- `ansible` when the work is fleet configuration rather than a one-host script.
