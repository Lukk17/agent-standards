# Exa MCP

An optional search and fetch route. Load this file only when the session already has an Exa MCP server connected.

---

### A route, not a tier

Use Exa only when the session already has the server connected. It is a route, not a tier: a search through it is still tier 8 in [source-order.md](source-order.md), so its results point at a primary source you then read, and a scrape through it is a way to get the page text for tiers 2 to 7. Never add a server or an API key to a configuration file just to run one query. Exa is an optional extra, so never report it as a missing research tool.

---

### Tools

| Tool | Use it for |
|---|---|
| `web_search_exa` | Web search that returns page content with each result |
| `web_fetch_exa` | The full content of one or more URLs as markdown |
| `web_search_advanced_exa` | Search filtered by domain and date, off by default and enabled through the `tools` URL parameter |

Exa's date filters make it a good route to the newest sources when recency decides the question.

Exa's hosted server accepts an API key on the URL as `?exaApiKey=`. Authenticate with OAuth or a header set from the environment instead, because a key in a URL lands in a configuration file and in logs.

Tool names as documented in https://github.com/exa-labs/exa-mcp-server (section "Available Tools"). Older guides name Exa's fetch tool `crawling_exa`, which the current README no longer lists, so check the connected server's own tool list before calling one.
