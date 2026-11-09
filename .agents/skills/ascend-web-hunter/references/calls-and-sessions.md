# Calls and Sessions

Contents:

- [Send heavy_mode and include_links on every read](#send-heavy_mode-and-include_links-on-every-read)
- [Hand a CAPTCHA or a login wall back to the user](#hand-a-captcha-or-a-login-wall-back-to-the-user)
- [Establish a session ahead of a known login wall](#establish-a-session-ahead-of-a-known-login-wall)
- [Search a blocking site first, then read](#search-a-blocking-site-first-then-read)

Companion reference for the [ascend-web-hunter](../SKILL.md) skill. Load it for the exact Bash and PowerShell commands for a read, a session and a search, and for the CAPTCHA and login hand-off to the user.

---

### Send heavy_mode and include_links on every read

Set `heavy_mode: true` so the call skips the two plain HTTP tiers and starts at `4-playwright_stealth`. Those tiers
drop JavaScript-rendered content such as most modern job boards, single-page apps, and lazy-loaded sections, and an
agent cannot tell a partial page from a complete one. Set `include_links: true` so the response carries a `links` map for
follow-up navigation, which saves a second round trip. Narrow the result with `link_filter: "<substring>"` when only
a subset matters, for example `"jobs/view"` on a job board. The service caches a read for five minutes by default,
keyed by the URL and every option, `link_filter` included. A repeat with the same body is answered from the cache, and
a repeat with another `link_filter` runs the whole cascade again, so pick the filter on the first read.

Pass: send `{"url": "…", "heavy_mode": true, "include_links": true}`.

Fail: send `{"url": "…"}` and treat the shallow tier's partial text as the whole page.

Bash:

```bash
curl -s --max-time 150 $BASE/api/v2/web/read -X POST -H "Content-Type: application/json" -d '{"url":"https://example.com/jobs/view/123","heavy_mode":true,"include_links":true}'
```

PowerShell:

```powershell
curl.exe -s --max-time 150 $BASE/api/v2/web/read -X POST -H "Content-Type: application/json" -d '{\"url\":\"https://example.com/jobs/view/123\",\"heavy_mode\":true,\"include_links\":true}'
```

Call `curl.exe` in PowerShell so the shell does not route the name to its `Invoke-WebRequest` alias, and escape the
inner double quotes of the JSON body. Give the client a timeout of about 150 seconds. The service checks its
90-second read budget only before it starts each tier, so a tier that starts late runs past it, and the Crawlee tier
alone may take 60 seconds.

---

### Hand a CAPTCHA or a login wall back to the user

On a 428 the service has already opened a headed browser on a machine it controls, pointed it at the target URL, and
started monitoring it. Show `vnc_url` as a clickable link with a short prompt, for example: this page needs a CAPTCHA
solved or a sign-in, open the link on any device and finish it, then tell me. The URL already carries
`?autoconnect=true`, so the user lands on the live browser at once. NoVNC asks for a password only when the
operator set `VNC_PASSWORD`. Once they finish, the service captures the cookies and clearance tokens into a shared
Redis cache keyed by domain and profile. Re-call `/api/v2/web/read` with the same URL and the same body, and the cached
session is matched with no extra parameter. Other pages on the same domain reuse it until the cookies expire. A retry
while the window is still open joins the same flow and answers the same 428 with `joined: true`, so it opens no second
window.

The service pushes no completion signal, so poll: wait around 30 seconds, retry, repeat, and stop early when the
user says they are done. Cap the retries at about five so the loop ends when the user walks away.

Keep the `flow_id` of the 428 body. When the user says they will not solve it, or the window was opened for the wrong
page, close it so the slot is free at once for the next read. Nothing the window holds is saved. The call answers
HTTP 204, or HTTP 404 with code `flow_not_found` when the window already ended, which needs no further action.

Bash:

```bash
curl -s -X DELETE $BASE/api/v2/session/interventions/$FLOW_ID
```

PowerShell:

```powershell
curl.exe -s -X DELETE $BASE/api/v2/session/interventions/$FLOW_ID
```

Pass: show `vnc_url`, wait, retry `/read` on a 30-second cadence, stop after five attempts.

Fail: retry `/read` in a tight loop while the user is mid-solve, which wastes work and can invalidate the session.

---

### Establish a session ahead of a known login wall

A `read` call only discovers a login wall after burning through the faster tiers and the roughly 90-second cascade
budget, unless the URL matches a known login redirect. It tells a login from a CAPTCHA by a login redirect, a sign-in
page title, or a blocked page whose main form holds a password field, so a login page that shows none of them is
reported as a CAPTCHA or read as content. When the user tells you a site needs a sign-in, or the target is
a private dashboard, call `session/establish` first and turn a guaranteed failed round trip into one call.

Pass: call `session/establish` for a dashboard the user says needs a login.

Fail: call `session/establish` speculatively while a `vnc_url` you already showed is still awaiting a solve.

Bash:

```bash
curl -s -X POST $BASE/api/v2/web/session/establish -H "Content-Type: application/json" -d '{"url":"https://app.example.com/dashboard"}'
```

PowerShell:

```powershell
curl.exe -s -X POST $BASE/api/v2/web/session/establish -H "Content-Type: application/json" -d '{\"url\":\"https://app.example.com/dashboard\"}'
```

That returns HTTP 200 with
`{"status":"login_required","target":"…","intervention_type":"…","vnc_url":"…","flow_id":"…","joined":false,"window":{…}}`
and holds a real browser session for up to 10 minutes, or joins the open one for the same site and profile with
`joined: true`. When every NoVNC window is in use it answers HTTP 409 with code `novnc_busy`, as a read does. Show
`vnc_url` exactly as in the CAPTCHA flow, then re-call `read` once the user is done.

Check `session/status` before re-establishing when you are unsure whether a prior login still holds. Same body
shape, and it returns `{"url": "…", "status": "active" | "expired" | "none", "auth_ttl_remaining_seconds": …,
"last_validated": …, "profile": "…", "last_window": …}`. A saved login counts as `active` while it holds a cookie,
or a localStorage entry the site set on its own origin, so a site that keeps its login only in localStorage counts
too. Analytics and consent keys do not count, and the browser tiers restore both cookies and localStorage.

`last_window` says how the last NoVNC window for the site and profile ended, CAPTCHA or login, as
`{"flow_id": "…", "intervention_type": "captcha" | "login", "outcome": "…", "finished_at": …}`, with
`finished_at` in Unix seconds, or `null` when no window ended within the session lifetime (14 days by default). Read
it after the user says they are done, rather than guessing from one more read:

| `outcome` | Meaning | Next step |
| --- | --- | --- |
| `resolved` | The user solved the CAPTCHA or signed in, and the session was saved. | Read again. |
| `already_authenticated` | The stored login already worked, so the window closed and kept it. | Read again. |
| `timeout` | The window ran out of time with no clear result. | Ask the user before opening a new one. |
| `rejected` | The window ran out of time on a CAPTCHA while the page was still blocked. | Ask the user before opening a new one. |
| `browser_closed` | The browser of the window closed or crashed. | Ask the user before opening a new one. |
| `cancelled` | The window was closed through `DELETE /api/v2/session/interventions/{flow_id}`. | Nothing was saved. Open a new window only when the user asks. |

Bash:

```bash
curl -s -X POST $BASE/api/v2/web/session/status -H "Content-Type: application/json" -d '{"url":"https://app.example.com/dashboard"}'
```

PowerShell:

```powershell
curl.exe -s -X POST $BASE/api/v2/web/session/status -H "Content-Type: application/json" -d '{\"url\":\"https://app.example.com/dashboard\"}'
```

Clear a stale session with the same body shape against `session/clear`, for instance when the user says they logged
out or switched accounts. That call always returns HTTP 200 and
`{"status":"cleared","url":"…","existed": true | false,"cleared_cache_entries": …}`, whether or not a session
existed. All three session endpoints accept an optional `profile` field, such as `"work"` or `"personal"`, for sites
where the user keeps more than one identity. Omit it to use the server's default profile.

---

### Search a blocking site first, then read

Use `search` only to find candidate URLs on a site already known to block a normal fetch, then pass each promising
one to `read`. Going straight to `read` on a URL you guessed wastes the whole cascade budget on a 404. An open-ended
web search goes to `research`, not here.

Pass: search for the listing on the blocking site, pick the three most relevant results, read each one.

Fail: invent a likely-looking URL and read it.

Bash:

```bash
curl -s "$BASE/api/v1/web/search?query=ascend%20ai&limit=5"
```

PowerShell:

```powershell
curl.exe -s "$BASE/api/v1/web/search?query=ascend%20ai&limit=5"
```
