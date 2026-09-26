---
name: jira-integration
description: 'Jira mechanics from a coding session: fetching an issue and its comments, running JQL, adding progress comments, transitioning status through the project workflow, and linking branches back to the key, through the Atlassian MCP server or the REST v3 API. Use when you say "pull up PROJ-1234", "move this ticket to In Review", "comment the PR link on the ticket", or "find my open issues this sprint". Not for how a work item should be written or closed, use `project-tracking`.'
---

# Jira Integration

How to talk to Jira from a coding session: authenticate, read an issue, act on it, and record progress against it.
The content rules for a work item, what it should say and when it may close, live in `project-tracking`, and this
skill defers to them rather than restating them.

---

### When to activate

- Fetching a Jira issue to understand what is being asked
- Searching for issues with a JQL query
- Adding a progress comment to an issue during or after implementation
- Transitioning an issue through the project workflow
- Linking a branch, pull request or merge request back to an issue key
- Diagnosing a failing Jira call, such as a 401 or a rejected transition

---

### When not to activate

- Deciding what an item should contain, how it is sized, or when it may close, use `project-tracking`
- Operating GitHub issues, pull requests and releases, use `github-ops`
- Naming the branch or writing the commit message that carries the key, use `git-workflow`
- Writing the tests the acceptance criteria imply, use `tdd-workflow` or the language test skill
- Reviewing the code the ticket produced, use `code-reviewer`

---

### Add Atlassian's remote MCP server yourself

No MCP configuration file in this repository declares a Jira server. The MCP tools below come from Atlassian's own
remote MCP server, which each user adds to the MCP file or command their agent tool uses, following
[Getting started with the Atlassian MCP Server](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/).
Atlassian hosts it, so there is no package to install or pin. It signs in through an OAuth 2.1 browser flow, or
through an API token in an `Authorization` header for a headless client.

One rule holds regardless of tool. A token comes from the process environment or a secrets manager, never as a
literal value inside a configuration file that can be committed.

Pass:

```text
Server added with the OAuth sign-in. No token in any committed file.
```

Fail:

```json
{"headers": {"Authorization": "Basic the-real-token-pasted-into-a-committed-file"}}
```

Create the token at the Atlassian account security page, store it in the environment or a secrets manager, and scope
it to the projects you actually need. Rotate it immediately if it ever reaches git history.

---

### Fall back to REST v3 when no MCP server is available

The REST API answers the same questions over `curl`. It needs the same three environment variables.

| Variable | What it holds |
|---|---|
| `JIRA_URL` | The instance base URL |
| `JIRA_EMAIL` | The Atlassian account email |
| `JIRA_API_TOKEN` | The API token, from the environment only |

Validate that all three are set before the first call and fail with a clear message if not, because an unset variable
produces a 401 that reads like a permissions problem.

---

### Know which MCP tool answers which question

| Tool | Use it for |
|---|---|
| `searchJiraIssuesUsingJql` | JQL queries across a project |
| `getJiraIssue` | Full detail for one key |
| `createJiraIssue` | Creating a Task, Bug, Story or Epic |
| `editJiraIssue` | Changing summary, description or assignee |
| `listJiraIssueTransitions` | The transitions valid for this issue right now |
| `transitionJiraIssue` | Moving status |
| `addOrEditJiraIssueComment` | Progress updates |
| `getJiraBoardSprintData` | Everything in the active sprint of a board |
| `createJiraIssueLink` | Blocks, relates to, duplicates |

These names come from Atlassian's
[supported tools](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/supported-tools/) page. A client
connected before the current server version can still list older names, such as `getTransitionsForJiraIssue` and
`addCommentToJiraIssue`, so call the name the connected server actually lists.

---

### Read a transition ID before transitioning

Transition IDs are per project workflow and change between projects, so an ID that worked on one board fails on the
next. Ask for the available transitions first, match on the name, then execute.

Read the available transitions:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_URL/rest/api/3/issue/PROJ-1234/transitions" | jq '.transitions[] | {id, name}'
```

Then execute the one you matched:

```bash
curl -s -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Content-Type: application/json" -d '{"transition": {"id": "31"}}' "$JIRA_URL/rest/api/3/issue/PROJ-1234/transitions"
```

Pass:

```text
Fetched transitions, "In Review" is id 31 on this board, transitioned with 31.
```

Fail:

```text
Used transition id 21 because that was "In Review" on the last project.
```

---

### Fetch an issue with the fields you need

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_URL/rest/api/3/issue/PROJ-1234" | jq '{key, summary: .fields.summary, status: .fields.status.name, type: .fields.issuetype.name, labels: .fields.labels, description: .fields.description}'
```

