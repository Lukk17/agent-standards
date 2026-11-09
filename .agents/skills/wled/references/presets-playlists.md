# Presets and Playlists

Read this before saving, applying, deleting or listing presets, or building a playlist. The rules live in [SKILL.md](../SKILL.md). Every save and delete writes `/presets.json`, so back it up first as [backup-and-restore.md](backup-and-restore.md) shows.

Written for WLED 16. Sources: https://kno.wled.ge/features/presets/ and the Playlists section of https://kno.wled.ge/interfaces/json-api/, and the WLED 16 source files `wled00/presets.cpp`, `playlist.cpp` and `json.cpp` at https://github.com/wled/WLED. No call here was sent to a device.

Contents:

1. [What a preset is](#what-a-preset-is)
2. [List presets](#list-presets)
3. [Apply a preset](#apply-a-preset)
4. [Save a preset](#save-a-preset)
5. [Delete a preset](#delete-a-preset)
6. [Playlists](#playlists)
7. [Keep the preset file small](#keep-the-preset-file-small)

---

### What a preset is

1. A preset is a saved state object, or a saved API call, stored under an ID from 1 to 250 in `/presets.json` (VERIFIED, docs "support for up to 250 presets", and `presets.cpp` `savePreset` refuses 0 and 251 to 254). ID 255 is a temporary preset the device uses itself.
2. A playlist is a preset whose object holds a `playlist` key, and it is applied like any other preset.
3. The state object reports the running preset in `ps` and the running playlist in `pl`. The name is not in the state, so match the ID against `/presets.json` (VERIFIED, docs "Obtaining preset list").

---

### List presets

```bash
curl -s http://<wled-host>/presets.json
```

The answer is an object keyed by ID as a string. Each entry has `n` for its name and, when set, `ql` for its quick load label. Key `"0"` is an empty placeholder the device creates (VERIFIED, `presets.cpp` `initPresetsFile`).

---

### Apply a preset

Applying writes nothing to flash. It changes the light, so it needs the user's yes like any state change.

```bash
curl -s -X POST -H 'Content-Type: application/json' -d '{"ps":5}' http://<wled-host>/json/state
```

`"ps":"1~5~"` steps to the next preset from 1 to 5 on each call, and `"ps":"1~5r"` picks one at random (VERIFIED, docs `ps` row). Neither gives the same result twice, so never retry them. Applying the preset that is already running does nothing (VERIFIED, `json.cpp` `deserializeState`, `presetCycCurr != currentPreset`).

---

### Save a preset

Save the current state with a name, its brightness and its segment bounds. The docs give this form (VERIFIED, https://kno.wled.ge/features/presets/ "Saving named presets"):

```bash
curl -s -X POST -H 'Content-Type: application/json' -d '{"psave":5,"n":"<name>","ib":true,"sb":true}' http://<wled-host>/json/state
```

| Key | Meaning |
|---|---|
| `psave` | Target ID 1 to 250, an existing preset there is overwritten |
| `n` | Name, up to 32 characters, `Preset <id>` when left out |
| `ib` | Include brightness |
| `sb` | Include segment bounds, needed for a boot preset |
| `sc` | Save only the selected segments |
| `ql` | Quick load label, up to 2 characters in the web page |
| `bootps` | Also make this the boot preset, a config change (VERIFIED, `presets.cpp` `savePreset`) |

Check the target ID in `/presets.json` first and tell the user when it is taken, because the save overwrites it with no warning.

Save a fixed state rather than the current one by sending the state keys together with `"o":true`, so the body itself is stored. The source says this path "often causes presets.json corruption", so take a fresh backup right before it (VERIFIED, `presets.cpp` `savePreset`). Saving the current state is the safer path: set the light first, then send `psave` alone.

`rb` in the same body as `psave` is ignored (VERIFIED, `json.cpp`, `if (root[F("psave")].isNull()) doReboot = ...`).

---

### Delete a preset

```bash
curl -s -X POST -H 'Content-Type: application/json' -d '{"pdel":5}' http://<wled-host>/json/state
```

The ID stays in the file with an empty object (VERIFIED, `presets.cpp` `deletePreset`). A playlist or a schedule that names the ID stops working, so search `/presets.json` and the time settings in `GET /json/cfg` for the ID before deleting.

---

### Playlists

Start a playlist without saving it:

```bash
curl -s -X POST -H 'Content-Type: application/json' -d '{"playlist":{"ps":[1,2,3],"dur":[300,300,600],"transition":[10],"repeat":0}}' http://<wled-host>/json/state
```

| Key | Meaning |
|---|---|
| `ps` | Preset IDs in order, at most 100 entries (VERIFIED, `playlist.cpp` `loadPlaylist`) |
| `dur` | Time per entry in tenths of a second, one number for all, 10 seconds when left out |
| `transition` | Transition into each entry in tenths of a second, one number for all, the current transition when left out |
| `repeat` | Rounds before it ends, `0` or left out means forever, a negative number means forever in random order (VERIFIED, `playlist.cpp`) |
| `end` | Preset applied when it ends, no effect when it runs forever, `255` brings back the preset that ran before (VERIFIED, `playlist.cpp`) |
| `r` | `true` shuffles the order (VERIFIED, `playlist.cpp`) |

The table rows without a source are VERIFIED in the Playlists section of https://kno.wled.ge/interfaces/json-api/. `"np":true` jumps to the next entry, since WLED 0.15, and is not safe to retry.

Save a playlist as a preset by sending the `playlist` object with `psave`, `n` and `"o":true`, then apply it with `{"ps":<id>}`. The docs show the stored form, an entry such as `"9":{"playlist":{...},"on":true,"n":"<name>"}` in `/presets.json`.

---

### Keep the preset file small

The docs say random writes to the preset file are "very resource intensive", the light can freeze "for up to a few seconds", and advise "not having more than 50-ish single segment or a dozen of multi-segment presets" (VERIFIED, https://kno.wled.ge/features/presets/ "A note on performance"). So:

1. Do not save presets in a loop or on every change. Save once, when the user asks.
2. Prefer sending a state directly over saving it as a preset when it is only used by an outside program.
3. Do not edit `/presets.json` by uploading a changed copy while the device runs a playlist from it.

How many writes the flash survives is not documented by WLED (UNVERIFIED).
