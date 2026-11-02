# Planning the Work

Contents:

- [Define completion before execution](#define-completion-before-execution)
- [Run a capability eval and a regression eval](#run-a-capability-eval-and-a-regression-eval)
- [Size units so one agent can finish and verify one](#size-units-so-one-agent-can-finish-and-verify-one)
- [Route by capability tier, not by habit](#route-by-capability-tier-not-by-habit)
- [Verify external interfaces before using them](#verify-external-interfaces-before-using-them)

Companion reference for the [agentic-engineering](../SKILL.md) skill. Load it for the reasoning and the pass and fail examples behind the planning rules: the done condition, the two evals, unit sizing, capability tiers, and checking external interfaces.

---

### Define completion before execution

Write the done condition before any code is generated. An agent given a goal but no completion test explores widely
and retries, which burns time and produces work nobody asked for.

Pass:

```text
Done when POST /orders rejects a negative quantity with 422 and the existing order tests still pass.
```

Fail:

```text
Done when the order endpoint handles bad input properly.
```

---

### Run a capability eval and a regression eval

Two different measurements answer two different questions. A capability eval asks whether the new behaviour now
works, and it is expected to fail before the change. A regression eval asks whether anything that already worked
stopped working, and it is expected to pass before and after. Running only the first ships breakage. Running only the
second ships nothing.

Take a rate limiter added to a login endpoint.

Capability eval, expected to fail at baseline and pass afterwards:

```text
Send 11 login attempts for one account in 60 seconds. Expect the 11th to return 429 with a Retry-After header.
```

Regression eval, expected to pass at baseline and still pass afterwards:

```text
Send 1 valid login. Expect 200 and a session cookie. Send 1 wrong password. Expect 401 and no cookie.
```

The loop is: define both, run both to capture the baseline and the failure signature, implement, re-run both, and
compare the deltas rather than reading the final run alone.

Fail:

```text
Wrote the rate limiter, ran the full suite once at the end, it was green, shipped.
```

---

### Size units so one agent can finish and verify one

Aim at a unit an agent can complete in roughly a quarter of an hour of work. Each unit is independently verifiable,
carries a single dominant risk, and exposes a clear done condition. A unit with two risks fails in a way that takes
longer to diagnose than the unit took to write.

Pass:

```text
Unit 1: add the migration adding orders.cancelled_at, nullable, with a down migration. Risk: migration lock time.
Unit 2: expose cancelled_at on the order response DTO. Risk: contract change for existing clients.
```

Fail:

```text
Unit 1: add order cancellation end to end, migration through UI.
```

---

### Route by capability tier, not by habit

Match the strength of the model to what the unit actually demands, and describe the tier by what it is for rather
than by a product name, because names change and a skill that hardcodes them goes stale.

Pick the tier when you spawn the unit. A subagent definition never pins a model, so the same subagent runs on a small tier for a mechanical edit and on the strongest tier for a design review.

| Tier | Use it for | Signal you picked wrong |
|---|---|---|
| Small and fast | Lookups, classification, mechanical transforms, narrow single-file edits | It gets the answer right but you did not need it that fast |
| Mid capability | Bounded implementation, refactors inside known boundaries, test writing | It loops on the same failure without new reasoning |
| Strongest available | Architecture, root-cause analysis, cross-file invariants, final review | You are paying design rates for a rename |

Escalate a tier only after the lower tier fails with a visible reasoning gap, and say what the gap was. Escalating on
the first error teaches you nothing about whether the task was actually hard.

Pass:

```text
Small tier rewrote the 40 import paths. Mid tier implemented the handler. Strongest tier reviewed the transaction boundary.
```

Fail:

```text
Used the strongest tier for everything because it is the safest choice.
```

---

### Verify external interfaces before using them

Before implementing against an external API, SDK or library, check the current documentation. Training data goes
stale and an invented method signature costs more to debug than it costs to look up. When documentation is
unavailable, state the assumption out loud before writing code against it.

Pass:

```text
Checked the current SDK reference: the client takes a config object, not positional args, since v4. Implementing that.
```

Fail:

```text
The client constructor takes the API key as the first argument.
```
