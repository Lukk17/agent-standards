# Firecrawl MCP

An optional search and scrape route. Load this file only when the session already has a Firecrawl MCP server connected.

---

### A route, not a tier

Use Firecrawl only when the session already has the server connected. It is a route, not a tier: a search through it is still tier 8 in [source-order.md](source-order.md), so its results point at a primary source you then read, and a scrape through it is a way to get the page text for tiers 2 to 7. Never add a server or an API key to a configuration file just to run one query. Firecrawl is an optional extra, so never report it as a missing research tool.

---

### Tools

| Tool | Use it for |
|---|---|
| `firecrawl_search` | Ranked web results from a query, with page content only when `scrapeOptions` is set |
| `firecrawl_scrape` | One known URL, returned as markdown or as JSON against a schema you supply |
| `firecrawl_crawl` | Many pages under one site, bounded with `limit` and path filters |

Firecrawl documents its JSON format as the preferred one, but that format extracts fields rather than returning the page. For a quote, a number or a verdict, request markdown and read it, the same raw-text rule as in [source-order.md](source-order.md).

Tool names as documented in https://github.com/firecrawl/firecrawl-mcp-server (section "When to Use This Server"). Check the connected server's own tool list before calling one.
