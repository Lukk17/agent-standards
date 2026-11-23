# Homelab Services Checklist

Run it before calling work on the stack done. Each item names the command or the output that proves it. The rules behind the items are in [SKILL.md](../SKILL.md) and in the reference of each service.

- [ ] The change was made in the clone first and copied with `scp`, then `docker compose pull`, `docker compose up -d` and `docker compose ps`
- [ ] A container whose mounted file changed was restarted, Telegraf above all
- [ ] Every service in the Compose file carries `max-size` and `max-file`, and the containers were recreated once after the limit was added
- [ ] Every mounted folder existed before the first start and belongs to the login user
- [ ] A configuration file or database was backed up before the edit, and the value was read back afterwards
- [ ] A lower query log interval was approved after the owner heard that old queries go for good
- [ ] Uptime Kuma was restarted after a new tag, and `docker logs --since 1m uptime-kuma 2>&1 | grep -c PROMETHEUS` printed 0
- [ ] `.env` is mode 600, every value was checked by length, and nothing secret was printed
- [ ] The data disk is mounted by UUID with `nofail`, the empty mount point carries `chattr +i`, and `findmnt` showed the disk
- [ ] `df -h /` read after any change that writes data, and the largest container logs checked when it climbs
- [ ] The local CA was read back and shows `CA:TRUE, pathlen:0`, `Permitted: DNS:internal` and both excluded addresses, and `ca.key` is in no repository
- [ ] Every `.internal` name with a proxy host is in `INTERNAL_DNS_NAMES`, the SSL tab of every proxy host is on None, and the proxy was restarted after the job logged `issuing a new certificate`
- [ ] The certificate end date on the `notAfter=` line of `docker logs --tail 2 internal-ca` is more than 30 days away, or the job ran again
