# Source Order

The tiers in the order to try them, what each one is good and bad at, and the command that queries it. Load this
file when picking where to look next or when a tier returns nothing useful.

---

### Check the toolbox first

Before the first query, check which research tools this session has: the Context7 MCP server, a web fetch, a web
search, `gh`, and `curl`. Name any missing one in the first line of the reply, with the route used instead. Note
whether a Firecrawl or Exa MCP server is also connected, but do not report either as missing, because both are
optional extras covered at the end of this file.

Pass:

```text
No web search in this session. Using Context7 for the SDK docs and gh api for the release notes instead.
```

Fail:

```text
Search is unavailable, so going by what I know: the option was added in version 4.
```

When the check touches environment variables, for example to see whether an API key or a service URL is set, list
the names only and never the values. A value can be a token or a password, and whatever a command prints ends up in
the session log and the transcript. Filter the name list for the one you need rather than printing a variable to see
whether it exists.

```bash
compgen -e
```

```powershell
(Get-ChildItem Env:).Name
```

Pass:

```text
compgen -e | grep CONTEXT7 printed CONTEXT7_API_KEY, so the key is set. Its value was never printed.
```

Fail:

```text
Ran env to see what is configured, and the output included the full value of GITHUB_TOKEN.
```

---

### The tiers at a glance

| Tier | Source | What it settles |
|---|---|---|
| 1 | Context7 MCP (`resolve-library-id`, then `query-docs`) | Library and tool API, configuration, usage |
| 2 | Vendor documentation and product pages | Supported behaviour, limits, pricing as the vendor states it |
| 3 | Vendor source code (`gh api`, raw GitHub) | What the code actually does, schema field names, defaults |
| 4 | Changelogs and release notes | When a behaviour arrived, changed or was removed |
| 5 | Issue trackers | Known bugs, their status, the version that fixed them |
| 6 | Community: forums, Reddit, GitHub discussions, blogs, Stack Overflow | Workarounds, real-world practice, quirks |
| 7 | Sector and industry pages, standards bodies | Regulation, specifications, industry norms |
| 8 | General web search | Anything the tiers above did not reach |

Search engines surface pages written to rank above the vendor page, so open the vendor or the original even when it
sits lower in the results. Start with a short broad query to see what exists, then target the page that decides.

---

### Read raw text for anything load-bearing

Some fetch tools do not hand the page to the agent. They pass it through a smaller model and return that model's
answer, which can compress, merge two figures, or invent a detail. Claude Code's own tool description says its web
fetch "answers `prompt` against it using a small fast model". For a quote, a number, or a verdict, fetch the raw
text and read it: `curl` the page, read the docs source on GitHub, or strip the HTML with a text extractor. Use the
summarising fetch for orientation only. A page that renders only with JavaScript goes to `ascend-web-hunter`.

```bash
curl -sL https://example.dev/docs/page
```

Community report behind this rule (r/ClaudeAI, 2026-08-08, 80 comments): a user found fabricated statistics and a
framework name absent from the cited paper, switched subagents to raw `curl`, and caught 17 errors across about 30
papers. https://www.reddit.com/r/ClaudeAI/comments/1vim8b7/psa_be_careful_letting_claude_use_webfetch_for/

---

### Tier 1: Context7 MCP

Context7 serves current, version-specific documentation for libraries and tools. Resolve the name to a library ID
first, then query with the question itself rather than a keyword. Name the version in the query when it matters.

```text
resolve-library-id  libraryName="fastapi"
query-docs  libraryId="/fastapi/fastapi"  query="how to declare a lifespan handler"
```

Good at: API signatures, configuration keys, usage examples. Weak at: pricing, limits, very recent releases, and
anything the vendor documents outside its main docs. When it returns nothing or an old version, move to tier 2.

---

### Tier 2: Vendor documentation and product pages

Fetch the page itself, not a search result snippet about it. Record the heading of the section you quote and the
date the page says it was updated, if it shows one. For exact wording, fetch the raw source of the docs where the
vendor publishes it on GitHub, because a summarising fetch tool can paraphrase.

---

### Tier 3: Vendor source code

The code is the ground truth for defaults, field names, and what happens on an error. Read it at the released tag,
not the default branch, when the question is about a released version.

```bash
gh api repos/OWNER/REPO/contents/PATH?ref=TAG --jq .content
```

```bash
gh search code fieldName --repo OWNER/REPO
```

```bash
curl -sL https://raw.githubusercontent.com/OWNER/REPO/TAG/PATH
```

The `.content` field is base64, so decode it before reading.

---

### Tier 4: Changelogs and release notes

These answer when: when a behaviour arrived, changed, or was removed. Match the version the user actually runs.

