# The TV's REST API

Read this before checking the TV directly. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on a 2024 QN85D in the Polish region. Every other statement is UNVERIFIED.

Sources: the `samsungtvws` library at https://github.com/xchwarze/samsung-tv-ws-api, which Home Assistant's `samsungtv` integration uses, and its Frame check in `samsungtvws/art/art.py`.

---

### What answers on which port

| Port | What | Login |
|---|---|---|
| 8001 | REST API over `http`, device info and one call per app | none, anyone on the LAN can read it. VERIFIED |
| 8002 | Secure websocket for keys and app launches | a token the TV hands out once the owner allows the client on screen. Home Assistant stores it in the `samsungtv` config entry. VERIFIED |

The agent uses port 8001 only, and only with `GET`. Everything on port 8002 goes through Home Assistant.

---

### Device info

```bash
curl -s --max-time 5 http://<tv-ip>:8001/api/v2/
```

The fields sit under the `device` key. The ones worth reading, VERIFIED present on the QN85D:

| Field | Tells you |
|---|---|
| `networkType` | `wired` or `wireless`, which decides how far to trust Wake on LAN, see [power-on.md](power-on.md) |
| `wifiMac` | the MAC address to send the magic packet to |
| `PowerState` | whether the TV reports itself on or in standby |
| `FrameTVSupport` | `true` only on a Frame TV. The art API needs it, see [cast-and-ambient.md](cast-and-ambient.md) |
| `TokenAuthSupport` | whether the TV hands out the token port 8002 needs |
| `developerMode` | whether developer mode is on |

Read only the fields you need:

```bash
curl -s --max-time 5 http://<tv-ip>:8001/api/v2/ | jq '.device | {networkType, wifiMac, PowerState, FrameTVSupport, TokenAuthSupport, developerMode}'
```

The MAC address goes into the owner's notes and the Home Assistant automation, never into a shared file.

No answer within the timeout means the TV is off the network, in deep standby, or on another address. Read the address from Home Assistant or the router before concluding anything. That a TV in standby stops answering port 8001 is UNVERIFIED.

---

### One app

```bash
curl -s --max-time 5 http://<tv-ip>:8001/api/v2/applications/<app-id>
```

An installed app answers with `id`, `name`, `running`, `version` and `visible`. An ID that is not installed answers `{"code":404,"message":"Not found error."}`. VERIFIED, both forms. How to use it to pick an ID is in [app-ids.md](app-ids.md).

The same path launches, closes and installs an app with `POST`, `DELETE` and `PUT`, as `rest_app_run`, `rest_app_close` and `rest_app_install` in `samsungtvws/rest.py` show. VERIFIED in the source. The agent never sends them (hard rule 1).
