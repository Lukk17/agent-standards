# Comment Examples

Contents:

- [Comment only on what the pull request changes](#comment-only-on-what-the-pull-request-changes)
- [Keep it to one to three sentences](#keep-it-to-one-to-three-sentences)
- [Say what is wrong and nothing else](#say-what-is-wrong-and-nothing-else)
- [Be firm on a point that must be fixed](#be-firm-on-a-point-that-must-be-fixed)
- [Put each point where it belongs](#put-each-point-where-it-belongs)
- [Approve with the build result, not praise](#approve-with-the-build-result-not-praise)
- [Reply with fixed, how, or why not](#reply-with-fixed-how-or-why-not)
- [Back a reply with a source](#back-a-reply-with-a-source)
- [Never point at a chat](#never-point-at-a-chat)
- [Explain every abbreviation in each message](#explain-every-abbreviation-in-each-message)
- [Drafts and posting](#drafts-and-posting)
- [Laying out other people's comments in chat](#laying-out-other-peoples-comments-in-chat)

Companion reference for the [review-comments](../SKILL.md) skill. Load it for the reasoning and the pass and fail examples behind each rule. Every number, path and name below is an example.

---

### Comment only on what the pull request changes

A comment on code the pull request did not touch asks the author to widen their change, and a comment on something a later linked pull request already fixes costs them a reply for nothing. Read every linked pull request before writing the first comment.

Pass:

```text
This new retry loop has no upper bound, so a dead upstream keeps the request open forever.
```

Fail:

```text
While you are here, the logging in OrderMapper could use a cleanup too.
```

---

### Keep it to one to three sentences

A reviewer who writes a paragraph buries the point. One to three sentences hold the problem and, where it helps, the change that fixes it.

Pass:

```text
The cache key leaves out the tenant, so two tenants can read each other's prices. Add the tenant identifier to the key.
```

Fail:

```text
I was looking at this and thinking about how caching works in general in this service, and I remember we had a similar problem last year, so I wanted to raise that the key here might be missing something, possibly the tenant, which could mean that in some cases...
```

---

### Say what is wrong and nothing else

Polite and friendly comes from plain words, not from filler. A comment says what is wrong, if anything, and stops.

Pass:

```text
This query runs once per order line. One query with an IN list would do the same work.
```

Fail:

```text
Thanks for this! Good catch on the null check. Fair point about the naming too. One tiny thing, if you have a moment...
```

---

### Be firm on a point that must be fixed

A blocker worded as a suggestion gets treated as optional. Stay friendly, and say clearly what has to change.

Pass:

```text
The token is written to the log here at info level. Please remove it before this merges.
```

Fail:

```text
Maybe consider whether logging the token is a good idea?
```

---

### Put each point where it belongs

A point about the whole change, such as the approach or a missing test suite, goes in a normal conversation comment. Each small point gets its own comment on its own line, so each can be resolved on its own.

Pass, as a conversation comment:

```text
There is no test for the cancel path in this change. Please add one for a paid order and one for a shipped order.
```

Fail, as one line comment holding three points:

```text
Rename this, also the timeout on line 80 is too short, and the test file is missing a case.
```

---

### Approve with the build result, not praise

An approval tells the author and the next reviewer the change is fine and the build agrees. Praise adds nothing they can act on.

Pass:

```text
Build green, all checks passed.
```

Fail:

```text
Looks great, really clean work, love it!
```

---

### Reply with fixed, how, or why not

A reply to a review comment answers one question: what happened to the point. It says it is fixed, how in a few words where that is not obvious, or why it is not fixed.

Pass:

```text
Fixed, the lock is now released in a finally block.
```

Pass:

```text
Not changed, the retry limit is set per client in the service configuration, as docs/adr/0007-retry-policy.md records.
```

Fail:

```text
Good catch, thanks! Fixed in 3f9c2ab along with a few other things I noticed while I was there.
```

---

### Back a reply with a source

A reply that declines a change or moves it to later points to what decided it: a decision record, a project document or a ticket. When the work moved to later, the ticket number is the source.

Pass:

```text
Moved to later, #512 tracks the pagination change.
```

Fail:

```text
We will do this later.
```

---

### Never point at a chat

A decision number from a chat with an agent or a teammate means nothing to someone reading the pull request. Name the decision record or the ticket instead, or say the reason in the reply.

Pass:

```text
Not changed, docs/adr/0012-event-ordering.md keeps ordering per aggregate only.
```

Fail:

```text
Not changed, see decision 4 from our discussion.
```

---

### Explain every abbreviation in each message

A reader often lands on one reply from a notification, without the thread above it. Explain each abbreviation at its first use in every comment and every reply, even when an earlier message already did.

Pass:

```text
This is still a PoC (proof of concept), so the SLA (service level agreement) checks come in #530.
```

Fail:

```text
Still a PoC, SLA checks come later.
```

---

### Drafts and posting

Every draft is printed in full in the chat, numbered, so the user can approve, change or drop each one by its number. A draft never goes into a file, because a file outlives the session and reads as project truth. Nothing is posted before the user approves it, and replies wait until every fix is done, green and pushed, because a reply that says fixed must be true the moment it appears.

Pass:

```text
1. src/orders/OrderService.java:142, reply: Fixed, the lock is now released in a finally block.
2. Conversation comment: Moved to later, #512 tracks the pagination change.
```

Fail:

```text
I wrote the replies to review-replies.md and posted the first two already.
```

No posted text carries a trace of an agent or tool, a commit hash or a placeholder such as `#XXX`, and none uses an em dash, an en dash, a semicolon joining two clauses, bold or italic.

---

### Laying out other people's comments in chat

When working through comments on our code, each comment gets a horizontal line, then its `path:line`, then the comment quoted, then our response, so the user can match every answer to its comment at a glance. A blank line goes before the horizontal line and between each of the four, because the chat renders markdown: without them the `---` turns the line above it into a heading, and our response runs into the quote.

Pass:

```text
---

services/orders/src/main/java/com/example/orders/OrderService.java:142

> This lock is never released on failure.

Fixed, the lock is now released in a finally block.
```

Fail:

```text
The reviewer said something about a lock in OrderService, which I fixed, and also mentioned the tests.
```

Fail, with no blank lines, so the chat turns the line above the `---` into a heading and shows the response inside the quote:

```text
---
services/orders/src/main/java/com/example/orders/OrderService.java:142
> This lock is never released on failure.
Fixed, the lock is now released in a finally block.
```
