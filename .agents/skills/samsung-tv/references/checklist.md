# Samsung TV Checklist

Run it before calling work on the TV or its Home Assistant scripts done. The rules behind the items are in [SKILL.md](../SKILL.md).

- [ ] Every app ID in a script answered the applications call with its `name` on the TV the script is for
- [ ] Apps launch through the shared script and its `rest_command` `POST`, which stops with an error on a status other than `200`, never through `media_player.play_media`
- [ ] An automation on `samsungtv.turn_on` sends `KEY_POWER` only when `PowerState` reads `standby`, and the entity shows turn on
- [ ] Power On with Mobile is on in the TV's Expert Settings, and the network type was read before trusting Wake on LAN
- [ ] Home Assistant Cast is used only with an `https` external URL set
- [ ] No address, MAC, entity ID or token of a real setup in the skill or a shared repository
- [ ] Every change in Home Assistant had its own yes after the worst case and the undo were stated
- [ ] Every UNVERIFIED fact used is still marked UNVERIFIED in the result
