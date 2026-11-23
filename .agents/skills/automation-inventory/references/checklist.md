# Automation Inventory Checklist

Companion reference for the [automation-inventory](../SKILL.md) skill. Run it before calling an audit done.

- [ ] The audit started read-only and changed nothing without a request
- [ ] Every automation surface was enumerated, not just the obvious one
- [ ] Each item carries exactly one live state and one problem type
- [ ] Each important claim cites a command and its output
- [ ] Presence in configuration was never reported as working
- [ ] The evidence table exists before any merge or delete recommendation
- [ ] Every row ends in keep, merge, cut or fix next
- [ ] Anything undetermined is named, with the command that would settle it
