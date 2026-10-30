# Endpoints, Tiers and Responses

Contents:

- [Call only the five agent-facing endpoints](#call-only-the-five-agent-facing-endpoints)
- [Know the tiers behind a read](#know-the-tiers-behind-a-read)
- [Branch on the status field, not on the HTTP code alone](#branch-on-the-status-field-not-on-the-http-code-alone)

Companion reference for the [ascend-web-hunter](../SKILL.md) skill. ascend-web-hunter is the web reading service of [AscendAI](https://github.com/Lukk17/AscendAI). It lives in `apps/ascend-web-hunter`, runs as the service and the container `ascend-web-hunter`, listens on port 7021, and was formerly called AscendWebSearch. Load this file to choose an endpoint, to understand which tier answered a read, or to route a response by its `status` field.

---

### Call only the five agent-facing endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/v1/web/search?query=…&limit=…` | GET | SearXNG meta-search, returns a list of `{title, url, content}` results. |
| `/api/v2/web/read` | POST | Extract one page. POST avoids a GET router mangling `?` and `&` inside the target URL. |
| `/api/v2/web/session/establish` | POST | Open a real browser session for a URL and hand the user a link to sign in. |
| `/api/v2/web/session/status` | POST | Check whether a stored session for a URL is still active. |
| `/api/v2/web/session/clear` | POST | Delete a stored session and any cached reads for that domain. |

The other endpoints stay out of an agent's reach, apart from the `/health` probe above. `GET /health`, `GET /ready`
and `GET /metrics` serve orchestration and monitoring. `POST /api/v1/blocklist/refresh` and
`GET /api/v1/blocklist/status` maintain the server's blocklist, which is an operator action. The same process also
serves MCP at `/mcp`, with the tools `web_search`, `web_read`, `session_establish`, `session_status` and
`session_clear` behind the same code, for a runtime that has the service configured as an MCP server.

Pass: call `/api/v2/web/read` to get page text.

Fail: call `/api/v1/blocklist/refresh` because a page looked full of ads.

---

### Know the tiers behind a read

The tiers on the AscendAI `master` branch, which is what a user gets from GitHub. Each tier name is also the `mode` value a successful read returns.

| Tier | What it does |
| --- | --- |
| `1-beautifulsoup` | Plain HTTP with a browser fingerprint, parsed with BeautifulSoup. |
| `2-trafilatura` | The same fetch, with the main text pulled out by Trafilatura. |
| `3-flaresolverr` | A FlareSolverr container solves a Cloudflare challenge. |
| `4-playwright_stealth` | A headed Chromium driven by Playwright with stealth settings. |
| `5-crawlee_adaptive` | The adaptive crawler of Crawlee. |
| `6-novnc` | A browser a human drives over NoVNC, answered with the 428 case below. |

A read without `heavy_mode` starts at tier 1. A read with `heavy_mode: true` starts at tier 4, so FlareSolverr never
runs for it. The request also takes a `tier` field that starts the chain at a named tier. Leave it out and let
`heavy_mode` decide, because the tier names are changing.

Coming change: the AscendAI branch `feature/all-openspec-groups` removes the `3-flaresolverr` tier with its settings and its container, and adds the browser tiers `4a-patchright` and `4b-camoufox` after `4-playwright_stealth`. Once that reaches `master`, a request that names `3-flaresolverr` is refused with HTTP 400 and no tier runs. Read the `mode` values the service returns rather than this table when the two disagree.

Pass: send `heavy_mode: true` and read `mode` only to report which tier answered.

Fail: send `"tier": "3-flaresolverr"`, or branch on `mode` being `"3-flaresolverr"`.

---

### Branch on the status field, not on the HTTP code alone

| Case | HTTP | Key fields |
| --- | --- | --- |
| Success | 200 | `status: "success"`, `content`, `mode` (the winning tier, for example `"4-playwright_stealth"`), plus `links` when requested. |
| Error | 200 | `status: "error"`, `error`, `reason` (`"all_tiers_failed"` or `"budget_exhausted"`). |
| Human needed | 428 | `status: "human_intervention_required"`, `intervention_type` (`"captcha"` or `"login"`), `vnc_url`, `message`. |
| Session expired | 200 | `status: "session_expired"`, empty `content`, `profile`, `message`. |
| NoVNC busy | 409 | `status: "novnc_busy"`, `holder_url`, `holder_profile`, `message`, and a `Retry-After: 30` header. |

Link markers are woven into `content` as numbers, so `"View job [3]"` pairs with `{"3": "https://…"}` in `links`.
The markers restart at 1 on every response and are not stable across calls. The 428 case is not a failure, so a
client that calls `raise_for_status()` or checks `response.ok` has to unwrap it before treating the request as
broken. The session expired case means a stored login for the domain and profile no longer works, and the service
refuses to read the page anonymously, so run `session/establish` for it and read again. The 409 case means the shared
browser is already held for someone else, so wait the seconds in `Retry-After` and retry.

Pass: read `status` out of the body and route the 428 case into the human-intervention flow.

Fail: call `raise_for_status()` and report the page as unreadable.
