---
name: ascend-web-hunter
description: Page-content extraction through the self-hosted AscendWebSearch service for pages a normal fetch cannot read, covering WAF bypass, CAPTCHA escalation to a remote browser, and cached login sessions. Use when the user says "this page is behind Cloudflare", "the fetch got a bot check", "scrape this job listing that blocks bots", "this site needs a login", or "log me in to that site so you can read it". Not for general research or a web search a normal fetch can answer, use `research`, and not for recalling facts the user told you in an earlier conversation, use `ascend-memory`.
compatibility: Requires the self-hosted AscendWebSearch service reachable over HTTP. The base URL comes from ASCEND_WEB_HUNTER_URL, else the first of http://ascend-web-hunter.internal and http://localhost:7021 whose /health answers, and appears in the examples as $BASE.
---

# Ascend Web Hunter

Pull page content through AscendWebSearch, which cascades from fast HTTP to FlareSolverr to a headed Playwright
browser to a remote NoVNC session a human can drive. Use it for any page a plain fetch cannot read, and for login
walls the user signs into once so the service can cache the session. General web search and every page a normal fetch
returns in full belong to `research`, which hands a blocked page to this skill.

---

### When to activate

- A plain fetch already returned a Cloudflare interstitial, a WAF challenge, a CAPTCHA, or a bot check.
- The target page is known to block normal fetching, such as a job board or a shop that rejects automated clients.
- The target page sits behind a login the user can complete once on a phone or a laptop.

---

### When not to activate

- General research, a web search, or reading a page a normal fetch returns in full, use `research`.
- Recalling something the user told you in an earlier conversation, use `ascend-memory`.
- Turning a recording or a video into text, use `audio-scribe`.
- Writing or polishing the markdown you produce from a fetched page, use `markdown-writer`.

---

### Resolve the base URL in a fixed order

1. Use the environment variable `ASCEND_WEB_HUNTER_URL` when it is set.
2. Otherwise probe `http://ascend-web-hunter.internal`, then `http://localhost:7021`, and use the first whose
   `/health` endpoint answers.
3. When none answers, tell the user the service is down. Do not fall back to a normal web fetch without saying so.

The local compose file publishes port 7021 and exposes `/health` and `/ready` there. Use the resolved value as
`$BASE` in every call. The probe commands are in [references/base-url.md](references/base-url.md).

Pass: `ASCEND_WEB_HUNTER_URL` is unset, the `.internal` probe times out, `localhost:7021/health` answers, use that.

Fail: every probe fails, and the page is read with the built-in web fetch as if nothing happened.

---

### Call only the five agent-facing endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/v1/web/search?query=…&limit=…` | GET | SearXNG meta-search, returns a list of `{title, url, content}` results. |
| `/api/v2/web/read` | POST | Extract one page. POST avoids a GET router mangling `?` and `&` inside the target URL. |
| `/api/v2/web/session/establish` | POST | Open a real browser session for a URL and hand the user a link to sign in. |
| `/api/v2/web/session/status` | POST | Check whether a stored session for a URL is still active. |
| `/api/v2/web/session/clear` | POST | Delete a stored session and any cached reads for that domain. |

Four other endpoints exist and stay out of an agent's reach, apart from the `/health` probe above. `GET /health`
and `GET /ready` serve orchestration.
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

---

### Related skills

- `research` for general research, web search, and every page a normal fetch can read.
- `ascend-memory` for facts about the user that must survive across conversations.
- `audio-scribe` for turning an audio or video recording into text.
- `markdown-writer` for shaping fetched content into a human-facing document.

---

### Checklist

- Base URL taken from `ASCEND_WEB_HUNTER_URL`, else the first candidate whose `/health` answers, else reported down.
- `heavy_mode` and `include_links` set on every `read`.
- Response routed on its `status` field, with 428 and 409 handled as their own cases.
- CAPTCHA and login walls handed to the user with `vnc_url`, then polled with a capped retry.
- `session/establish` used only for a login wall you already know about.
- Search run before read whenever the URL on a blocking site was not given to you, open-ended search left to `research`.
