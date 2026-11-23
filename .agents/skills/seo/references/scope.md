# Scope

Companion reference for the [seo](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Auditing crawlability, indexability, canonicals, or redirects.
- Improving title tags, meta descriptions, and heading structure.
- Adding or validating structured data.
- Diagnosing Core Web Vitals against search requirements.
- Doing keyword research and mapping keywords to URLs.
- Planning internal linking, sitemap, or robots changes.
- The user says "audit this site for SEO", "why is this page not indexed", "add schema markup to the product pages", "map these keywords to URLs" or "write titles and meta descriptions for these routes".

---

### When not to activate

- Profiling and fixing the performance problems behind a failing vital. Use `performance-optimization`.
- Implementing `generateMetadata`, sitemaps, or route handlers in Next.js. Use `nextjs-app-router-patterns`.
- Heading semantics for assistive technology rather than for crawlers. Use `web-accessibility`.
- Writing and structuring human-facing documentation. Use `markdown-writer`.
- API contract design. Use `api-design`.

---

### Related skills

- `nextjs-app-router-patterns` for `generateMetadata`, canonical URLs, sitemaps, and route handlers that serve them.
- `performance-optimization` for the profiling and remediation behind Core Web Vitals.
- `web-accessibility` for heading structure, alt text, and language attributes as assistive-technology requirements.
- `react-patterns` for the components that render the marked-up content.
- `frontend-design` for the marketing surfaces the copy sits on.
- `markdown-writer` for long-form content structure and an honest voice.
