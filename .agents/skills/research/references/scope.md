# Scope

Companion reference for the [research](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- A question depends on how a library, tool, service or vendor behaves today
- The user asks for a current version, a supported option, a price, a limit or a compatibility fact
- Two or more options have to be compared before a decision
- A failure looks like a known bug needing its issue, status and workaround
- A claim in a document or a review has no source behind it
- The user says "look this up", "does tool Y support Z", "compare these options", "is this a known bug", "research X", "what is the current version", "find a workaround", "deep dive into X" or "check the docs"

The skill covers source order from Context7 to the web, quoting the deciding sentence, measuring instead of reading, labelling each claim, and like-for-like comparisons.

---

### When not to activate

- The page blocks a plain fetch with a WAF, a CAPTCHA or a login wall, use `ascend-web-hunter` if it is installed,
  which needs its own self-hosted service, else report the page as blocked, as [source-order.md](source-order.md) says
- The answer is already in the repository, read the code and the docs instead
- Recalling what the user said in an earlier conversation, use `ascend-memory` if it is installed, else ask the user
- Writing the result into a human-facing document, use `markdown-writer`
- Recording the decision the research led to, use `architecture-decision-records`

---

### Related skills

- `ascend-web-hunter` owns fetching pages behind a WAF, a CAPTCHA or a login, when it is installed, because it needs
  its own self-hosted service
- `markdown-writer` owns writing the findings into a document
- `architecture-decision-records` owns recording the decision the research supported
- `automation-inventory` owns proving which automations are live, with the same command-and-output rule
