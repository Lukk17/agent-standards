---
name: code-reviewer
description:
  Use this skill to review code. It supports both local changes (staged or working tree)
  and remote Pull Requests (by ID or URL). It focuses on correctness, maintainability,
  and adherence to project standards.
---

# Code Reviewer

This skill guides the agent in conducting professional and thorough code reviews for both local development and remote
Pull Requests.

Review against the `coding-standards` hub (SOLID, DRY, error handling and exception chaining, immutability, explicit
state, architecture boundaries), plus `review-duplication` for reuse and `security-review` for security. Lead every
finding with a `path:line` reference.

---

### Workflow

#### 1. Determine Review Target
*   Remote PR: If the user provides a PR number or URL (e.g., "Review PR #123"), target that remote PR.
*   Local Changes: If no specific PR is mentioned, or if the user asks to "review my changes", target the current local
    file system states (staged and unstaged changes).

#### 2. Preparation

##### For Remote PRs:
1.  Checkout: Use the GitHub CLI to checkout the PR.
    ```bash
    gh pr checkout <PR_NUMBER>
    ```
2.  Preflight: Execute the project's standard verification suite to catch automated failures early.
    ```bash
    npm run preflight
    ```
3.  Context: Read the PR description and any existing comments to understand the goal and history.

##### For Local Changes:
1.  Identify Changes:
    *   Check status: `git status`
    *   Read diffs: `git diff` (working tree) and/or `git diff --staged` (staged).
2.  Preflight (Optional): If the changes are substantial, ask the user if they want to run `npm run preflight` before
    reviewing.

#### 3. In-Depth Analysis
Analyze the code changes based on the following pillars:

*   Correctness: Does the code achieve its stated purpose without bugs or logical errors?
*   Maintainability: Is the code clean, well-structured, and easy to understand and modify in the future? Consider
    factors like code clarity, modularity, and adherence to established design patterns.
*   Readability: Is the code consistently formatted according to our project's coding style guidelines, and does it
    read on its own without a comment propping it up?
*   Doc comments: Javadoc, docstrings, JSDoc, `///` and Go doc comments default to none, because code should explain
    itself through extraction and precise naming. Flag every doc comment that a well-named function or a tighter type
    would have made unnecessary, and flag any that merely restates the signature. Where one is genuinely needed the
    prose caps at five lines and is usually one, `@param` earns its place only for units, nullability, a valid range,
    or who owns the argument afterwards, `@return` only when non-obvious, and `@throws` is required for every
    exception a caller can act on because unchecked exceptions never appear in the signature. Every tag line is
    capped at one physical line, so a `@param` that wraps onto a second line is itself a finding: shorten it or
    delete it.
*   Efficiency: Are there any obvious performance bottlenecks or resource inefficiencies introduced by the changes?
*   Security: Are there any potential security vulnerabilities or insecure coding practices?
*   Edge Cases and Error Handling: Does the code appropriately handle edge cases and potential errors?
*   Testability: Is the new or modified code adequately covered by tests (even if preflight checks pass)? Suggest
    additional test cases that would improve coverage or robustness.

#### 4. Provide Feedback

##### Structure
*   Summary: A high-level overview of the review.
*   Findings:
    *   Critical: Bugs, security issues, or breaking changes.
    *   Improvements: Suggestions for better code quality or performance.
    *   Nitpicks: Formatting or minor style issues (optional).
*   Conclusion: Clear recommendation (Approved / Request Changes).

##### Tone
*   Be constructive, professional, and friendly.
*   Explain why a change is requested.
*   For approvals, acknowledge the specific value of the contribution.

#### 5. Cleanup (Remote PRs only)
*   After the review, ask the user if they want to switch back to the default branch (e.g., `main` or `master`).
