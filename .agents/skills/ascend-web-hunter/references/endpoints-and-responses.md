# Endpoints, Tiers and Responses

Contents:

- [Call only the six agent-facing endpoints](#call-only-the-six-agent-facing-endpoints)
- [Know the tiers behind a read](#know-the-tiers-behind-a-read)
- [Branch on the status or code field, not on the HTTP code alone](#branch-on-the-status-or-code-field-not-on-the-http-code-alone)

Companion reference for the [ascend-web-hunter](../SKILL.md) skill. ascend-web-hunter is the web reading service of [AscendAI](https://github.com/Lukk17/AscendAI). It lives in `apps/ascend-web-hunter`, runs as the service and the container `ascend-web-hunter`, listens on port 7021, and was formerly called AscendWebSearch. Load this file to choose an endpoint, to understand which tier answered a read, or to route a response by its `status` or `code` field.

---

### Call only the six agent-facing endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/v1/web/search?query=…&limit=…` | GET | SearXNG meta-search, returns a list of `{title, url, content}` results. |
| `/api/v2/web/read` | POST | Extract one page. POST avoids a GET router mangling `?` and `&` inside the target URL. |
| `/api/v2/web/session/establish` | POST | Open a real browser session for a URL and hand the user a link to sign in. |
| `/api/v2/web/session/status` | POST | Check whether a stored session for a URL is still active. |
| `/api/v2/web/session/clear` | POST | Delete a stored session and any cached reads for that domain. |
| `/api/v2/session/interventions/{flow_id}` | DELETE | Close one open NoVNC window the user gave up on, saving nothing from it. |

The other endpoints stay out of an agent's reach, apart from the `/health` probe above. `GET /health`, `GET /ready`
and `GET /metrics` serve orchestration and monitoring. `POST /api/v1/blocklist/refresh` and
`GET /api/v1/blocklist/status` maintain the server's blocklist, which is an operator action. This skill does not
cover the crawl jobs (`POST /api/v1/crawl/jobs`, `GET /api/v1/crawl/jobs`, `GET /api/v1/crawl/jobs/{job_id}` and
`DELETE /api/v1/crawl/jobs/{job_id}`), `POST /api/v2/web/session/import`, which stores a browser storage state
captured outside the service, or `GET /api/v2/session/interventions`, which lists the open NoVNC windows. The same
process also serves MCP at `/mcp`, with the tools `web_search`, `web_read`, `session_establish`, `session_status`,
`session_clear` and `session_cancel_intervention` behind the same code, plus `session_interventions`, `crawl_submit`, `crawl_job_status`,
`crawl_list_jobs` and `crawl_cancel_job`, for a runtime that has the service configured as an MCP server.

Pass: call `/api/v2/web/read` to get page text.

Fail: call `/api/v1/blocklist/refresh` because a page looked full of ads.

---

### Know the tiers behind a read

Each tier name is also the `mode` value a successful read returns.

| Tier | What it does |
| --- | --- |
| `1-beautifulsoup` | Plain HTTP with a browser fingerprint, parsed with BeautifulSoup. |
| `2-trafilatura` | The same fetch, with the main text pulled out by Trafilatura. |
| `4-playwright_stealth` | A headed Chromium driven by Playwright with stealth settings. |
| `4a-patchright` | A patched Chromium build driven by Patchright. |
| `4b-camoufox` | Camoufox, a Firefox-family browser with its own fingerprint, skipped when the operator sets `CAMOUFOX_ENABLED=false`. |
| `5-crawlee_adaptive` | The adaptive crawler of Crawlee. |
| `6-novnc` | A browser a human drives over NoVNC, answered with the 428 case below. |

A read without `heavy_mode` starts at tier 1, or at the tier that last succeeded for the same domain, which the
service remembers for `TIER_MEMORY_TTL_SECONDS` (one day by default). A read with `heavy_mode: true`, or for a domain
with a stored session, starts at `4-playwright_stealth`. A URL that matches a known login redirect goes straight to
`6-novnc`. The request also takes a `tier` field that starts the chain at a named tier. Leave it out and let
`heavy_mode` decide. A name outside the table, such as the removed `3-flaresolverr`, is refused with HTTP 400 and code
`validation` before any tier runs, and `4b-camoufox` while the operator switched it off is refused with HTTP 409 and
code `tier_disabled`.

Every request a browser tier makes, the page and each frame and resource on it, passes the same fetch guard as the
plain HTTP tiers and goes through the same pinned fetch, so a page or a redirect hop on a private address is refused
with HTTP 400 and code `unsafe_uri` and the cascade stops there. The page's WebSockets are closed, so content a page
only loads over a WebSocket, such as a live chat or a live price feed, is missing from the read.

Pass: send `heavy_mode: true` and read `mode` only to report which tier answered.

Fail: send `"tier": "3-flaresolverr"`, which is refused with HTTP 400, or branch on a `mode` value.

---

### Branch on the status or code field, not on the HTTP code alone

| Case | HTTP | Key fields |
| --- | --- | --- |
| Success | 200 | `status: "success"`, `content`, `mode` (the winning tier, for example `"4-playwright_stealth"`), plus `links` when requested. |
| Error | 200 | `status: "error"`, `error`, `reason` (`"all_tiers_failed"` or `"budget_exhausted"`). |
| Human needed | 428 | `code: "human_intervention_required"`, `detail`, `intervention_type` (`"captcha"` or `"login"`), `vnc_url`, `flow_id`, `joined`, `window`. |
| Session expired | 200 | `status: "session_expired"`, empty `content`, `profile`, `message`. |
| NoVNC busy | 409 | `code: "novnc_busy"`, `detail`, `holder_url`, `holder_profile`, `active_flows`, `max_concurrent_flows`, `flows`, and a `Retry-After` header, 30 seconds by default. |
| Refused | 400 | `code`, such as `validation` for a bad field or an unknown tier, or `unsafe_uri` when the fetch guard refuses the URL, and `detail`. |
| Window closed | 204 | No body, from `DELETE /api/v2/session/interventions/{flow_id}`. |
| No such window | 404 | `code: "flow_not_found"`, from the same call when no open window has that `flow_id`, because it already ended or never existed. |

Link markers are woven into `content` as numbers, so `"View job [3]"` pairs with `{"3": "https://…"}` in `links`.
The markers restart at 1 on every response and are not stable across calls. The 428, 409, 404 and 400 answers are RFC 7807
problem bodies (`application/problem+json`) whose `status` holds the HTTP code as a number, so route them on `code`.
Over MCP, `web_read` returns the 428 and 409 cases as successful tool results carrying
`status: "human_intervention_required"` or `status: "novnc_busy"` and a `message`, and a refusal is a tool error whose
text starts with its code, such as `validation: `. `session_cancel_intervention` answers
`{"status": "cancelled", "flow_id": "…"}`, or a tool error starting `flow_not_found: `. The 428 case is not a failure, so a
client that calls `raise_for_status()` or checks `response.ok` has to unwrap it before treating the request as
broken. The session expired case means a stored login for the domain and profile no longer works, and the service
refuses to read the page anonymously, so run `session/establish` for it and read again. The 409 case means every
NoVNC window of the container is in use, `NOVNC_MAX_CONCURRENT_FLOWS` of them (four by default), so wait the seconds
in `Retry-After` and retry.

Pass: read `status` out of a 200 body and `code` out of a 428 body, and route the 428 case into the human-intervention
flow.

Fail: call `raise_for_status()` and report the page as unreadable.
