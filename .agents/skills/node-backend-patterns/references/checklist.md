# Node Backend Checklist

Run it before calling a change to a Node service, or a review of one, done.

- [ ] Handler, service, and repository responsibilities are separate.
- [ ] No `SELECT *` and no query inside a loop on any request path.
- [ ] Multi-statement writes run inside one transaction.
- [ ] Configuration is parsed once at startup against a schema, never read from `process.env` in business logic.
- [ ] Every error leaves through one handler as `application/problem+json`, with no internal detail in the body.
- [ ] Retries are capped, jittered, deadline-bound, and applied only to transient failures.
- [ ] Independent awaits run under `Promise.all`.
- [ ] Logging goes through one logger, never `console`, with `correlationId` and `requestId` on every request-path line.
- [ ] Async state is a discriminated union, not a bag of nullable fields.
- [ ] `SIGTERM` drains the server and closes the pools within a bounded timeout.
