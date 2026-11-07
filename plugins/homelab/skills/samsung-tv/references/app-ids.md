# App IDs

Read this before writing an app ID into a script, an automation or a note. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on a 2024 QN85D in the Polish region, or read in the page named.

Sources: the community ID list at https://github.com/xchwarze/samsung-tv-ws-api/blob/master/APPLICATIONS.md, and the Home Assistant `samsungtv` page at https://www.home-assistant.io/integrations/samsungtv/.

---

### Why there is no app list

Samsung removed the call that listed installed apps on newer models. APPLICATIONS.md, under "Getting Installed Applications from Your TV (Tizen Studio)": "Samsung removed the API previously used to fetch installed apps directly from the plugin." VERIFIED.

Home Assistant shows apps in the `source_list` only on some older models. The `samsungtv` page, under "Selecting a source": "Some older models also expose the installed applications through the WebSocket, in which case the source list is adjusted accordingly." VERIFIED.

So the way to confirm an ID is to ask the TV about that one ID.

---

### Confirm an ID

1. Take the candidate IDs for the app from the table below or from APPLICATIONS.md, which warns that "IDs are not guaranteed to work on your TV".
2. Ask the TV about each one:

```bash
curl -s --max-time 5 http://<tv-ip>:8001/api/v2/applications/<app-id>
```

3. Keep the ID that answers with a `name`. A `404` means that ID is not installed on this TV.
4. Write the confirmed ID into the owner's notes with the model and region, because the same app can carry another ID elsewhere.

To check several candidates in one go:

```bash
for id in <app-id-1> <app-id-2> <app-id-3>; do printf '%s ' "$id"; curl -s --max-time 5 "http://<tv-ip>:8001/api/v2/applications/$id"; echo; done
```

---

### IDs measured on one TV

Installed on a 2024 QN85D, Polish region, VERIFIED with the call above:

| App | ID |
|---|---|
| Spotify | `3201606009684` |
| Disney+ | `3201901017640` |
| Netflix | `3201907018807` |
| YouTube | `111299001912` |
| Prime Video | `3201910019365` |
| HBO Max | `3202301029760` |
| Plex | `3201512006963` |
| Twitch | `3202203026841` |
| Xbox | `3202203026799` |

Answered `404` on the same TV, so they are other regions' or older IDs, or apps not installed there, VERIFIED:

| App | ID |
|---|---|
| Disney+ | `3202204027038`, `3202009021709` |
| Netflix | `11101200001` |
| Prime Video | `3201512006785` |
| HBO Max | `3201601007230` |
| HBO GO | `3201706012478` |
| SmartThings | `3201710015016`, `3201910019378` |
| Amazon Alexa | `3202004020626` |

On another model or region, confirm again before use. A `404` there for an ID in the first table is not an error in this file.
