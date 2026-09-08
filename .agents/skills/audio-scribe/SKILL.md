---
name: audio-scribe
description: Speech-to-text through the self-hosted AudioScribe service, covering a local faster-whisper backend, hosted API backends, and chronological speaker merging for multi-track Audacity or Craig recordings. Use when the user says "transcribe this", "what is said in this audio", "turn this recording into text", "write up this meeting", or hands you a path ending in .mp3, .wav, .m4a, .ogg, .flac, or .zip. Not for extracting text from a web page, use `ascend-web-hunter`.
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

---

### When not to activate

- Pulling text out of a web page or a URL, use `ascend-web-hunter`.
- Storing a fact from the transcript so it survives the conversation, use `ascend-memory`.
- Formatting the finished transcript into a human-facing document, use `markdown-writer`.

---

### Take the base URL from configuration, never from a guess

Read the base URL from whatever configuration surface the runtime provides for AudioScribe. It differs between a
host install, a container, and a remote deployment. Ask the user when nothing is configured. Examples below use
`$BASE` as the placeholder. A configured value might look like `http://audio-scribe.local:8080`, shown here only as
an example of the shape, with the real value always coming from the user's own configuration.

Pass: resolve the base URL from configuration, then use it as `$BASE` in every call.

Fail: assume a default host and port and upload the user's recording to whatever answers.

---

### Use the four endpoints under /api/v1/transcribe

| Endpoint | Backend | Form fields |
| --- | --- | --- |
| `/local` | Local faster-whisper on the host GPU | `file`, `model` (default `Systran/faster-whisper-large-v3`), `language`, `with_timestamps`, `stream` |
| `/openai` | OpenAI Whisper API, server-side chunking above 25MB | `file`, `model` (default `whisper-1`), `language`, `stream` |
| `/hf` | Hugging Face Inference | `file`, `model` (default `openai/whisper-large-v3`), `hf_provider` (default `hf-inference`), `stream` |
| `/audacity` | Multi-track `.zip`, merged chronologically | `file` (must be `.zip`), `provider` (`local`, `openai`, `hf`, default `local`), `model`, `language`, `hf_provider`, `stream` |

The default response is the transcript file itself. Set `stream=true` for a server-sent-events progress stream that
ends with a `download_url` you fetch from `/api/v1/transcribe/download/{file_id}`. The `/audacity` endpoint extracts
each track, transcribes it with the backend you name, and merges the results into `[HH:MM:SS] [Speaker] …` lines.

Pass: `POST /audacity` with a Craig `.zip` so speakers stay attributed.

Fail: unzip the Craig dump yourself and post one track at a time to `/local`, which loses the chronological merge.

---

### Pick the backend from privacy, length, and speaker count

Default to `local`: it is free, keeps the audio on the host, and supports timestamps whenever a GPU is available.
Switch to `openai` for a short, non-sensitive clip where general-purpose quality matters most and timestamps do not.
Reach for `hf` only when the user pins a specific Hugging Face model. Send anything multi-speaker, and every
Discord or Craig recording, to `/audacity`.

Pass: a confidential hour-long interview goes to `/local` with `with_timestamps=true`.

Fail: a confidential recording goes to `/openai` because it is a little faster.

Local backend with timestamps, Bash:

```bash
curl -s -o transcript.md -X POST $BASE/api/v1/transcribe/local -F "file=@meeting.m4a" -F "with_timestamps=true"
```

Local backend with timestamps, PowerShell:

```powershell
curl.exe -s -o transcript.md -X POST $BASE/api/v1/transcribe/local -F "file=@meeting.m4a" -F "with_timestamps=true"
```

Hosted backend with the language forced, Bash:

```bash
curl -s -o transcript.md -X POST $BASE/api/v1/transcribe/openai -F "file=@voice-note.mp3" -F "language=en"
```

Hosted backend with the language forced, PowerShell:

```powershell
curl.exe -s -o transcript.md -X POST $BASE/api/v1/transcribe/openai -F "file=@voice-note.mp3" -F "language=en"
```

Multi-track zip with a chronological speaker merge, Bash:

```bash
curl -s -o transcript.md -X POST $BASE/api/v1/transcribe/audacity -F "file=@session.zip" -F "provider=local"
```

Multi-track zip with a chronological speaker merge, PowerShell:

```powershell
curl.exe -s -o transcript.md -X POST $BASE/api/v1/transcribe/audacity -F "file=@session.zip" -F "provider=local"
```

Call `curl.exe` in PowerShell so the shell does not route the name to its `Invoke-WebRequest` alias.

---

### Stream long files instead of blocking on one request

Long recordings take real time, so raise the client timeout to ten minutes or more for anything approaching an hour
and set `stream=true` so the user watches progress instead of a hung request. The stream emits
`{"type":"progress",…}` events and ends with
`{"type":"complete","download_url":"/api/v1/transcribe/download/<id>"}`, which you fetch from `$BASE` to get the
Markdown.

Pass: an hour-long podcast goes out with `stream=true` and a ten-minute client timeout.

Fail: the same file goes out on a default 30-second timeout and the request dies mid-transcription.

Streaming progress, Bash:

```bash
curl -N -X POST $BASE/api/v1/transcribe/local -F "file=@long-podcast.mp3" -F "stream=true"
```

Streaming progress, PowerShell:

```powershell
curl.exe -N -X POST $BASE/api/v1/transcribe/local -F "file=@long-podcast.mp3" -F "stream=true"
```

---

### Pass the language when you know it, and never ask for API keys

Set `language` whenever the user names it or the file makes it obvious, because auto-detection spends the first
chunk identifying the language instead of transcribing it. Credentials for the hosted backends are configured on the
server, so asking the user for a key is both unnecessary and a way to end up with a secret in a transcript.

Pass: `-F "language=pl"` on a Polish voice note.

Fail: prompt the user to paste an API key so the hosted backend can run.

---

### Related skills

- `ascend-web-hunter` for text that lives on a web page rather than in a recording.
- `ascend-memory` for storing a durable fact you extracted from a transcript.
- `markdown-writer` for turning a raw transcript into a document a person reads.

---

### Checklist

- Base URL resolved from configuration, not from a default.
- Backend chosen from privacy, clip length, and speaker count, with `local` as the default.
- Multi-track and Craig recordings sent to `/audacity` rather than split by hand.
- `language` set whenever it is known.
- `stream=true` and a raised client timeout on anything long.
- No API key requested from the user.
