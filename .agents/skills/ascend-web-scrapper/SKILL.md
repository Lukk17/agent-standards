---
name: ascend-web-scrapper
description: Scrape any web page or run a meta-search via the self-hosted AscendWebSearch service. Use this whenever the task involves fetching, reading, or extracting content from a URL — job listings, articles, product pages, docs, paywalled or Cloudflare-protected sites — or a web search the agent should run itself. Handles WAFs automatically and escalates CAPTCHAs / login walls to a remote browser the user can drive on their phone.
---

# Ascend Web Scrapper

Self-hosted scraping + meta-search. Runs a tiered cascade (fast HTTP → FlareSolverr → headed Playwright → remote NoVNC for human help) so most pages just work.

## Base URL

Use whatever base URL the user / runtime config provides for AscendWebSearch (env var, MCP config, etc.). It varies between environments — host vs container, local vs remote. If unknown, ask. Examples below use `$BASE` as a placeholder.

## Endpoints

There are exactly two, both for different jobs:

- `POST {BASE}/api/v2/web/read` — extract one page's content. Use POST/v2 because target URLs often contain `?` and `&` that the GET router would mangle.
- `GET  {BASE}/api/v1/web/search?query=…&limit=…` — SearXNG meta-search; returns a list of `{title, url, content}` results.

Typical workflow: `search` to find candidate URLs, then `read` each one.

## Always send `heavy_mode: true` and `include_links: true`

These are the defaults you should use on every `read` call. Never opt out without a specific reason.

- **`heavy_mode: true`** — skips the fast-but-shallow tier and goes straight to the rendering tier. The fast tier silently drops JS-heavy content (most modern job boards, SPAs, anything with lazy-loaded sections), and an agent has no good way to detect that it got a partial page. Paying the latency once is cheaper than realizing later that half the listing was missing.
- **`include_links: true`** — the response gains a `links` dict. Agents almost always need links for follow-up navigation (pagination, "view full job", related results). Asking for them upfront avoids a second round-trip and keeps the trail visible.

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

**Success** — has `status: "success"`, plus `content` (extracted text), `mode` (which tier won), and `links` (dict of anchor-text → URL when `include_links=true`).

**Error** — `status: "error"` with an `error` message; means every tier failed.

**Human intervention required** — `status: "human_intervention_required"`, with `intervention_type` (`"captcha"` or `"login"`), `vnc_url`, and a human-readable `message`. This is *not* an error — see below.

## Handling CAPTCHA / login walls

When you get `human_intervention_required`, the service has already opened a real headed browser session pointed at the target URL on a server it controls, and is monitoring it in the background. Your job:

1. Show `vnc_url` to the user as a clickable link with a short prompt — e.g. *"This page needs you to solve a CAPTCHA / log in. Open this link on any device and do it: `<vnc_url>`. Tell me when you're done, or I'll keep checking."* The URL already includes `?autoconnect=true`, so the user lands directly on the live browser without a VNC password.
2. The user solves the challenge (taps the checkbox, signs in, whatever). When they finish, the service captures the resulting cookies / clearance tokens and writes them to a shared Redis cache keyed by domain.
3. Re-call `/api/v2/web/read` with the same URL and same body. The cached session is matched automatically — no extra parameter needed — and the call returns `success`. Subsequent calls to *other pages on the same domain* also reuse that session until the cookies expire.

Since the service doesn't push a "done" signal, just poll: wait roughly 30 seconds, retry, repeat. Stop early if the user says they're finished and retry immediately. Cap retries (e.g., 5) so you don't loop forever if they walk away.

Treat `human_intervention_required` as expected on auth-walled or aggressively protected sites (LinkedIn, Indeed, paywalled news). Don't hammer `/read` in a tight loop while a human is mid-solve — that just wastes work and may invalidate the in-progress session.

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
