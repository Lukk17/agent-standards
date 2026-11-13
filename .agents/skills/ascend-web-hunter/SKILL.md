---
name: ascend-web-hunter
description: 'Page-content extraction through the self-hosted ascend-web-hunter service for pages a normal fetch cannot read: WAF bypass, CAPTCHA escalation to a remote browser and cached login sessions. Use when the user says "this page is behind Cloudflare", "the fetch got a bot check" or "this site needs a login". Not for a search a normal fetch can answer, use `research`.'
compatibility: Requires the self-hosted ascend-web-hunter service of AscendAI (https://github.com/Lukk17/AscendAI) reachable over HTTP. The base URL comes from ASCEND_WEB_HUNTER_URL, else the first of http://ascend-web-hunter.internal and http://localhost:7021 whose /health answers, and appears in the examples as $BASE.
metadata:
  version: "1.0.0"
---

# Ascend Web Hunter

Pull page content through ascend-web-hunter, the web reading service of [AscendAI](https://github.com/Lukk17/AscendAI), listening on port 7021. A read cascades from fast HTTP through headed and patched browsers to a remote NoVNC session a human can drive. Use it for any page a plain fetch cannot read, and for login walls the user signs into once so the service can cache the session. General web search and every page a normal fetch returns in full belong to `research`, which hands a blocked page to this skill.

| Task | Open |
| --- | --- |
| Probing the candidate base URLs before the first call | [references/base-url.md](references/base-url.md) |
| The six endpoints, the tier table, and the response cases with their fields | [references/endpoints-and-responses.md](references/endpoints-and-responses.md) |
| Exact Bash and PowerShell commands for read, session and search, and the CAPTCHA hand-off | [references/calls-and-sessions.md](references/calls-and-sessions.md) |

---

### When to activate

- A plain fetch already returned a Cloudflare interstitial, a WAF challenge, a CAPTCHA, or a bot check.
- The target page is known to block normal fetching, such as a job board or a shop that rejects automated clients.
- The target page sits behind a login the user can complete once on a phone or a laptop.
- The user says "scrape this job listing that blocks bots" or "log me in to that site so you can read it".

---

### When not to activate

- General research, a web search, or reading a page a normal fetch returns in full, use `research`.
- Recalling something the user told you in an earlier conversation, use `ascend-memory` if it is installed. It needs
  its own self-hosted service, so without it ask the user.
- Turning a recording or a video into text, use `audio-scribe` if it is installed. It needs its own self-hosted
  service, so without it tell the user that no transcription route is available.
- Writing or polishing the markdown you produce from a fetched page, use `markdown-writer`.

---

### Resolve the base URL in a fixed order

1. Use the environment variable `ASCEND_WEB_HUNTER_URL` when it is set.
2. Otherwise probe `http://ascend-web-hunter.internal`, then `http://localhost:7021`, and use the first whose
   `/health` endpoint answers.
3. When none answers, tell the user the service is down. Do not fall back to a normal web fetch without saying so.

The local compose file publishes port 7021 and exposes `/health` and `/ready` there. Use the resolved value as
`$BASE` in every call.

Pass: `ASCEND_WEB_HUNTER_URL` is unset, the `.internal` probe times out, `localhost:7021/health` answers, use that.

Fail: every probe fails, and the page is read with the built-in web fetch as if nothing happened.

---

### Rules

1. Call only the six agent-facing endpoints: `GET /api/v1/web/search`, `POST /api/v2/web/read`, `session/establish`, `session/status` and `session/clear`, and `DELETE /api/v2/session/interventions/{flow_id}`. Blocklist, metrics and readiness endpoints are operator actions, never an agent's, and the crawl job, session import and intervention list endpoints are outside this skill.
2. Send `heavy_mode: true` and `include_links: true` on every read, narrowed with `link_filter` when only a subset matters. The plain HTTP tiers silently drop JavaScript-rendered content. Choose `link_filter` on the first read, because it is part of the read cache key and a second read with another filter runs the whole cascade again.
3. Never send a `tier` field and never branch on a `mode` value, because the tier names changed and a removed name such as `3-flaresolverr` is refused with HTTP 400. Read `mode` only to report which tier answered.
4. Give the client a timeout of about 150 seconds, and in PowerShell call `curl.exe` with the inner JSON quotes escaped.
5. Route a 200 on the body's `status` field and a 428, 409 or 400 on the problem body's `code` field: 428 `human_intervention_required` is a human-intervention case, not a failure, 409 `novnc_busy` waits `Retry-After` and retries, and a 200 `session_expired` needs `session/establish` before reading again.
6. On a 428, show `vnc_url` as a clickable link with a short prompt and keep its `flow_id`, then poll `read` with the same body every 30 seconds, at most about five times, stopping early when the user says they are done. Never retry in a tight loop. When the user gives up, close the window with `DELETE /api/v2/session/interventions/{flow_id}` so its slot is free at once.
7. Call `session/establish` first only for a login wall you already know about, never speculatively while a shown `vnc_url` awaits a solve. Check `session/status` before re-establishing, read its `last_window.outcome` to learn how the last window ended, and call `session/clear` when the user logs out or switches accounts.
8. On a blocking site, search first and read the promising results rather than guessing a URL. Open-ended search goes to `research`.

---

### Related skills

- `research` for general research, web search, and every page a normal fetch can read.
- `ascend-memory` for facts about the user that must survive across conversations, when it is installed.
- `audio-scribe` for turning an audio or video recording into text, when it is installed.
- `markdown-writer` for shaping fetched content into a human-facing document.

---

### Checklist

- Base URL taken from `ASCEND_WEB_HUNTER_URL`, else the first candidate whose `/health` answers, else reported down.
- `heavy_mode` and `include_links` set on every `read`.
- A 200 routed on its `status` field and a 428 or 409 on its `code` field, with `session_expired` handled as its own case.
- No `tier` sent and no decision taken on a `mode` value, because the tier names changed and `3-flaresolverr` is refused.
- CAPTCHA and login walls handed to the user with `vnc_url`, then polled with a capped retry, and a window the user gave up on closed by its `flow_id`.
- `session/establish` used only for a login wall you already know about.
- Search run before read whenever the URL on a blocking site was not given to you, open-ended search left to `research`.
