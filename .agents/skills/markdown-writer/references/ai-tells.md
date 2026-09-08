# AI Tells in Technical Prose

The patterns below are the ones a reader notices first when a document was generated rather than written. Each entry
names the pattern, says why it reads as machine output, and gives the repair. Load this file when auditing prose for
voice, or when a draft feels flat and you need a name for what is wrong with it.

---

### Cadence uniformity

The strongest single signal. Generated prose settles into sentences of roughly eighteen to twenty-four words and
holds that length paragraph after paragraph, which produces a metronome a reader feels without being able to name.

Repair: mix short sentences of five to ten words with long ones of twenty-five to forty. Read the draft aloud. If it
sounds like a steady drumbeat, split one sentence and merge two others.

Before:

```text
The service exposes a REST interface for job submission and status queries. Clients authenticate with a bearer token issued by the identity provider. The queue guarantees at-least-once delivery for every accepted job. Workers acknowledge completion through a separate endpoint.
```

After:

```text
The service exposes a REST interface for job submission and status queries, and clients authenticate with a bearer token from the identity provider. Delivery is at-least-once. Workers acknowledge separately.
```

---

### Stacked parallel structures

Three-beat lists with matched rhythm ("fast, reliable, and affordable") and blocks where every bullet opens with the
same syntax. One per section at most, and only when the parallel really is the point.

Repair: break the rhythm by varying bullet openings, or collapse the list into a sentence.

---

### Negative parallelisms

"It is not just X, it is Y." "These are not merely A, they are B." "Not only that, but also."

Repair: state the positive claim directly and delete the negated half.

Before:

```text
This is not just a queue, it is a full job orchestration platform.
```

After:

```text
It orchestrates jobs: retries, scheduling, and dependency ordering.
```

---

### Filler intensifiers and transitions

"It is worth noting that", "It is important to consider", "Furthermore", "Moreover", "In today's world",
"Importantly".

Repair: delete the phrase. The information after it survives untouched, which is the proof the phrase carried none.

---

### Boilerplate closers

"One thing is clear", "As X continues to evolve", "In conclusion", "Ultimately".

Repair: end on the actual point. A technical document needs no wind-down.

---

### Hedging stacks

"This approach can be a useful tool for many teams in certain situations." Four qualifiers in one sentence, each
softening the claim until nothing is asserted.

Repair: keep one qualifier or none, and name the condition that the hedge was gesturing at.

Before:

```text
This approach can often be a fairly useful option for many projects in certain circumstances.
```

After:

```text
Use this when the job rate stays under about 10,000 per second.
```

---

### Rigid paragraph structure

Every paragraph opens with a topic sentence, adds two or three supports, closes with a summary. It reads like an
essay-grading rubric because that shape is what the rubric rewards.

Repair: lead with the result, start mid-thought, or let a single sentence be the whole paragraph.

---

### Marketing adjectives with no payoff

"comprehensive", "robust", "seamless", "leverage", "delve", "elevate", "unlock", "cutting-edge", "revolutionary".

Repair: replace the adjective with the fact it was standing in for, such as a case count or a latency figure. If no
fact exists, delete the adjective and keep the noun.

Before:

```text
A robust, comprehensive caching layer that seamlessly accelerates reads.
```

After:

```text
Caches read results for 60 seconds, which cuts p99 read latency from 40ms to under 3ms.
```

---

### Rhythm chains

"fast, reliable, affordable, tested, scalable, secure". The em dash version of this is banned outright, but the
rhythm reads as generated even with commas or semicolons doing the work.

Repair: split the chain into two sentences, or pick the one term that carries information.

---

### Audit procedure

Read the draft once for cadence, once for vocabulary, once for structure. Report findings as a list of passages with
the pattern named, and offer the repair rather than applying it silently, so the author can keep a phrasing they
chose on purpose.
