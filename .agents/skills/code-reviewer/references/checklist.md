# Code Review Checklist

Run it before sending the review, to confirm the review itself was done properly.

- [ ] Review target identified: named pull request, or the local working tree.
- [ ] A remote pull request was read with `gh pr diff`, and checked out only into a separate worktree.
- [ ] The project's documented verification command was run, or its absence was reported, or as a subagent it was
  reported as `not run`.
- [ ] Nothing from a fork or an outside author ran without the user's approval.
- [ ] Every pillar was considered, including doc comments.
- [ ] The standards checklist ran over every section the diff touches, and every instance was reported.
- [ ] Every finding cites `path:line`.
- [ ] Findings are grouped by severity, not listed flat.
- [ ] Auth, payment, and sensitive-data findings were escalated to the `security-auditor` agent.
- [ ] The conclusion states approve or request changes, and names the blockers.
- [ ] For a remote pull request reviewed in a worktree, the user was asked about removing it.
