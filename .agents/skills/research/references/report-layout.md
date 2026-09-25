# Report Layout

An optional layout for a long answer or a written report. Use it when the user asks for a report, or when the answer
covers several sub-questions and would not fit the short shape in the evidence-and-output reference. A short answer
keeps the short shape.

---

### The layout

The report keeps every rule from the manifest: answer first, each claim labelled and dated, quotes read from raw
text. The layout only decides where things go.

```text
Title: <topic>, research report
Fetched: <date from the system clock> | Sources: <count of independent sources> | Overall confidence: high, medium or low

Answer
<two to four sentences that answer the question, with the recommendation if one was asked for>

Findings, one block per sub-question
<sub-question>
- Verified: "<quoted sentence>" <URL>, section "<heading>", fetched <date>, version <version>
- Inferred, medium: <claim>. Gap: <what is missing>
- Community, cross-checked: <claim>, <URL>, posted <date>

Comparison
<one like-for-like table, when options were compared, unknown cells marked unknown>

Case against
<what the search for the opposite found, or one line saying it found nothing>

Unknown
<each open point, with what would settle it>

Sources
<one line per source: URL, tier, fetch date, publish date or version>

Method
<the sub-questions, the tiers and tools used, which tools were missing and the route taken instead>
```

---

### Deliver it in the conversation

Post the report in the reply. Write it into a file only when the user asks for one, and then use `markdown-writer`
for the document. A report file the user did not ask for is a process file left behind.

Pass:

```text
Posted the report in the reply. No file written.
```

Fail:

```text
Saved the full report to research-report.md at the repository root and replied with a link.
```
