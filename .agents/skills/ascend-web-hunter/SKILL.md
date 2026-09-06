---
name: ascend-web-hunter
description: Search the web and scrape/extract page content via the self-hosted AscendWebSearch service. Use this whenever the task involves running a web search the agent should perform itself, or fetching, reading, or extracting content from a URL — job listings, articles, product pages, docs, paywalled or Cloudflare-protected sites. Handles WAFs automatically and escalates CAPTCHAs / login walls to a remote browser the user can drive on their phone.
---

# Ascend Web Hunter

Self-hosted meta-search plus a tiered scraping cascade (fast HTTP → FlareSolverr → headed Playwright → remote NoVNC for human help), so most pages just work, and a session layer for getting past login walls proactively.

## Base URL

The service can live anywhere: a container name on the same Docker network, a `host:port` pair, a hostname on a local network, or a public HTTPS address behind a reverse proxy. There is no default here on purpose — a default that's wrong for the current environment looks like a working configuration right up until the first request fails. Take the base URL from whatever configuration surface the runtime provides for AscendWebSearch (an MCP server URL, an env var, a settings file) and ask the user if none is configured. Examples below use `$BASE` as a placeholder.

## Endpoints

Five endpoints matter to an agent, all under one base:

- `GET  {BASE}/api/v1/web/search?query=…&limit=…` — SearXNG meta-search; returns a list of `{title, url, content}` results.
- `POST {BASE}/api/v2/web/read` — extract one page's content. Use POST/v2 because target URLs often contain `?` and `&` that a GET router would mangle.
- `POST {BASE}/api/v2/web/session/establish` — proactively open a real browser session for a URL and hand the human a link to log in ahead of a read. See "Sessions" below.
- `POST {BASE}/api/v2/web/session/status` — check whether a stored session for a URL is still active.
- `POST {BASE}/api/v2/web/session/clear` — delete a stored session (and any cached reads for that domain).

Four more endpoints exist on the service and are deliberately left out of this list: `GET /health` and `GET /ready` are for orchestration, not for an agent; `POST /api/v1/blocklist/refresh` and `GET /api/v1/blocklist/status` maintain the server's ad/annoyance blocklist and are an operator action, not something a calling agent should trigger.

Typical workflow: `search` to find candidate URLs, then `read` each one. Reach for the session endpoints only when a site needs a login rather than a one-off CAPTCHA.

## Always send `heavy_mode: true` and `include_links: true`

These are the defaults you should use on every `read` call. Never opt out without a specific reason.

- **`heavy_mode: true`** — skips the fast-but-shallow tier and goes straight to the rendering tier. The fast tier silently drops JS-heavy content (most modern job boards, SPAs, anything with lazy-loaded sections), and an agent has no good way to detect that it got a partial page. Paying the latency once is cheaper than realizing later that half the listing was missing.
- **`include_links: true`** — the response gains a `links` map keyed by the numeric markers inserted into `content` (see "Response shapes" below). Agents almost always need links for follow-up navigation (pagination, "view full job", related results). Asking for them upfront avoids a second round-trip and keeps the trail visible.

Add `link_filter: "<substring>"` to narrow the returned links if you only care about a subset (e.g., `"jobs/view"` on LinkedIn).

## Example

Bash / Linux / macOS:

```bash
curl -s --max-time 90 $BASE/api/v2/web/read \
  -X POST -H "Content-Type: application/json" \
  -d '{"url":"https://www.linkedin.com/jobs/view/123","heavy_mode":true,"include_links":true}'
```

PowerShell (Windows):

```powershell
curl.exe -s --max-time 90 $BASE/api/v2/web/read `
  -X POST -H "Content-Type: application/json" `
  -d '{\"url\":\"https://www.linkedin.com/jobs/view/123\",\"heavy_mode\":true,\"include_links\":true}'
```

