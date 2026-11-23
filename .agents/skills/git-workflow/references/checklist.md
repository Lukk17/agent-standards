# Git Workflow Checklist

Run it before committing, and again before requesting review on a pull request.

- [ ] One branching strategy chosen and followed consistently
- [ ] Every commit message carries a type and an imperative subject, with a body explaining why
- [ ] Nothing shared was rebased, and nothing was pushed without an explicit instruction
- [ ] Branch names carry a type prefix and a readable subject
- [ ] Merged branches deleted locally and on the remote
- [ ] Only intended paths staged, verified before committing
- [ ] Pull request states what, why, how and how it was tested, and is under about five hundred lines
- [ ] CI green and self-review done before review was requested
- [ ] Description short, not reading as AI-written, linking the related open issues, with no walk through many files
- [ ] An integration pull request lists the pull requests it contains, not loose commits
- [ ] Description draft printed in full in the chat, numbered, posted only after approval, with no AI trace, commit hash, placeholder number, em dash, en dash, joining semicolon, bold or italic
- [ ] No secret and no generated artifact in the commit
