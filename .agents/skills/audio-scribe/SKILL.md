---
name: audio-scribe
description: 'Speech-to-text through the self-hosted AudioScribe service, with speaker merging for multi-track recordings. Use when the user says "transcribe this" or "write up this meeting". Not for a web page, use `research`.'
compatibility: Requires the self-hosted AudioScribe service reachable over HTTP. Its base URL is configured by the user and appears in the examples as the placeholder $BASE, for example `http://audio-scribe.local:8080`. No default base URL is assumed.
metadata:
  version: "1.1.0"
---

# AudioScribe

Turn speech into text through AudioScribe, which fronts three swappable transcription backends plus one endpoint built for multi-track Audacity and Craig recordings. Every endpoint takes a multipart `file` upload and returns a Markdown transcript.

---

### When not to activate

- Pulling text out of a web page or a URL, use `research`, which hands a page that blocks a normal fetch to `ascend-web-hunter` when that is installed.
- Storing a fact from the transcript so it survives the conversation, use `ascend-memory` if it is installed, else give the fact back to the user to keep.
- Formatting the finished transcript into a human-facing document, use `markdown-writer`.

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

### Reference files

| Open this | When |
| --- | --- |
| [backends-and-commands.md](references/backends-and-commands.md) | Making a call: the endpoint and form field table, the Bash and PowerShell commands per backend, streaming, with pass and fail examples |
| [checklist.md](references/checklist.md) | Before calling a transcription done |
