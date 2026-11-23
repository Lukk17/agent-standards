# Express

The Express 5 form of the core rules. Open it when the service is an Express app. The reasoning behind each rule is in [core-rules.md](core-rules.md).

---

### Layering

A handler parses and responds, a service holds the business rule, and a repository is the only thing that speaks to the database. This skill owns the layering, error responses, logging, and shutdown of an Express route.

---

### Error responses

Every error leaves through the one handler in [core-rules.md](core-rules.md#return-every-error-through-one-handler-as-problemjson).

Fail: `res.status(500).json({ error: err.message })`, which ships the database error text to the caller.

---

### Startup hook

The startup readiness block is emitted from the `app.listen` callback, in one log call.
