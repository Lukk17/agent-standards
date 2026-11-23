# The Evidence Table

Companion reference for the [automation-inventory](../SKILL.md) skill. Load it when writing the audit report, for the columns of the table, a filled example and the one-word calls.

---

### Report as one evidence table, then one recommendation per item

The table is the deliverable. Each row carries the automation, where it is defined, its live state, its problem
type, and the proof. Recommendations come after the table and each one is a single word, so the user can act on the
list without interpreting a paragraph.

A filled example:

| Automation | Source | Live state | Problem type | Proof | Call |
|---|---|---|---|---|---|
| Nightly backup timer | `/etc/systemd/system/backup.timer` | verified | none | `systemctl list-timers backup` shows next run in 6h, last run OK | keep |
| CI test workflow | `.github/workflows/ci.yml` | verified | none | `gh run list --workflow ci.yml` shows 5 of 5 success | keep |
| Pre-commit lint hook | `.git/hooks/pre-commit` | stale | active breakage | Calls `npx eslint`, `npx eslint --version` exits 127, package removed | fix next |
| Legacy deploy script | `scripts/deploy.sh` | stale | overlap | No run in git log since the CI deploy job landed, same steps as `deploy.yml` | cut |
| Atlassian MCP server | `.mcp.json` | configured | authentication outage | Process starts, `atlassianUserInfo` returns 401, no token in environment | fix next |
| Secret scanning | none found | missing | missing capability | No `gitleaks` config, no scanning workflow, no pre-push hook | fix next |

Every row ends in keep, merge, cut or fix next. No row ends in "investigate further" without a named next command.
