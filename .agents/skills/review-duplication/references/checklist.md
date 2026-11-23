# Review Duplication Checklist

Run it before folding the findings into the review.

- [ ] The underlying mechanic was named, not just the feature.
- [ ] Candidate locations were hypothesised from the project's real layout before searching.
- [ ] Any newly imported library was traced to its existing usage and wrapper.
- [ ] The manifest was checked for an installed library that already solves the problem, blank checks and format detection included.
- [ ] Open-ended searching was delegated to `code-archaeologist`, a read-only search subagent, or a general subagent, or, from a subagent that cannot spawn one, done directly with grep and glob and the delegation named for the caller.
- [ ] Convention bypasses were checked, not only copied code.
- [ ] Every proposed merge shows the two copies encode the same rule and change for the same reason.
- [ ] Every finding names the reusable symbol, its path, and how to call it.
- [ ] Findings were folded back into the `code-reviewer` report.
