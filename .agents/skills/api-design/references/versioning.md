# API versioning and deprecation

Read this when introducing a version, planning a breaking change, or retiring an old endpoint.

---

### Version in the URL path

```text
/api/v1/users
/api/v2/users
```

It is explicit, trivial to route, cacheable by a proxy, and visible in every log line. The cost is that the URL changes
between versions, which matters less than being able to see which version a caller is on.

---

### Header versioning is the alternative, not the default

```text
GET /api/users
Accept: application/vnd.myapp.v2+json
```

URLs stay clean, and that is the whole benefit. The version is invisible in logs and browser address bars, easy to
forget in a client, and awkward to exercise from a shell. Choose it only when a partner contract requires it.

---

### Decide whether the change actually needs a version

Additive changes do not, because a correct client ignores what it does not know about.

| No new version | New version |
| --- | --- |
| Adding a field to a response | Removing or renaming a field |
| Adding an optional query parameter | Changing a field's type |
| Adding an endpoint | Changing the URL structure |
| Relaxing a validation rule | Tightening a validation rule |
| Adding an enum value a client may ignore | Adding an enum value a client must handle |
| | Changing the authentication method |

The last row of the left column is the one teams get wrong. A new enum value is additive only if clients were told to
tolerate unknown values from the start. Say so in the documentation on day one, or treat it as breaking.

---

### Run at most two versions, and announce the end

- Keep a deprecated version running for at least six months after its successor ships.
- Never run more than two active versions. A third means the first should already be gone.
- Announce the retirement on the response itself, so a client that never reads the changelog still finds out.

```text
Deprecation: true
Sunset: Sat, 01 Jan 2026 00:00:00 GMT
Link: <https://docs.example.com/migrate-v2>; rel="deprecation"
```

- Return 410 Gone after the sunset date, not 404. The distinction tells the caller the endpoint was removed on purpose.

---

### Instrument before you retire

Count requests per version, per client, before announcing a sunset date, and again the week before it. Retiring a
version you have not measured is how a partner integration breaks on a Saturday.

---

### Related skills

- `api-design` for the contract the version wraps.
- `database-migrations` when the breaking change reaches the stored shape as well as the wire shape.
- `deployment-patterns` for running two versions side by side during the overlap.