```bash
gh release list --repo OWNER/REPO --limit 10
```

```bash
gh release view TAG --repo OWNER/REPO
```

For a package registry, ask the registry for the current version rather than trusting a page.

```bash
npm view PACKAGE version
```

```bash
pip index versions PACKAGE
```

---

### Tier 5: Issue trackers

Search without a state filter so open and closed issues both come back, then read the thread to the end, because
the fix, the workaround and the reason it was closed are usually in the last comments. Record the state and the
state reason.

```bash
gh search issues "error text" --repo OWNER/REPO --limit 20
```

```bash
gh issue view NUMBER --repo OWNER/REPO --comments
```

Closed as completed with a linked pull request usually means fixed, so find the release that contains it. Closed as
not planned means the behaviour stays, so the workaround is the answer.

---

### Tier 6: Community sources

Forums, Reddit, GitHub discussions, blog posts and Stack Overflow show how people actually use a tool, which
workarounds hold up, and which quirks the docs never mention. Every item from this tier is labelled community, dated,
and cross-checked against a primary source or a second independent report before it carries a claim. Stack Overflow
answers age fast: check the answer date against the version in question.

Some sites refuse unauthenticated automated requests. Measure the refusal (the status code) rather than assuming it,
then try another route, such as a search restricted to that site, the Hacker News search API, or `ascend-web-hunter`.

```bash
curl -s "https://hn.algolia.com/api/v1/search?query=QUERY&tags=story"
```

Reddit answered its JSON API with 403 and its RSS feeds with 200 when measured on 2026-09-24, and it rate limits
unauthenticated readers to roughly one request every few seconds (`x-ratelimit-remaining: 0` on a 429). Space the
requests and read a thread with its top comments through the feed.

```bash
curl -s -A "Mozilla/5.0" "https://www.reddit.com/r/SUBREDDIT/search.rss?q=QUERY&restrict_sr=1&sort=top&t=year"
```

```bash
curl -s -A "Mozilla/5.0" "https://www.reddit.com/r/SUBREDDIT/comments/ID/SLUG/.rss?sort=top&limit=12"
```

```bash
gh api graphql -f query='{ search(query: "QUERY repo:OWNER/REPO", type: DISCUSSION, first: 10) { nodes { ... on Discussion { title url answer { url } } } } }'
```

---

### Tier 7: Sector and industry pages, standards

Use when the question has a regulatory, legal, or specification side: a standards body (IETF, W3C, ISO, NIST), a
regulator, an industry association. Quote the clause number with the sentence, and note the edition or revision.

---

### Tier 8: General web search

The last resort, and the most exposed to content written to rank rather than to inform. Use it to find a primary
source you did not know existed, then go and read that source. A search result snippet is never evidence on its own.

---

### Pages that block fetching

A WAF interstitial, a CAPTCHA, a login wall, or a page that renders only in a browser goes to `ascend-web-hunter`.
Report that the page was reached through it, so the reader knows the route.

---

### Optional search tools: Firecrawl and Exa MCP

Use these only when the session already has the server connected. They are routes, not tiers: a search through
either one is still tier 8, so its results point at a primary source you then read, and a scrape through either one
is a way to get the page text for tiers 2 to 7. Never add a server or an API key to a configuration file just to run
one query.

| Server | Tool | Use it for |
|---|---|---|
| Firecrawl | `firecrawl_search` | Ranked web results from a query, with page content only when `scrapeOptions` is set |
| Firecrawl | `firecrawl_scrape` | One known URL, returned as markdown or as JSON against a schema you supply |
| Firecrawl | `firecrawl_crawl` | Many pages under one site, bounded with `limit` and path filters |
| Exa | `web_search_exa` | Web search that returns page content with each result |
| Exa | `web_fetch_exa` | The full content of one or more URLs as markdown |
| Exa | `web_search_advanced_exa` | Search filtered by domain and date, off by default and enabled through the `tools` URL parameter |

Firecrawl documents its JSON format as the preferred one, but that format extracts fields rather than returning the
page. For a quote, a number or a verdict, request markdown and read it, the same raw-text rule as above. Exa's
date filters make it a good route to the newest sources when recency decides the question.

Exa's hosted server accepts an API key on the URL as `?exaApiKey=`. Authenticate with OAuth or a header set from the
environment instead, because a key in a URL lands in a configuration file and in logs.

Tool names as documented on 2026-09-25 in https://github.com/firecrawl/firecrawl-mcp-server (section "When to Use
This Server") and https://github.com/exa-labs/exa-mcp-server (section "Available Tools"). Older guides name Exa's
fetch tool `crawling_exa`, which the current README no longer lists, so check the connected server's own tool list
before calling one.
