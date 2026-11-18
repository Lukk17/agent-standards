# Posting

Companion reference for the [review-comments](../SKILL.md) skill. The gh commands that read the comments on a pull request and post the drafts the user approved. Every command runs only after the user has approved the exact text it posts. Each one reads that text from standard input through a quoted heredoc (`<<'EOF'`), so no draft is stored in a file, and the shell passes backticks, `$` and quotes in the text through unchanged, where a double-quoted `--body` argument would break on them or run them. Replace each `<...>` with the real value, and pick a different end word than `EOF` if a line of the text is exactly `EOF`.

---

### Reading the comments

The conversation comments and the reviews of a pull request:

```bash
gh pr view <number> --comments
```

The line comments, each with its `id`, `path`, `line` and `body`, which give the `path:line` of the chat layout and the ID a reply needs:

```bash
gh api repos/{owner}/{repo}/pulls/<number>/comments --paginate
```

gh fills `{owner}` and `{repo}` from the repository of the current directory.

---

### Posting a conversation comment

A point that is not about one line:

```bash
gh pr comment <number> --body-file - <<'EOF'
<approved text>
EOF
```

`gh pr comment --help` documents `-F, --body-file file` with the help text `Read body text from file (use "-" to read from standard input)`.

---

### Posting a line comment

A line comment is tied to a commit of the pull request, so read the head commit first:

```bash
gh pr view <number> --json headRefOid --jq .headRefOid
```

Then post one comment per small point. `-F body=@-` reads the text from standard input, `-F` sends `line` as a number, and `side=RIGHT` puts the comment on the new version of the file:

```bash
gh api repos/{owner}/{repo}/pulls/<number>/comments -F body=@- -f commit_id=<head commit> -f path=<path> -F line=<line> -f side=RIGHT <<'EOF'
<approved text>
EOF
```

`gh api --help` documents `-F, --field key=value` with the help text `Add a typed parameter in key=value format (use "@<path>" or "@-" to read value from file or stdin)`, and a value read this way is sent as a string.

GitHub documents `line` as "The line of the blob in the pull request diff that the comment applies to", and `commit_id` with the warning that "Not using the latest commit SHA may render your comment outdated if a subsequent commit modifies the line you specify" ([REST API, pull request review comments](https://docs.github.com/en/rest/pulls/comments)). The commit only addresses the comment and never appears in its text.

---

### Posting a reply

A reply goes under the review comment it answers, by that comment's `id`:

```bash
gh api repos/{owner}/{repo}/pulls/<number>/comments/<comment id>/replies -F body=@- <<'EOF'
<approved text>
EOF
```

The ID must be the first comment of the thread: "This must be the ID of a top-level review comment, not a reply to that comment. Replies to replies are not supported" (same page).

---

### Approving or requesting changes

An approval states the build result, so read the checks first:

```bash
gh pr checks <number>
```

The command exits with code 8 while a check is still pending (`gh pr checks --help`: "8: Checks pending"), so wait for a final result before drafting the approval. Then approve:

```bash
gh pr review <number> --approve --body-file - <<'EOF'
<approved text>
EOF
```

`gh pr review --help` documents `-F, --body-file file` with the help text `Read body text from file (use "-" to read from standard input)`.

A request for changes:

```bash
gh pr review <number> --request-changes --body-file - <<'EOF'
<approved text>
EOF
```
