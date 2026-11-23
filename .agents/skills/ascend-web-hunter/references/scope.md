# Scope

Companion reference for the [ascend-web-hunter](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- A plain fetch already returned a Cloudflare interstitial, a WAF challenge, a CAPTCHA, or a bot check.
- The target page is known to block normal fetching, such as a job board or a shop that rejects automated clients.
- The target page sits behind a login the user can complete once on a phone or a laptop.
- The user says "this page is behind Cloudflare", "the fetch got a bot check", "this site needs a login", "scrape this job listing that blocks bots" or "log me in to that site so you can read it".

The service extracts page content for pages a normal fetch cannot read: WAF bypass, CAPTCHA escalation to a remote browser and cached login sessions.

---

### When not to activate

- General research, a web search, or reading a page a normal fetch returns in full, use `research`.
- Recalling something the user told you in an earlier conversation, use `ascend-memory` if it is installed. It needs
  its own self-hosted service, so without it ask the user.
- Turning a recording or a video into text, use `audio-scribe` if it is installed. It needs its own self-hosted
  service, so without it tell the user that no transcription route is available.
- Writing or polishing the markdown you produce from a fetched page, use `markdown-writer`.

---

### Related skills

- `research` for general research, web search, and every page a normal fetch can read.
- `ascend-memory` for facts about the user that must survive across conversations, when it is installed.
- `audio-scribe` for turning an audio or video recording into text, when it is installed.
- `markdown-writer` for shaping fetched content into a human-facing document.
