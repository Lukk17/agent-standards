---
name: audio-scribe
description: Transcribe audio (speech-to-text) via the self-hosted AudioScribe service. Use this whenever the user wants the spoken content of an audio or video file as text — meeting recordings, voice notes, podcasts, interviews, lectures, Discord/Craig recordings, Audacity multi-track sessions. Trigger on phrases like "transcribe this", "what's said in this audio", "turn this recording into text", or any file path ending in .mp3 / .wav / .m4a / .ogg / .flac / .zip (Audacity).
---

# AudioScribe

Speech-to-text with three swappable backends and one specialised endpoint for multi-track Audacity / Craig recordings. All endpoints accept a multipart `file` upload and return a Markdown transcript.

## Base URL

Use whatever base URL the runtime gives you for AudioScribe; examples below use `$BASE`. Ask if it isn't configured.

## Endpoints

All under `/api/v1/transcribe`. Each takes a `file` form field plus a few optional form fields. By default the response is the transcript file itself (Markdown). Set `stream=true` to get an SSE progress stream that ends with a `download_url` you can fetch from `/api/v1/transcribe/download/{file_id}`.

- `POST /local` — local faster-whisper on the host GPU. Best when the file is sensitive (no third-party API), GPU is available, or you want timestamps. Form fields: `file`, `model` (default `Systran/faster-whisper-large-v3`), `language` (auto if omitted), `with_timestamps` (default false), `stream`.
- `POST /openai` — OpenAI Whisper API. Best for short clips when you want the highest-quality general-purpose result and don't need timestamps. Server handles chunking for files >25MB. Form fields: `file`, `model` (default `whisper-1`), `language`, `stream`.
- `POST /hf` — Hugging Face Inference. Use when the user names a specific HF model or you want to avoid OpenAI. Form fields: `file`, `model` (default `openai/whisper-large-v3`), `hf_provider` (default `hf-inference`), `stream`.
- `POST /audacity` — multi-track `.zip` (Audacity `.aup` project, or a Craig Bot dump). Extracts each track, transcribes them with whichever backend you pick, and merges chronologically into `[HH:MM:SS] [Speaker] …` lines. Form fields: `file` (must be `.zip`), `provider` (`local` / `openai` / `hf`, default `local`), `model`, `language`, `hf_provider`, `stream`.

## Picking a backend

Default to `local` when the host has a GPU — it's free, private, and supports timestamps. Switch to `openai` for short clips where quality matters and the recording is non-sensitive. Use `hf` only when the user pins a specific HF model. For multi-speaker or Discord/Craig recordings always use `/audacity`.

## Examples

Quick transcription with the local model (response is the `.md` file) — Bash:

```bash
curl -s -o transcript.md \
  -X POST $BASE/api/v1/transcribe/local \
  -F "file=@meeting.m4a" \
  -F "with_timestamps=true"
```

PowerShell:

```powershell
curl.exe -s -o transcript.md `
  -X POST $BASE/api/v1/transcribe/local `
  -F "file=@meeting.m4a" `
  -F "with_timestamps=true"
```

OpenAI backend, English forced — Bash:

```bash
curl -s -o transcript.md \
  -X POST $BASE/api/v1/transcribe/openai \
  -F "file=@voice-note.mp3" \
  -F "language=en"
```

PowerShell:

```powershell
curl.exe -s -o transcript.md `
  -X POST $BASE/api/v1/transcribe/openai `
  -F "file=@voice-note.mp3" `
  -F "language=en"
```

Audacity / Craig multi-track zip with chronological speaker merge — Bash:

```bash
curl -s -o transcript.md \
  -X POST $BASE/api/v1/transcribe/audacity \
  -F "file=@session.zip" \
  -F "provider=local"
```

PowerShell:

```powershell
curl.exe -s -o transcript.md `
  -X POST $BASE/api/v1/transcribe/audacity `
  -F "file=@session.zip" `
  -F "provider=local"
```

Streaming progress (SSE) for a long file — Bash:

```bash
curl -N -X POST $BASE/api/v1/transcribe/local \
  -F "file=@long-podcast.mp3" \
  -F "stream=true"
```

PowerShell:

```powershell
curl.exe -N -X POST $BASE/api/v1/transcribe/local `
  -F "file=@long-podcast.mp3" `
  -F "stream=true"
```

The stream emits `{"type":"progress",…}` events and ends with `{"type":"complete","download_url":"/api/v1/transcribe/download/<id>"}`. Fetch the URL from `$BASE` to get the Markdown.

Note for PowerShell: line continuation is the backtick `` ` ``, not `\`. Use `curl.exe` so PowerShell doesn't route to its `Invoke-WebRequest` alias.

## Tips

- Long files take real time — set the HTTP client timeout high (10+ minutes) for hour-long recordings, and prefer `stream=true` so the user sees progress instead of staring at a hung request.
- Pass `language` when you know it; auto-detection wastes the first chunk on identification.
- The Markdown response is plain text — feel free to post-process (summarise, extract action items, diarize further) once you have it.
- Servers' `OPENAI_API_KEY` / `HF_TOKEN` are configured server-side — don't ask the user for keys.
