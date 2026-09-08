---
name: ascend-web-hunter
description: Web search and page-content extraction through the self-hosted AscendWebSearch service, covering WAF bypass, CAPTCHA escalation to a remote browser, and cached login sessions. Use when the user says "search the web for X", "read this URL", "scrape this job listing", "this page is behind Cloudflare", or "log me in to that site so you can read it". Not for recalling facts the user told you in an earlier conversation, use `ascend-memory`.
compatibility: Requires the self-hosted AscendWebSearch service reachable over HTTP. Its base URL is configured by the user and appears in the examples as the placeholder $BASE, for example `http://ascend-web-hunter.local:8080`. No default base URL is assumed.
---

# Ascend Web Hunter

Search the web and pull page content through AscendWebSearch, which cascades from fast HTTP to FlareSolverr to a
headed Playwright browser to a remote NoVNC session a human can drive. Use it for any page a plain fetch cannot
read, and for login walls the user signs into once so the service can cache the session.

---

### When to activate

- The task needs a web search the agent runs itself rather than an answer from memory.
- The task needs the text of a specific URL: a job listing, an article, a product page, a documentation page.
- A plain fetch already returned a Cloudflare interstitial, a WAF challenge, or a bot check.
- The target page sits behind a login the user can complete once on a phone or a laptop.

---

### When not to activate

- Recalling something the user told you in an earlier conversation, use `ascend-memory`.
- Turning a recording or a video into text, use `audio-scribe`.
- Writing or polishing the markdown you produce from a fetched page, use `markdown-writer`.

---

### Take the base URL from configuration, never from a guess

Read the base URL from whatever configuration surface the runtime provides for AscendWebSearch, such as an MCP
server URL, an environment variable, or a settings file. The service can live anywhere: a container name on the same
Docker network, a host and port pair, a hostname on a local network, or a public HTTPS address behind a reverse
proxy. Ask the user when nothing is configured. A wrong default looks like a working configuration right up until
the first request fails. A configured value might look like `http://ascend-web-hunter.local:8080`, shown here only
as an example of the shape, with the real value always coming from the user's own configuration.

Pass: resolve the base URL from configuration, then use it as `$BASE` in every call.

Fail: assume a default such as a well-known local port and start firing requests at it.

---

### Call only the five agent-facing endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/v1/web/search?query=…&limit=…` | GET | SearXNG meta-search, returns a list of `{title, url, content}` results. |
| `/api/v2/web/read` | POST | Extract one page. POST avoids a GET router mangling `?` and `&` inside the target URL. |
| `/api/v2/web/session/establish` | POST | Open a real browser session for a URL and hand the user a link to sign in. |
| `/api/v2/web/session/status` | POST | Check whether a stored session for a URL is still active. |
| `/api/v2/web/session/clear` | POST | Delete a stored session and any cached reads for that domain. |

Four other endpoints exist and stay out of an agent's reach. `GET /health` and `GET /ready` serve orchestration.
`POST /api/v1/blocklist/refresh` and `GET /api/v1/blocklist/status` maintain the server's blocklist, which is an
operator action.

Pass: call `/api/v2/web/read` to get page text.

Fail: call `/api/v1/blocklist/refresh` because a page looked full of ads.

---

### Send heavy_mode and include_links on every read

Set `heavy_mode: true` so the call skips the fast-but-shallow tier and renders the page. The fast tier drops
JavaScript-rendered content such as most modern job boards, single-page apps, and lazy-loaded sections, and an agent
cannot tell a partial page from a complete one. Set `include_links: true` so the response carries a `links` map for
follow-up navigation, which saves a second round trip. Narrow the result with `link_filter: "<substring>"` when only
a subset matters, for example `"jobs/view"` on a job board.

Pass: send `{"url": "…", "heavy_mode": true, "include_links": true}`.

Fail: send `{"url": "…"}` and treat the shallow tier's partial text as the whole page.

Bash:

```bash
curl -s --max-time 90 $BASE/api/v2/web/read -X POST -H "Content-Type: application/json" -d '{"url":"https://example.com/jobs/view/123","heavy_mode":true,"include_links":true}'
```

PowerShell:

```powershell
curl.exe -s --max-time 90 $BASE/api/v2/web/read -X POST -H "Content-Type: application/json" -d '{\"url\":\"https://example.com/jobs/view/123\",\"heavy_mode\":true,\"include_links\":true}'
```

Call `curl.exe` in PowerShell so the shell does not route the name to its `Invoke-WebRequest` alias, and escape the
inner double quotes of the JSON body. Give the client a generous timeout of around 90 seconds, because a cold
Cloudflare domain takes a while on the first hit while FlareSolverr warms up.

---

### Branch on the status field, not on the HTTP code alone

| Case | HTTP | Key fields |
| --- | --- | --- |
| Success | 200 | `status: "success"`, `content`, `mode` (the winning tier, for example `"3-flaresolverr"`), plus `links` when requested. |
| Error | 200 | `status: "error"`, `error`, `reason` (`"all_tiers_failed"` or `"budget_exhausted"`). |
| Human needed | 428 | `status: "human_intervention_required"`, `intervention_type` (`"captcha"` or `"login"`), `vnc_url`, `message`. |
| NoVNC busy | 409 | `status: "novnc_busy"`, `holder_url`, `holder_profile`, `message`. |

Link markers are woven into `content` as numbers, so `"View job [3]"` pairs with `{"3": "https://…"}` in `links`.
The markers restart at 1 on every response and are not stable across calls. The 428 case is not a failure, so a
client that calls `raise_for_status()` or checks `response.ok` has to unwrap it before treating the request as
broken. The 409 case means the shared browser is already held for someone else, so wait and retry.

Pass: read `status` out of the body and route the 428 case into the human-intervention flow.

Fail: call `raise_for_status()` and report the page as unreadable.

---

### Hand a CAPTCHA or a login wall back to the user

On a 428 the service has already opened a headed browser on a machine it controls, pointed it at the target URL, and
started monitoring it. Show `vnc_url` as a clickable link with a short prompt, for example: this page needs a CAPTCHA
solved or a sign-in, open the link on any device and finish it, then tell me. The URL already carries
`?autoconnect=true`, so the user lands on the live browser with no VNC password. Once they finish, the service
captures the cookies and clearance tokens into a shared Redis cache keyed by domain. Re-call `/api/v2/web/read` with
the same URL and the same body, and the cached session is matched with no extra parameter. Other pages on the same
domain reuse it until the cookies expire.

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

### Search first, then read

Use `search` to discover candidate URLs, then pass each promising one to `read`. Going straight to `read` on a URL
you guessed wastes the whole cascade budget on a 404.

Pass: search for the topic, pick the three most relevant results, read each one.

Fail: invent a likely-looking URL and read it.

Bash:

```bash
curl -s "$BASE/api/v1/web/search?query=ascend%20ai&limit=5"
```

PowerShell:

```powershell
curl.exe -s "$BASE/api/v1/web/search?query=ascend%20ai&limit=5"
```

---

### Related skills

- `ascend-memory` for facts about the user that must survive across conversations.
- `audio-scribe` for turning an audio or video recording into text.
- `markdown-writer` for shaping fetched content into a human-facing document.

---

### Checklist

- Base URL resolved from configuration, not from a default.
- `heavy_mode` and `include_links` set on every `read`.
- Response routed on its `status` field, with 428 and 409 handled as their own cases.
- CAPTCHA and login walls handed to the user with `vnc_url`, then polled with a capped retry.
- `session/establish` used only for a login wall you already know about.
- Search run before read whenever the URL was not given to you.
