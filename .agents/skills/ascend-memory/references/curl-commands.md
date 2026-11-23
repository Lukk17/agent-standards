# curl Commands

The exact Bash and PowerShell command for each call the [ascend-memory](../SKILL.md) skill makes. `$BASE` is the base URL resolved from configuration. The endpoints, their body fields and the rule behind each call are in [api-endpoints.md](api-endpoints.md).

Call `curl.exe` in PowerShell so the shell does not route the name to its `Invoke-WebRequest` alias, and escape the inner double quotes of any JSON body.

---

### Insert

Bash:

```bash
curl -s -X POST $BASE/api/v1/memory/insert -H "Content-Type: application/json" -d '{"user_id":"<user-id>","text":"Prefers terse responses with no trailing summaries.","metadata":{"type":"preference"}}'
```

PowerShell:

```powershell
curl.exe -s -X POST $BASE/api/v1/memory/insert -H "Content-Type: application/json" -d '{\"user_id\":\"<user-id>\",\"text\":\"Prefers terse responses with no trailing summaries.\",\"metadata\":{\"type\":\"preference\"}}'
```

---

### Search

Bash:

```bash
curl -s "$BASE/api/v1/memory/search?user_id=<user-id>&query=coffee%20preference&limit=5"
```

PowerShell:

```powershell
curl.exe -s "$BASE/api/v1/memory/search?user_id=<user-id>&query=coffee%20preference&limit=5"
```

---

### Delete

Take the id from a search result, as the stale-entry rule describes.

Bash:

```bash
curl -s -X DELETE "$BASE/api/v1/memory?memory_id=<id-from-search>"
```

PowerShell:

```powershell
curl.exe -s -X DELETE "$BASE/api/v1/memory?memory_id=<id-from-search>"
```
