# Scope

Companion reference for the [audio-scribe](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- The user hands you an audio or video file and wants what was said.
- The user asks for meeting notes, action items, or a summary from a recording rather than from text.
- The file is a multi-track `.zip` from Audacity or a Craig bot dump and needs speaker attribution.
- The user asks for timestamps against spoken content.
- The user says "transcribe this", "turn this recording into text", "write up this meeting" or "what is said in this audio", or hands over an audio or video file or a multi-track `.zip`.

The service has a local faster-whisper backend and hosted API backends, and merges speakers for multi-track Audacity or Craig recordings.

---

### When not to activate

- Pulling text out of a web page or a URL, use `research`, which hands a page that blocks a normal fetch to
  `ascend-web-hunter` when that is installed.
- Storing a fact from the transcript so it survives the conversation, use `ascend-memory` if it is installed. It
  needs its own self-hosted service, so without it give the fact back to the user to keep.
- Formatting the finished transcript into a human-facing document, use `markdown-writer`.

---

### Related skills

- `research` for text that lives on a web page rather than in a recording.
- `ascend-web-hunter` for a page behind a WAF, a CAPTCHA or a login that blocks a normal fetch, when it is installed.
- `ascend-memory` for storing a durable fact you extracted from a transcript, when it is installed.
- `markdown-writer` for turning a raw transcript into a document a person reads.
