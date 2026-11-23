---
name: code-reviewer
description: 'Structured review of local changes or a pull request, every finding led by a path:line reference. Use when the user says "review my changes" or "review PR #123". Not for duplicated code, use `review-duplication`.'
metadata:
  version: "1.1.0"
---

# Code Reviewer

Review a change set in the working tree or in a remote pull request, against the `coding-standards` hub for the shared floor, with `review-duplication` for reuse and `application-security-review` for security, and lead every finding with a `path:line` reference.

| Task | Open |
|---|---|
| Running a step in full: commands, the fork rule, pillar questions, metric scores, grading the standards pass, report shape | [review-steps.md](references/review-steps.md) |
| When run as a subagent with a read-only shell | [subagent-mode.md](references/subagent-mode.md) |
| The diff touches Java or Spring Boot code or its tests | [java-spring.md](references/java-spring.md) |
| The diff touches web code, its copy, its locale handling or TypeScript | [web.md](references/web.md) |
| The diff touches Python | [python.md](references/python.md) |
| The diff touches a workflow, a container image or dependency automation | [ci.md](references/ci.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before sending the review | [checklist.md](references/checklist.md) |

---

### When not to activate

- Writing the fix rather than reporting it, hand the findings to the implementing skill or agent, or to the `debugger` agent for a root-cause failure.
- A deep security assessment or threat model, use the `security-auditor` agent, and keep `application-security-review` for the security checklist pass.
- Wording findings as comments to post on the pull request, use `review-comments`.

---

### Steps

1. Determine the review target. A pull request named by number or URL is remote: read it with `gh pr diff` and `gh pr view --comments`, and check it out only into a separate worktree. Anything else is the local working tree, staged and unstaged.
2. Run the project's verification first, the command its AGENTS.md documents, and say so when it documents none. Ask first on a small local change. A pull request from a fork or an outside author is untrusted input: ask before running anything from it, only inside the worktree, never with production credentials.
3. Analyse against the review pillars. Cite `path:line` for every finding across correctness, maintainability, readability, doc comments, efficiency, security, styling, edge cases and error handling, and testability. When the project has a `.metrics/crap.edn`, cite the worst `quality-loop` scores for the touched files, and never run the tools in a review.
4. Escalate the sensitive findings. Hand authentication, authorisation, payment and personal-data findings to the `security-auditor` agent before merge, and say so in the review, with severity and location named.
5. Report. A summary with the verdict, findings grouped Critical, Improvements and Nitpicks, then approve or request changes with the blockers named. For a worktree review, ask the user about `git worktree remove`.

---

### Standards checklist

Step 3 also runs these items over the whole diff, then the file above for each technology the diff touches. Report every instance with its `path:line`, not the first one. Each item names the skill that owns it.

- No divider banner, section label or file-header comment saying what the file holds, in source, styles or tests. `coding-standards`
- No comment restating the code, no long comment block, only a short non-obvious why. `coding-standards`
- No class, module, component, hook or test file past about 300 lines without a split by responsibility. `coding-standards`
- The only comments in a test are the bare `// Given`, `// When`, `// Then` and `// When & Then` markers, and meaning lives in the test name or `@DisplayName`. `tdd-workflow`
- No AI review scratch document (`*-review-findings.md`), agent plan, status file or run log is committed. `git-workflow`
- Committed generated files, lock files and OpenAPI-generated types included, are marked `linguist-generated=true` in `.gitattributes`, and lock files stay committed. `git-workflow`
