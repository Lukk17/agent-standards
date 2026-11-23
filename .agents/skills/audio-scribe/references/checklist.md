# AudioScribe Checklist

Run it before calling a transcription done.

- Base URL resolved from configuration, not from a default.
- Backend chosen from privacy, clip length, and speaker count, with `local` as the default.
- Multi-track and Craig recordings sent to `/audacity` rather than split by hand.
- `language` set whenever it is known.
- `stream=true` and a raised client timeout on anything long.
- No API key requested from the user.
