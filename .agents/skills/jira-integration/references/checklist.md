# Jira Integration Checklist

Companion reference for the [jira-integration](../SKILL.md) skill. Run it before calling a piece of Jira work done.

- [ ] Credentials come from the process environment, never a literal in a config file
- [ ] The MCP server is declared in the file the running tool actually reads
- [ ] Each MCP tool called is one the connected server actually lists
- [ ] Every transition and comment ran only after the user approved that one action
- [ ] Transitions were read for this issue before one was executed
- [ ] A new issue carries its parent epic and the required labels from the project's list
- [ ] Every other field written was one the user named
- [ ] Comments link outward rather than pasting reports
- [ ] Item content follows `project-tracking`, not conventions invented here
