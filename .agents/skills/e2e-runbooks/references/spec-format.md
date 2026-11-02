# Spec Format

Contents:

- [Directory layout](#directory-layout)
- [The three-file triple](#the-three-file-triple)
- [Spec sections, fixed and in order](#spec-sections-fixed-and-in-order)

Companion reference for the [e2e-runbooks](../SKILL.md) skill. Load it when scaffolding the `e2e/` tree, creating the spec, template and run-record triple, or writing the seven spec sections and the tasks-template.

---

### Directory layout

Scaffold once per project. The OpenSpec schema does this automatically on first use. Without it, create the tree by
hand.

```text
e2e/
├── README.md
├── fixtures/
│   └── README.md
└── testing/
    ├── README.md
    ├── 1-<capability>-test.md
    ├── templates/
    │   └── 1-<capability>-tasks.template.md
    └── runs/
        ├── README.md
        └── <ts>_<N>-<capability>-tasks.md
```

Add this to the project root `.gitignore`, which drops the ephemeral run records and keeps the runs README tracked.

```text
e2e/testing/runs/*.md
!e2e/testing/runs/README.md
```

The four README files carry the conventions: what the suite covers, the canary content per fixture, the spec and
template format, and the runner contract. The OpenSpec schema ships canonical text for each, and the [scaffold templates
in the schema repo](https://github.com/Lukk17/openspec-schemas/tree/master/e2e-runbooks/templates/scaffold) are the
source to copy from when scaffolding by hand.

---

### The three-file triple

Every capability test is three files, and the split is what makes a run auditable.

- `e2e/testing/{N}-{capability}-test.md`, the immutable spec. Seven fixed sections. Never edited between runs. When
  behaviour changes, write a new spec with a new `{N}`.
- `e2e/testing/templates/{N}-{capability}-tasks.template.md`, the immutable checklist. Mirrors the spec's Prerequisites,
  Reset, Run and Expected sections as checkboxes.
- `e2e/testing/runs/{utc-timestamp}_{N}-{capability}-tasks.md`, the execution record. Copied from the template at run
  start, ticked off as the run progresses, closed with a Result summary, a Verdict, and token counts. Gitignored by
  default.

Editing a spec to make a failing run pass destroys the record. Fix the system, or write a new spec.

---

### Spec sections, fixed and in order

Every spec has these seven sections, in this order, every time.

1. What this verifies. Bullet list of concrete, observable behaviours.
2. Prerequisites. Concrete check commands, one per fenced block, with the success criterion in the prose around the
   block. The runner executes each before starting and aborts on failure.
3. Reset state. One command per block, in execution order, wiping whatever the test will write so the run is
   reproducible. Use "None. This test does not write persisted state." when that is true.
4. Run. Numbered API-client invocations. Multi-step tests tell the runner to wait for success before continuing.
5. Expected. Observable assertions only, verified after each Run step.
6. Fixtures. Paths to local files the test reads, each with distinctive canary content. Use "None." if none.
7. Concurrency. The resources this test mutates, plus a `Serial:` flag.

The tasks-template mirrors it as checkboxes plus the accounting fields.

```text
### Prerequisites
- [ ] <one checkbox per prereq>

### Reset state
- [ ] <one checkbox per reset command>

### Run
- [ ] <one checkbox per numbered Run step>

### Expected
- [ ] <one checkbox per assertion>

### Verdict
- [ ] Verdict: PASS / FAIL (delete the wrong one)

Result summary: <one paragraph anchored to the Expected assertions>
Input tokens:
Output tokens:
Start (UTC):
End (UTC):
Duration:

Additional tasks I did: <anything off-spec>
```
