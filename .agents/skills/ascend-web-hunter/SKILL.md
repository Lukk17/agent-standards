---
name: ascend-web-hunter
description: 'Reads pages behind a WAF, CAPTCHA or login through the self-hosted ascend-web-hunter service. Use when the user says "this page is behind Cloudflare" or "this site needs a login". Not for other pages, use `research`.'
compatibility: Requires the self-hosted ascend-web-hunter service of AscendAI (https://github.com/Lukk17/AscendAI) reachable over HTTP. The base URL comes from ASCEND_WEB_HUNTER_URL, else the first of http://ascend-web-hunter.internal and http://localhost:7021 whose /health answers, and appears in the examples as $BASE.
metadata:
  version: "1.1.0"
---

# Ascend Web Hunter

Pull page content through ascend-web-hunter, the web reading service of [AscendAI](https://github.com/Lukk17/AscendAI), listening on port 7021. A read cascades from fast HTTP through headed and patched browsers to a remote NoVNC session a human can drive. Use it for any page a plain fetch cannot read, and for login walls the user signs into once so the service can cache the session.

| Task | Open |
| --- | --- |
| Probing the candidate base URLs before the first call | [base-url.md](references/base-url.md) |
| The six endpoints, the tier table, and the response cases with their fields | [endpoints-and-responses.md](references/endpoints-and-responses.md) |
| Exact Bash and PowerShell commands for read, session and search, and the CAPTCHA hand-off | [calls-and-sessions.md](references/calls-and-sessions.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling a read done | [checklist.md](references/checklist.md) |

---

### When not to activate

- General research, a web search, or reading a page a normal fetch returns in full, use `research`.
- Recalling something the user told you in an earlier conversation, use `ascend-memory` if it is installed, else ask the user.
- Turning a recording or a video into text, use `audio-scribe` if it is installed, else tell the user that no transcription route is available.

---

### Rules

1. Resolve the base URL in a fixed order: the environment variable `ASCEND_WEB_HUNTER_URL` when it is set, otherwise the first of `http://ascend-web-hunter.internal` and `http://localhost:7021` whose `/health` endpoint answers. When none answers, tell the user the service is down. Do not fall back to a normal web fetch without saying so.
2. Call only the six agent-facing endpoints: `GET /api/v1/web/search`, `POST /api/v2/web/read`, `session/establish`, `session/status` and `session/clear`, and `DELETE /api/v2/session/interventions/{flow_id}`. Every other endpoint is an operator action or outside this skill.
3. Send `heavy_mode: true` and `include_links: true` on every read, because the plain HTTP tiers silently drop JavaScript-rendered content. Choose any `link_filter` on the first read, because it is part of the read cache key.
4. Never send a `tier` field and never branch on a `mode` value, because the tier names changed. Read `mode` only to report which tier answered.
5. Give the client a timeout of about 150 seconds, and in PowerShell call `curl.exe` with the inner JSON quotes escaped.
6. Route a 200 on the body's `status` field and a 428, 409 or 400 on the problem body's `code` field: 428 `human_intervention_required` is a human-intervention case, not a failure, 409 `novnc_busy` waits `Retry-After` and retries, and a 200 `session_expired` needs `session/establish` before reading again.
7. On a 428, show `vnc_url` as a clickable link with a short prompt and keep its `flow_id`, then poll `read` with the same body every 30 seconds, at most about five times, stopping early when the user says they are done. Never retry in a tight loop. When the user gives up, close the window with the intervention `DELETE` so its slot is free at once.
8. Call `session/establish` first only for a login wall you already know about, never speculatively while a shown `vnc_url` awaits a solve. Check `session/status` before re-establishing, read its `last_window.outcome` to learn how the last window ended, and call `session/clear` when the user logs out or switches accounts.
9. On a blocking site, search first and read the promising results rather than guessing a URL. Open-ended search goes to `research`.
