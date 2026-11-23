# Ascend Memory Checklist

Run it before calling a memory read or write done.

- Base URL resolved from configuration, not from a default.
- `user_id` present on every insert, search, and wipe.
- Search run before answering anything that depends on the user's history.
- Corrections applied as delete plus insert, not insert alone.
- `metadata` short and structural, with prose kept in `text`.
- `wipe` used only on an explicit request to forget everything.
