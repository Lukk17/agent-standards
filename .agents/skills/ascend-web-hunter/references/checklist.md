# Ascend Web Hunter Checklist

Run it before calling a read through the service done.

- Base URL taken from `ASCEND_WEB_HUNTER_URL`, else the first candidate whose `/health` answers, else reported down.
- `heavy_mode` and `include_links` set on every `read`.
- A 200 routed on its `status` field and a 428 or 409 on its `code` field, with `session_expired` handled as its own case.
- No `tier` sent and no decision taken on a `mode` value, because the tier names changed and `3-flaresolverr` is refused.
- CAPTCHA and login walls handed to the user with `vnc_url`, then polled with a capped retry, and a window the user gave up on closed by its `flow_id`.
- `session/establish` used only for a login wall you already know about.
- Search run before read whenever the URL on a blocking site was not given to you, open-ended search left to `research`.
