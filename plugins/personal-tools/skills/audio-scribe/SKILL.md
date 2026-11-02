---
name: audio-scribe
description: 'Speech-to-text through the self-hosted AudioScribe service, with a local faster-whisper backend, hosted API backends, and speaker merging for multi-track Audacity or Craig recordings. Use when the user says "transcribe this", "turn this recording into text" or "write up this meeting", or hands over an audio or video file or a multi-track .zip. Not for reading a web page, use `research`.'
compatibility: Requires the self-hosted AudioScribe service reachable over HTTP. Its base URL is configured by the user and appears in the examples as the placeholder $BASE, for example `http://audio-scribe.local:8080`. No default base URL is assumed.
---

# AudioScribe

Turn speech into text through AudioScribe, which fronts three swappable transcription backends plus one endpoint
built for multi-track Audacity and Craig recordings. Every endpoint takes a multipart `file` upload and returns a
Markdown transcript.

---

### When to activate

- The user hands you an audio or video file and wants what was said.
- The user asks for meeting notes, action items, or a summary from a recording rather than from text.
- The file is a multi-track `.zip` from Audacity or a Craig bot dump and needs speaker attribution.
- The user asks for timestamps against spoken content.
- The user says "what is said in this audio".

---

### When not to activate

- Pulling text out of a web page or a URL, use `research`, which hands a page that blocks a normal fetch to
  `ascend-web-hunter` when that is installed.
- Storing a fact from the transcript so it survives the conversation, use `ascend-memory` if it is installed. It
  needs its own self-hosted service, so without it give the fact back to the user to keep.
- Formatting the finished transcript into a human-facing document, use `markdown-writer`.

---

### Reference files

| Task | Open |
| --- | --- |
| The endpoint and form field table, the Bash and PowerShell commands per backend, streaming, with pass and fail examples | [references/backends-and-commands.md](references/backends-and-commands.md) |

---

### Rules

1. Read the base URL from the runtime's configuration for AudioScribe and use it as `$BASE`. Ask the user when nothing is configured, and never assume a default host and port.
2. Use the four endpoints under `/api/v1/transcribe`: `/local` (faster-whisper on the host GPU, timestamps), `/openai` (Whisper API, server-side chunking above 25MB), `/hf` (Hugging Face Inference) and `/audacity` (a multi-track `.zip` merged chronologically into `[HH:MM:SS] [Speaker]` lines).
3. Default to `local`: free, audio stays on the host. Use `openai` only for a short, non-sensitive clip, and `hf` only when the user pins a Hugging Face model. Never send a confidential recording to a hosted backend.
4. Send every multi-track Audacity or Craig `.zip` to `/audacity`, the only endpoint that attributes speakers. A single-file recording with several speakers gets no speaker names.
5. In PowerShell call `curl.exe`, not the `Invoke-WebRequest` alias.
6. For a long file, set `stream=true` and a client timeout of ten minutes or more, then fetch the final `download_url` from `/api/v1/transcribe/download/{file_id}`.
7. Set `language` whenever it is known, so auto-detection does not spend the first chunk.
8. Never ask the user for an API key. Hosted backend credentials live on the server.

---

### Related skills

- `research` for text that lives on a web page rather than in a recording.
- `ascend-web-hunter` for a page behind a WAF, a CAPTCHA or a login that blocks a normal fetch, when it is installed.
- `ascend-memory` for storing a durable fact you extracted from a transcript, when it is installed.
- `markdown-writer` for turning a raw transcript into a document a person reads.

---

### Checklist

- Base URL resolved from configuration, not from a default.
- Backend chosen from privacy, clip length, and speaker count, with `local` as the default.
- Multi-track and Craig recordings sent to `/audacity` rather than split by hand.
- `language` set whenever it is known.
- `stream=true` and a raised client timeout on anything long.
- No API key requested from the user.
