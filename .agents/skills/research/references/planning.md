# Planning

How to break a topic down before the first query, and when to hand the parts to parallel subagents. Load this file
when a question needs more than one fact to answer, or when it covers a whole area rather than one behaviour.

---

### Split the topic into sub-questions first

A topic searched as one query returns whatever ranks, and the gaps stay invisible until the answer is written. Write
3 to 5 sub-questions before searching, each one answerable on its own and each one needed for the final answer.
Search per sub-question, keep one claim ledger across all of them, and say in the answer which sub-question found
nothing.

Pass:

```text
Topic: should we move the monorepo from npm workspaces to pnpm?
1. Which pnpm version is current, and which Node versions does it support?
2. Does our CI provider cache the pnpm store natively?
3. Which of our 40 dependencies break under pnpm's strict node_modules layout?
4. What does the migration path from package-lock.json look like in the pnpm docs?
```

Fail:

```text
Searched "npm vs pnpm" and summarised the top five results.
```

A single-fact lookup, such as the current version of one package, skips the split.

---

### Fan broad topics out to parallel subagents

When the sub-questions are independent and each needs several sources, run one subagent per sub-question in
parallel, if the runtime can spawn them. Each subagent starts with no shared state, so its prompt carries the
sub-question, the context behind it, the fetch date rule and this skill by name. Each one returns its ledger lines,
not a finished prose answer.

The parent owns the result. Merge the ledgers, drop the duplicates that trace back to one original, and re-check
every claim that decides the answer before relying on it, because a subagent can report a summarising fetch as a
quote.

Pass:

```text
Four subagents, one per sub-question, launched together. Merged 23 ledger lines. Re-fetched the two quotes the recommendation rests on and confirmed both.
```

Fail:

```text
One subagent researched all four sub-questions in sequence, and its summary went into the answer unchecked.
```

Keep a narrow question in one thread. Fanning out three subagents to find one version number costs more context than
it saves.
