# Worked Steps

Contents:

- [Step 1: extract the core logic](#step-1-extract-the-core-logic)
- [Step 2: hypothesise where it would already live](#step-2-hypothesise-where-it-would-already-live)
- [Step 3: delegate the investigation](#step-3-delegate-the-investigation)
- [Step 4: evaluate against project conventions](#step-4-evaluate-against-project-conventions)
- [Step 5: report what should have been reused](#step-5-report-what-should-have-been-reused)

Each step of the duplication investigation in full, with its reasoning, the location table, the subagent names per agent runtime, and the pass and fail forms. Load this file when running a step and the one-line summary in SKILL.md is not enough.

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
- A fast read-only search subagent is the fan-out for locating candidates across many directories and naming
  conventions when you do not yet know where to look. It reads excerpts and returns locations, so use it to narrow the
  field before a deeper pass. The built-in one is `Explore` on Claude Code, `explore` on OpenCode, Kilo Code and the
  GitHub Copilot CLI, and `explorer` on Codex.
- A general subagent handles turn-intensive semantic comparison, for example: "compare the new `OrderSummaryCard`
  against every component in the shared component module and report which one could be extended instead". The
  built-in one is `general-purpose` on Claude Code and the GitHub Copilot CLI, `general` on OpenCode and Kilo Code, and
  `default` on Codex.

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

Before recommending a merge, confirm the two copies encode the same rule and change for the same reason. Coincidental
similarity across features is not a finding. A checkout formatter and a reporting formatter that match today but answer
to different owners stay separate, because a shared helper between them grows a flag for every caller. The DRY rule
behind this, including when to extract, is in `coding-standards`.

Fail: two lookalikes merged on shape alone.

```text
formatCheckoutTotal and formatReportTotal have the same body. Merge them into formatTotal.
```

Pass: the shared reason is shown before the merge is proposed.

```text
formatCheckoutTotal and formatInvoiceTotal both render the amount a customer is charged, and the last two changes touched
both. Merge them into formatChargedAmount.
```

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