Note for PowerShell: line continuation is the backtick `` ` ``, not `\`. Use `curl.exe` so PowerShell doesn't route to its `Invoke-WebRequest` alias, and escape inner double quotes in the JSON body. Set the client timeout generously (~90s) — cold Cloudflare domains take a while on the first hit while FlareSolverr warms up.

## Response shapes

**Success** (HTTP 200) — has `status: "success"`, plus `content` (extracted text) and `mode` (which strategy tier won, e.g. `"3-flaresolverr"`). When `include_links=true`, the response also carries `links`, a map from the numeric marker woven into `content` to its absolute URL, e.g. `content` contains `"View job [3]"` and `links` contains `{"3": "https://…"}`. The markers restart from 1 on every response; they are not stable identifiers across calls.

**Error** (HTTP 200) — `status: "error"`, `error` (a message), and `reason` (`"all_tiers_failed"`, or `"budget_exhausted"` if the roughly 90-second wall-clock cascade budget ran out first). Both mean the page could not be read.

**Human intervention required** (HTTP 428 Precondition Required) — `status: "human_intervention_required"`, with `intervention_type` (`"captcha"` or `"login"`), `vnc_url`, and a human-readable `message`. This is *not* an error — see below — but it does arrive as a real 428: `curl` and most HTTP clients still hand you the body, but a client that calls something like `raise_for_status()` or only checks `response.ok` needs to unwrap this case explicitly rather than treating it as a failed request.

**NoVNC busy** (HTTP 409 Conflict) — `status: "novnc_busy"`, `holder_url`, `holder_profile`, `message`. Only one human intervention session, whether a manual `session/establish` call or an automatic escalation from `read`, can run at a time; the server is already holding the shared browser/display for someone else. Wait and retry rather than hammering it.

## Handling CAPTCHA / login walls

When you get `human_intervention_required` (HTTP 428), the service has already opened a real headed browser session pointed at the target URL on a server it controls, and is monitoring it in the background. Your job:

1. Show `vnc_url` to the user as a clickable link with a short prompt — e.g. *"This page needs you to solve a CAPTCHA / log in. Open this link on any device and do it: `<vnc_url>`. Tell me when you're done, or I'll keep checking."* The URL already includes `?autoconnect=true`, so the user lands directly on the live browser without a VNC password.
2. The user solves the challenge (taps the checkbox, signs in, whatever). When they finish, the service captures the resulting cookies / clearance tokens and writes them to a shared Redis cache keyed by domain.
3. Re-call `/api/v2/web/read` with the same URL and same body. The cached session is matched automatically — no extra parameter needed — and the call returns `success`. Subsequent calls to *other pages on the same domain* also reuse that session until the cookies expire.

Since the service doesn't push a "done" signal, just poll: wait roughly 30 seconds, retry, repeat. Stop early if the user says they're finished and retry immediately. Cap retries (e.g., 5) so you don't loop forever if they walk away.

Treat `human_intervention_required` as expected on auth-walled or aggressively protected sites (LinkedIn, Indeed, paywalled news). Don't hammer `/read` in a tight loop while a human is mid-solve — that just wastes work and may invalidate the in-progress session.

## Sessions: establish ahead of time for login walls

`read` only discovers that a page needs a login after it has already burned through the faster tiers, and the roughly 90-second cascade budget, and finally lands on the NoVNC tier, where it guesses `login` versus `captcha` from the URL (a known-redirect-pattern heuristic, not a general-purpose detector — a login form served without a redirect won't trip it). For a site you already know requires a login — the user tells you, or it's a private dashboard or authenticated app — call `session/establish` directly instead of waiting for `read` to fail first. That turns a guaranteed one-round-trip failure followed by a second call into a single call.

```bash
curl -s -X POST $BASE/api/v2/web/session/establish \
  -H "Content-Type: application/json" \
  -d '{"url":"https://app.example.com/dashboard"}'
```

```powershell
curl.exe -s -X POST $BASE/api/v2/web/session/establish `
  -H "Content-Type: application/json" `
  -d '{\"url\":\"https://app.example.com/dashboard\"}'
```

This returns HTTP 200 with `{"status":"login_required","target":"…","vnc_url":"…"}` and, exactly like the CAPTCHA flow, opens a real browser session held for up to 10 minutes. Show `vnc_url` to the user the same way as above, then re-call `read` once they say they're done — the session is cached by domain and reused automatically.

Because only one such session can run at a time (see the 409 case above), don't call `establish` speculatively for pages you haven't confirmed need it, and don't call it again while a `vnc_url` you already showed the user is still awaiting a solve.

Check status before re-establishing if you're unsure whether a prior login is still good:

```bash
curl -s -X POST $BASE/api/v2/web/session/status \
  -H "Content-Type: application/json" \
  -d '{"url":"https://app.example.com/dashboard"}'
```

```powershell
curl.exe -s -X POST $BASE/api/v2/web/session/status `
  -H "Content-Type: application/json" `
  -d '{\"url\":\"https://app.example.com/dashboard\"}'
```

Returns `{"url": "…", "status": "active" | "expired" | "none", "auth_ttl_remaining_seconds": …, "last_validated": …, "profile": "…"}`. Clear a stale session — for example when the user says they logged out or switched accounts — with the same request body shape against `session/clear`. That call always returns HTTP 200 and `{"status":"cleared","url":"…","existed": true | false,"cleared_cache_entries": …}`, whether or not a session existed.

All three session endpoints take an optional `profile` field (e.g. `"work"`, `"personal"`) for sites where the same user keeps more than one logged-in identity; omit it to use the server's default profile.

## Search example

Bash:

```bash
curl -s "$BASE/api/v1/web/search?query=ascend%20ai&limit=5"
```

PowerShell:

```powershell
curl.exe -s "$BASE/api/v1/web/search?query=ascend%20ai&limit=5"
```

Use it to discover URLs first; pass each promising one to `/read`.