Fetch the comment thread separately, because it is large and usually not needed:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_URL/rest/api/3/issue/PROJ-1234?fields=comment" | jq '.fields.comment.comments[] | {author: .author.displayName, created: .created[:10], body: .body}'
```

Search with JQL:

```bash
curl -s -G -u "$JIRA_EMAIL:$JIRA_API_TOKEN" --data-urlencode "jql=project = PROJ AND status = 'In Progress'" "$JIRA_URL/rest/api/3/search"
```

---

### Post a comment in Atlassian document format

The v3 comment endpoint takes a structured document, not a plain string. A plain string is rejected with a 400 that
does not say why.

```bash
curl -s -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Content-Type: application/json" -d '{"body":{"version":1,"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Branch feat/PROJ-1234 pushed."}]}]}}' "$JIRA_URL/rest/api/3/issue/PROJ-1234/comment"
```

Pass:

```text
Comment body wrapped in the doc structure with a paragraph node.
```

Fail:

```json
{"body": "Branch pushed."}
```

---

### Write only the fields the user named

Create or modify an issue only when the user asked for it, and set only the fields they named. Adding a label, a
component, a priority or a sprint on your own edits somebody else's board, and the change is invisible until a filter
returns the wrong set. Take the description template from the tracker rather than inventing one.

Pass:

```text
Asked for a bug in PROJ with that summary and description. Created exactly those two fields. Nothing else set.
```

Fail:

```text
Created it and added the "backend" component, priority High and the current sprint, since that seemed right.
```

---

### Propose updates as you go, at the points that carry information

Every row below is a proposal, not an action. Tell the user the transition or the comment you would make, and run it
only after they approve that one action.

| Moment in the work | What to propose for the issue |
|---|---|
| Work starts | Transition to the in-progress status |
| Branch created | Comment with the branch name |
| Tests written | Comment with what they cover |
| Pull request opened | Comment with the link, and link the issue |
| Pull request merged | Transition to the next status in the workflow |

Keep each comment short and link outward rather than pasting content. A comment that reproduces a test report goes
stale the moment the report is regenerated, and a link never does.

Pass:

```text
PR opened: <link>. 6 tests added covering the 429 path. Ready for review.
```

Fail:

```text
[400 lines of pasted test output]
```

---

### Defer the content of the item to project-tracking

What a good acceptance criterion looks like, how to size and split an item, which label taxonomy is allowed, and what
has to be true before an item closes are all owned by `project-tracking`. Read that skill before you write a
description, criteria or a closure comment, and use this skill only for getting that content into and out of Jira.

Where criteria are vague, ask before writing code rather than inventing an interpretation, and check linked issues
first so you understand the full scope of the feature.

---

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Token invalid, expired, or not exported into the agent's process | Check the environment, regenerate if needed |
| `403 Forbidden` | Token lacks permission on that project | Check token scope and project access |
| `404 Not Found` | Wrong key or wrong base URL | Verify `JIRA_URL` and the issue key |
| `400` on a comment | Body sent as a plain string | Wrap it in the Atlassian document structure |
| Transition rejected | ID belongs to a different workflow | Read the transitions for this issue first |
| Connection timeout | Network or VPN | Check VPN and firewall rules |
| MCP tools missing or asking to sign in | Server URL not in the agent's MCP file, or the OAuth sign-in never finished | Add the remote server URL, then finish the browser sign-in |

---

### Related skills

- `project-tracking` owns item kinds, sizing, acceptance criteria, labels, statuses and closure rules
- `github-ops` owns the same operational surface when the tracker is GitHub issues
- `git-workflow` owns branch naming and commit messages that carry the issue key
- `code-reviewer` owns reviewing the change the issue produced
- `security-review` owns handling and rotation of the API token itself

---

### Checklist

- [ ] Credentials come from the process environment, never a literal in a config file
- [ ] The MCP server is declared in the file the running tool actually reads
- [ ] Each MCP tool called is one the connected server actually lists
- [ ] Every transition and comment ran only after the user approved that one action
- [ ] Transitions were read for this issue before one was executed
- [ ] Only the fields the user named were written
- [ ] Comments link outward rather than pasting reports
- [ ] Item content follows `project-tracking`, not conventions invented here
