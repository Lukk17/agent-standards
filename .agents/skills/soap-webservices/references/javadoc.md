# Javadoc on SOAP Code

Companion reference for the [soap-webservices](../SKILL.md) skill. Load it when writing or reviewing a Javadoc block on an endpoint, a client or a mapping class.

---

### Javadoc

Default to none. A Javadoc block is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named method, rename the parameters so they carry their own meaning, and tighten the
types. Do that first and most Javadoc blocks have nothing left to say, which is the outcome you want. Code that
explains itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@param` and `@return` and `@throws` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `@param` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or
   who owns the argument afterwards. `@param orderId the wholesale order identifier` is noise, delete it.
3. `@return` only when it is non-obvious.
4. `@throws` always, for every exception a caller can act on. Unchecked exceptions never appear in the signature, so
   this one is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

```java
// GOOD: one sentence, then only what the signature cannot say
/**
 * Maps the inbound reservation request onto the domain and returns the ack.
 *
 * @throws ReservationFault when the warehouse cannot cover the request
 */
@PayloadRoot(namespace = NS, localPart = "ReserveRequest")
public ReserveResponse reserve(@RequestPayload ReserveRequest request) { ... }

// BAD: restates the signature and the annotation
/**
 * Handles the reserve request.
 *
 * @param request the reserve request
 * @return the reserve response
 */
public ReserveResponse reserve(@RequestPayload ReserveRequest request) { ... }
```
