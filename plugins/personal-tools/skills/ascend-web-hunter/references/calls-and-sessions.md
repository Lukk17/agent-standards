# Calls and Sessions

Contents:

- [Send heavy_mode and include_links on every read](#send-heavy_mode-and-include_links-on-every-read)
- [Hand a CAPTCHA or a login wall back to the user](#hand-a-captcha-or-a-login-wall-back-to-the-user)
- [Establish a session ahead of a known login wall](#establish-a-session-ahead-of-a-known-login-wall)
- [Search a blocking site first, then read](#search-a-blocking-site-first-then-read)

Companion reference for the [ascend-web-hunter](../SKILL.md) skill. Load it for the exact Bash and PowerShell commands for a read, a session and a search, and for the CAPTCHA and login hand-off to the user.

---

### Send heavy_mode and include_links on every read

Set `heavy_mode: true` so the call skips tiers 1 to 3 and renders the page in a browser. The two plain HTTP tiers
drop JavaScript-rendered content such as most modern job boards, single-page apps, and lazy-loaded sections, and an
agent cannot tell a partial page from a complete one. Set `include_links: true` so the response carries a `links` map for
follow-up navigation, which saves a second round trip. Narrow the result with `link_filter: "<substring>"` when only
a subset matters, for example `"jobs/view"` on a job board.

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
Redis cache keyed by domain. Re-call `/api/v2/web/read` with the same URL and the same body, and the cached session is
matched with no extra parameter. Other pages on the same domain reuse it until the cookies expire.

The service pushes no completion signal, so poll: wait around 30 seconds, retry, repeat, and stop early when the
user says they are done. Cap the retries at about five so the loop ends when the user walks away.

Pass: show `vnc_url`, wait, retry `/read` on a 30-second cadence, stop after five attempts.

Fail: retry `/read` in a tight loop while the user is mid-solve, which wastes work and can invalidate the session.

---

### Establish a session ahead of a known login wall

A `read` call only discovers a login wall after burning through the faster tiers and the roughly 90-second cascade
budget, and it then guesses login versus CAPTCHA from a known redirect pattern rather than a general detector, so a
login form served without a redirect slips past it. When the user tells you a site needs a sign-in, or the target is
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

That returns HTTP 200 with `{"status":"login_required","target":"…","vnc_url":"…"}` and holds a real browser session
for up to 10 minutes. Show `vnc_url` exactly as in the CAPTCHA flow, then re-call `read` once the user is done.

Check `session/status` before re-establishing when you are unsure whether a prior login still holds. Same body
shape, and it returns `{"url": "…", "status": "active" | "expired" | "none", "auth_ttl_remaining_seconds": …,
"last_validated": …, "profile": "…"}`.

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
