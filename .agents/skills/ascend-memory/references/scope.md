# Scope

Companion reference for the [ascend-memory](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- The user states a durable fact about themselves: a preference, a name, an ongoing project, a deadline.
- The user asks what they told you before, or the answer depends on a prior decision of theirs.
- The user asks you to save, remember, correct, or forget something.
- You are about to answer a question about the user's own life, work, or choices.
- The user says "remember that…", "what did I tell you about…", "save this for later" or "forget this", or prior context about the user would change the answer.

The service keeps long-term semantic memory for one user, in a per-user Qdrant namespace.

---

### When not to activate

- Running a web search or fetching a page for information you do not have, use `research`.
- Reading a page behind a WAF, a CAPTCHA or a login that blocks a normal fetch, use `ascend-web-hunter` if it is
  installed. It needs its own self-hosted service, so without it tell the user the page could not be read.
- Turning a recording into text before storing anything from it, use `audio-scribe` if it is installed. It needs
  its own self-hosted service, so without it ask the user for the text.
- Recording an architectural decision about a codebase rather than a fact about the user, use
  `architecture-decision-records`.

---

### Related skills

- `research` for information that lives on the web rather than in the user's history.
- `ascend-web-hunter` for a page behind a WAF, a CAPTCHA or a login that blocks a normal fetch, when it is installed.
- `audio-scribe` for turning a recording into text you might then store, when it is installed.
- `architecture-decision-records` for decisions about a codebase rather than facts about a person.
