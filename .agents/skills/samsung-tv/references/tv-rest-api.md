# The TV's REST API

Read this before checking the TV directly. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on a 2024 QN85D in the Polish region, the power state and the launch `POST` on 2026-11-06, or read in the source named. Every other statement is UNVERIFIED.

Sources: the `samsungtvws` library at https://github.com/xchwarze/samsung-tv-ws-api, which Home Assistant's `samsungtv` integration uses, and its Frame check in `samsungtvws/art/art.py`.

---

### What answers on which port

| Port | What | Login |
|---|---|---|
| 8001 | REST API over `http`, device info, one call per app and the app launch | none, anyone on the LAN can read it and launch an app. VERIFIED |
| 8002 | Secure websocket for keys, power and the websocket app launch | a token the TV hands out once the owner allows the client on screen. Home Assistant stores it in the `samsungtv` config entry. VERIFIED |

The agent itself uses port 8001 only, and only with `GET`. The launch `POST` on port 8001 is sent by Home Assistant, and everything on port 8002 goes through Home Assistant too.

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
| `PowerState` | `on` while the screen is on, `standby` while the screen is off and the network still up. VERIFIED. The turn on automation reads it, see [power-on.md](power-on.md#what-wakes-the-tv) |
| `FrameTVSupport` | `true` only on a Frame TV. The art API needs it, see [cast-and-ambient.md](cast-and-ambient.md) |
| `TokenAuthSupport` | whether the TV hands out the token port 8002 needs |
| `developerMode` | whether developer mode is on |

Read only the fields you need:

```bash
curl -s --max-time 5 http://<tv-ip>:8001/api/v2/ | jq '.device | {networkType, wifiMac, PowerState, FrameTVSupport, TokenAuthSupport, developerMode}'
```

The MAC address goes into the owner's notes and the Home Assistant automation, never into a shared file.

A TV in standby still answers, with `PowerState` `standby`. VERIFIED. No answer within the timeout means the TV is fully off with its network down, or on another address. Read the address from Home Assistant or the router before concluding anything. How long a TV stays in standby before its network goes down is UNVERIFIED.

---

### One app

```bash
curl -s --max-time 5 http://<tv-ip>:8001/api/v2/applications/<app-id>
```

An installed app answers with `id`, `name`, `running`, `version` and `visible`. An ID that is not installed answers `{"code":404,"message":"Not found error."}`. VERIFIED, both forms. How to use it to pick an ID is in [app-ids.md](app-ids.md). `running` says the app is started and `visible` that it is in front, INFERRED, high confidence, from the launch tests below.

The same path launches, closes and installs an app with `POST`, `DELETE` and `PUT`, as `rest_app_run`, `rest_app_close` and `rest_app_install` in `samsungtvws/rest.py` show. VERIFIED in the source. A `POST` with no body and no login answers HTTP `200`, and the app then reports `running` `true` and `visible` `true`. VERIFIED with Disney+ `3201901017640` and Netflix. Spotify answered `200` and `running` `true` but `visible` `false`, so whether it comes to the front is UNVERIFIED. A `200` says the TV took the call, not that the app is in front. Home Assistant sends the `POST` through a `rest_command`, see [home-assistant-control.md](home-assistant-control.md#launch-an-app). The agent never sends `POST`, `DELETE` or `PUT` itself (hard rule 1). `DELETE` and `PUT` were not tested, UNVERIFIED.
