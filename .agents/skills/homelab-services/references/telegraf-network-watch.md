# Telegraf network watch

Read this before setting up the per-second network probes, changing their config, reading their CSV files after a drop, or changing the speed test. The rules live in [SKILL.md](../SKILL.md). Facts marked VERIFIED were measured on the owner's homelab on 2026-10-23 with `telegraf:1.40.1`, unless the mark names another date. Every other command here is UNVERIFIED.

Sources, fetched on 2026-10-23 at tag v1.40.1 of https://github.com/influxdata/telegraf: `plugins/inputs/ping/README.md`, `plugins/inputs/internet_speed/README.md`, `plugins/outputs/file/README.md`, `plugins/serializers/csv/README.md`, `docs/CONFIGURATION.md`, and `config/config.go` for the default of `round_interval`.

---

### What it proves

A short internet drop is gone before anybody looks. Telegraf writes one row a second per target, so the rows show afterwards whether the drop happened and which layer failed:

| The rows show | It was |
|---|---|
| Pings to the router answer, pings past it and both DNS lookups fail | The line or the provider |
| Pings answer, only the lookup through AdGuard Home fails | AdGuard Home |
| Everything answers | One device or its Wi-Fi |
| No rows at all for a while | The VM, since Telegraf runs on it |

Write the files into a folder Syncthing sends to the owner's PC, so the record leaves the VM by itself. The folder setup belongs to the `syncthing` skill.

---

### The config

Run the container with `network_mode: host` and as user 1000, and mount the config file read only and the output folder:

```yaml
telegraf:
  image: telegraf:1.40.1
  network_mode: host
  user: "1000:1000"
  volumes:
    - ./telegraf/telegraf.conf:/etc/telegraf/telegraf.conf:ro
    - <output-dir>:/network-watch
```

The inputs, one row a second for ping and DNS and one every 5 seconds for HTTP:

```toml
[agent]
  flush_interval = "1s"

[[inputs.ping]]
  urls = ["<router-ip>", "<provider-gateway-ip>", "<provider-dns-ip>", "1.1.1.1"]
  method = "native"
  privileged = false
  count = 1
  deadline = "1s"
  interval = "1s"

[[inputs.dns_query]]
  servers = ["<vm-ip>"]
  domains = ["connectivitycheck.gstatic.com"]
  record_type = "A"
  timeout = "1s"
  interval = "1s"

[[inputs.http_response]]
  urls = ["http://connectivitycheck.gstatic.com/generate_204"]
  response_timeout = "2s"
  response_status_code = 204
  interval = "5s"
```

Add a second `[[inputs.dns_query]]` against a public resolver, so a failure of AdGuard Home and a failure of the line look different.

`privileged = false` uses ICMP datagram sockets. The ping README says that mode needs "the process GID to be within the range in the net.ipv4.ping_group_range sysctl and no further capabilities". With host networking the VM's own sysctl applies. Read it on the VM:

```bash
sysctl net.ipv4.ping_group_range
```

It must include 1000. Ubuntu Server ships `0 2147483647` from systemd. Every ping failing at once with an empty response time points here rather than at the network.

---

### CSV output with rotation

One `[[outputs.file]]` per input, selected with `namepass`, with a short fixed list of columns, rotated daily and kept 30 days:

```toml
[[outputs.file]]
  files = ["/network-watch/ping.csv"]
  namepass = ["ping"]
  data_format = "csv"
  csv_header = true
  csv_timestamp_format = "2006-01-02 15:04:05"
  csv_columns = ["timestamp", "tag.url", "field.result_code", "field.percent_packet_loss", "field.average_response_ms"]
  rotation_interval = "24h"
  rotation_max_archives = 30
```

The file README says of `rotation_max_archives`: "Maximum number of rotated archives to keep, any older logs are deleted." Pinning `csv_columns` keeps the rows short. VERIFIED on 2026-10-09: about 535,000 rows and 22.6 MiB a day across three files for four ping targets.

`csv_header` writes the header only when Telegraf creates a file, as the CSV README says, "Enable the header when outputting metrics to a new file". VERIFIED: the current day's `ping.csv` held no header line, while a rotated file held three, one per container start that day. So a script that reads the files tells a ping file by its name, not by its header, and skips every header line it meets.

A failed row has `result_code` other than 0. A ping that timed out can still carry `result_code` 0 with `percent_packet_loss` at 100, so count both. Two failed rows in a row is a drop, which filters out one lost packet.

---

### Changing the config

Telegraf reads its config only when it starts. Make the change in the clone, copy it as in [deploy-and-logs.md](deploy-and-logs.md#copy-and-start), then restart:

```bash
docker restart telegraf
```

Check that it writes, a minute later:

```bash
tail -n 3 <output-dir>/ping.csv
```

A full disk stops the writes, and the rows of that time are lost. VERIFIED: the rows from the night of 2026-10-22, when the VM's root file system was full, are missing, see [disk-full.md](disk-full.md).

---

### The speed test and its traffic

`[[inputs.internet_speed]]` runs a real speedtest.net test, so every test moves real data. The README warns: "This plugin downloads many MB of data each time it is run. As such consider setting a higher interval for this plugin to reduce the demand on your internet connection."

VERIFIED on 2026-10-09 with `telegraf:1.40.1`, measured with `telegraf --test --input-filter internet_speed` in a container on its own bridge network, reading `/proc/net/dev` afterwards: one test received 282,184,059 bytes and sent 402,764,399 bytes, about 685 MB, at about 200 Mbit/s, and filled the line for about 40 seconds. The test runs for a fixed time, so a faster line moves more data. At one test an hour that is about 16 GB a day, and at one every 10 minutes about 100 GB a day.

```toml
[[inputs.internet_speed]]
  interval = "1h"
  cache = true
```

`cache` "Caches the closest server location". `memory_saving_mode` stays off on a fast line, because the README says it reduces accuracy "especially for fast (>30Mb/s) connections".

Telegraf rounds every interval to the clock, `round_interval`, true by default in `config/config.go`. A one hour test therefore starts at the full hour, and a ping or DNS failure in the first minute after it may be the test filling the line. Look for a `speed.csv` row near that time before counting it as an outage.

---

### Keep the probe name out of AdGuard Home

A lookup a second is 86,400 a day. Put the probe's domain into both Ignored domains fields of AdGuard Home, as [adguard-home.md](adguard-home.md#ignored-domains) shows, or it drowns every other query in the log and the statistics.
