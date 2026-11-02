# Access and REST Calls

Contents:

- [Add Atlassian's remote MCP server yourself](#add-atlassians-remote-mcp-server-yourself)
- [Fall back to REST v3 when no MCP server is available](#fall-back-to-rest-v3-when-no-mcp-server-is-available)
- [Know which MCP tool answers which question](#know-which-mcp-tool-answers-which-question)
- [Read a transition ID before transitioning](#read-a-transition-id-before-transitioning)
- [Fetch an issue with the fields you need](#fetch-an-issue-with-the-fields-you-need)
- [Post a comment in Atlassian document format](#post-a-comment-in-atlassian-document-format)
- [Troubleshooting](#troubleshooting)

Companion reference for the [jira-integration](../SKILL.md) skill. Load it when adding the Atlassian MCP server, falling back to REST v3, picking an MCP tool, or running a transition, fetch, search or comment call, and when a Jira call fails.

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

These names come from Atlassian's [supported tools](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/supported-tools/) page. A client connected to an older server version can still list older names, such as `getTransitionsForJiraIssue` and `addCommentToJiraIssue`, so call the name the connected server actually lists.

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

Search with JQL through `/rest/api/3/search/jql`. The older `/rest/api/3/search` is marked deprecated in the [issue search reference](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/), which says "Endpoint is currently being removed". The new endpoint returns issue IDs only unless `fields` names what you want, its reference says "By default, this resource returns IDs only", and it pages with `nextPageToken` rather than `startAt`. The query must be bounded, so keep a project or assignee restriction in it.

```bash
curl -s -G -u "$JIRA_EMAIL:$JIRA_API_TOKEN" --data-urlencode "jql=project = PROJ AND status = 'In Progress'" --data-urlencode "fields=summary,status,assignee" "$JIRA_URL/rest/api/3/search/jql" | jq '.issues[] | {key, summary: .fields.summary, status: .fields.status.name}'
```

Fail:

```bash
curl -s -G -u "$JIRA_EMAIL:$JIRA_API_TOKEN" --data-urlencode "jql=project = PROJ" "$JIRA_URL/rest/api/3/search"
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
