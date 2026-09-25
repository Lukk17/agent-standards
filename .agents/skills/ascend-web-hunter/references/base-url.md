# Base URL Resolution

The commands behind the base-URL rule in the manifest. Load this file when resolving `$BASE` before the first call.

---

### Order

1. `ASCEND_WEB_HUNTER_URL`, when set, is the base URL and no probe runs.
2. `http://ascend-web-hunter.internal`, the service name on a shared network.
3. `http://localhost:7021`, the port the local compose file publishes, with `/health` and `/ready` on it.

A candidate counts only when `GET /health` answers with a success status inside a short timeout. When no candidate
answers, stop and tell the user the service is down, naming the candidates tried. A silent switch to a normal fetch
hides the outage and returns the partial or blocked page this service exists to avoid.

---

### Bash

```bash
BASE="${ASCEND_WEB_HUNTER_URL:-}"; if [ -z "$BASE" ]; then for candidate in http://ascend-web-hunter.internal http://localhost:7021; do curl -sf --max-time 3 "$candidate/health" >/dev/null && BASE="$candidate" && break; done; fi
```

An empty `$BASE` afterwards means the service is down. A set `ASCEND_WEB_HUNTER_URL` is used as given, without
probing the other candidates, so a request that fails against it is reported against that URL.

---

### PowerShell

```powershell
$BASE = if ($env:ASCEND_WEB_HUNTER_URL) { $env:ASCEND_WEB_HUNTER_URL } else { 'http://ascend-web-hunter.internal', 'http://localhost:7021' | Where-Object { try { Invoke-WebRequest "$_/health" -TimeoutSec 3 -ErrorAction Stop | Out-Null; $true } catch { $false } } | Select-Object -First 1 }
```

An empty `$BASE` means the service is down.
