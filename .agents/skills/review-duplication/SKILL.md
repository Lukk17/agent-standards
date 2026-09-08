---
name: review-duplication
description: Investigate a change for duplicated logic, reinvented utilities, and missed reuse of the project's existing helpers, patterns and installed libraries, then report what should have been reused and how. Use when you say "check this PR for duplication", "did we already have a function for this", "is this reinventing something", "why is there a second date formatter", or "review this for reuse before I approve it". Not for a full multi-pillar review pass, use `code-reviewer`.
---

# Review Duplication

Investigate a codebase during review to find logic the project already has, utilities that were reinvented, and
established patterns the change walked past. The conventions you check reuse against, and the DRY principle behind this
skill, live in the `coding-standards` hub.

---

### When to activate

- Reviewing a change that introduces a helper, formatter, validator, client wrapper, or generic component.
- A new third-party dependency or a new import of an existing one appears in the diff.
- The user asks whether something already exists in the project, or why two similar things now exist.
- A reviewer's instinct says "we have this somewhere", and the location needs to be found before the review is
  finalised.

---

### When not to activate

- The full review pass across correctness, security, performance and tests. Use `code-reviewer` and invoke this skill as
  its reuse step.
- Mapping an unfamiliar codebase for its own sake rather than for one change. Use the `code-archaeologist` agent
  directly.
- Deciding whether a new dependency is admissible and where its version is pinned. Use `build-dependency-management`.
- Restructuring the duplicated code once it is found. Use the language skill that owns it, such as `python-patterns`,
  `golang-patterns`, or `java-coding-standards`.

---

### Step 1: extract the core logic

Look past the business wrapper to the mechanics underneath: the algorithm, the utility function, the generic data
structure, the reusable component. Reuse is found by shape, not by feature name.

Fail: the search is framed around the feature and finds nothing.

```text
Searching for "checkout retry banner".
```

Pass: the search is framed around the mechanic, which the project may already implement elsewhere.

```text
The new code debounces input and formats a relative timestamp. Searching for existing debounce helpers and relative-time formatting.
```

---

### Step 2: hypothesise where it would already live

Name concrete candidate locations from the repo root before searching, so the search is directed rather than exhaustive.
Read the project's own layout first, then map each category onto it. In a layered service the categories usually land
like this:

| Category | Typical home |
| --- | --- |
| Shared utilities | a `utils`, `common`, or `shared` module under the source root |
| UI components | the component directory of the front-end module |
| Domain services | the service or use-case layer of the application module |
| Configuration | the config module, plus environment schema files |
| Cross-cutting logic | the core or domain module, when the behaviour is not presentation specific |

Trace third-party dependencies too. When the diff introduces an import of a utility library, find how the project
already uses that library, because a wrapper or a shared helper usually exists. Before flagging a hand-written
implementation of a standard algorithm, check the manifest (`package.json`, `pyproject.toml`, `build.gradle.kts`,
`go.mod`) for a library already installed that provides it.

---

### Step 3: delegate the investigation

Delegate deep searching to subagents so the review session stays readable and the search stays thorough. Give each one a
specific objective built from the mechanics found in step 1, not a vague "look for duplication".

- `code-archaeologist` is the primary researcher for structural questions. Ask it about the underlying APIs in use
  ("does any existing code call `Intl.DateTimeFormat` or a date library for the same purpose?"), naming patterns ("are
  there existing symbols matching `*Format*` or `*Debounce*`?"), where the behaviour is centralised today, and,
  crucially, how the new code could be refactored onto whatever it finds.
- `Explore` is the fast fan-out for locating candidates across many directories and naming conventions when you do not
  yet know where to look. It reads excerpts and returns locations, so use it to narrow the field before a deeper pass.
- `general-purpose` handles turn-intensive semantic comparison, for example: "compare the new `OrderSummaryCard` against
  every component in the shared component module and report which one could be extended instead".

Keep a fast path for unambiguous single-fact checks. Grepping the manifest for one package name is faster done directly
than delegated. Anything open-ended goes to a subagent.

---

### Step 4: evaluate against project conventions

Duplication is not only copied functions. A change that bypasses an established pattern duplicates the decision behind
it.

- Error handling: does it use the project's error types and logging entry point, or invent its own?
- State management: does it bypass an established store, context, or repository?
- Styling: does it hardcode colours and spacing instead of using the project's tokens?
- Configuration: does it read an environment variable directly where the project has a config object?

When the change introduces a genuinely new pattern, say so explicitly and compare it against the documented standard,
rather than letting a second way of doing the same thing land silently.

---

### Step 5: report what should have been reused

A useful finding names the replacement and shows the call. A useless one names the problem and leaves the work to the
author.

Fail: unactionable.

```text
This looks like it duplicates something we already have.
```

Pass: names the source, shows the integration, and states the benefit.

```text
This adds a new `formatDate` helper. The project already has a tested one in `src/utils/date-helpers.ts`.

Replace the new function with:

    import { formatDate } from '../utils/date-helpers'
    const displayDate = formatDate(userDate, 'MMM d, yyyy')

Reusing it keeps formatting consistent across the app and inherits the timezone handling the shared helper already covers.
```

Cite the path and the exact symbol, project-relative, on every finding, and explain the value in one clause:
consistency, maintenance, or edge cases the existing code already handles.

---

### Related skills

- `code-reviewer` is the parent review workflow. This skill is its reuse step and findings feed back into that report.
- `coding-standards` holds the DRY principle and the conventions reuse is judged against.
- `build-dependency-management` owns whether a newly imported library should be there at all.
- `hexagonal-architecture` helps when the duplication is a boundary problem rather than a copied function.

---

### Checklist

- [ ] The underlying mechanic was named, not just the feature.
- [ ] Candidate locations were hypothesised from the project's real layout before searching.
- [ ] Any newly imported library was traced to its existing usage and wrapper.
- [ ] The manifest was checked for an installed library that already solves the problem.
- [ ] Open-ended searching was delegated to `code-archaeologist`, `Explore`, or `general-purpose`.
- [ ] Convention bypasses were checked, not only copied code.
- [ ] Every finding names the reusable symbol, its path, and how to call it.
- [ ] Findings were folded back into the `code-reviewer` report.
