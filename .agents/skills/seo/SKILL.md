---
name: seo
description: 'Search visibility work across technical SEO, on-page optimisation, structured data, Core Web Vitals, keyword mapping and internal linking. Use when the user says "audit this site for SEO", "why is this page not indexed", "add schema markup to the product pages" or "map these keywords to URLs". Not for the performance work behind Core Web Vitals, use `performance-optimization`.'
license: Apache-2.0
---

# SEO

Improve search visibility through technical correctness, performance, and content relevance, not gimmicks. Every
recommendation here ties to a specific page or asset, because advice that names no URL cannot be implemented.

Written for search guidance built on mobile-first indexing and the Core Web Vitals set of LCP, INP, and CLS.

---

### When to activate

- Auditing crawlability, indexability, canonicals, or redirects.
- Improving title tags, meta descriptions, and heading structure.
- Adding or validating structured data.
- Diagnosing Core Web Vitals against search requirements.
- Doing keyword research and mapping keywords to URLs.
- Planning internal linking, sitemap, or robots changes.
- The user says "write titles and meta descriptions for these routes".

---

### When not to activate

- Profiling and fixing the performance problems behind a failing vital. Use `performance-optimization`.
- Implementing `generateMetadata`, sitemaps, or route handlers in Next.js. Use `nextjs-app-router-patterns`.
- Heading semantics for assistive technology rather than for crawlers. Use `web-accessibility`.
- Writing and structuring human-facing documentation. Use `markdown-writer`.
- API contract design. Use `api-design`.

---

### Reference files

| Task | Open |
| --- | --- |
| Crawlability and indexability definitions, keyword mapping steps, title shapes, schema types per page, and pass and fail examples for every rule | [references/seo-examples.md](references/seo-examples.md) |

---

### Rules

1. Fix technical blockers before content, in order: crawlability, indexability, performance, content.
2. Crawlable means `robots.txt` allows what matters, no unintended `noindex`, shallow click depth, redirect chains under three hops, and self-consistent, non-looping canonicals. Indexable means one URL format, correct hreflang, a sitemap matching the public surface, and no uncontrolled duplicates.
3. One primary keyword or theme maps to one URL. Map by intent, variants, priority, one theme per URL, then check for cannibalisation before publishing.
4. Titles run about 50 to 60 characters with the primary concept first (`Primary Topic - Specific Modifier | Brand`), descriptions about 120 to 160 characters describing the page honestly.
5. One `H1` per page, with heading levels following the content hierarchy, never font size.
6. Structured data describes only what the page renders, with the type matched to the page: organisation on the homepage, `Article` or `BlogPosting` on editorial, `Product` and `Offer` on products, `BreadcrumbList` on interior pages, `FAQPage` only for real questions and answers.
7. Treat the vitals as thresholds on field data at the 75th percentile: LCP under 2.5s, INP under 200ms, CLS under 0.1. Measurement and profiling belong to `performance-optimization`.
8. Internal anchors describe their destination. Link from strong pages to the pages you want to rank, and from new pages to relevant existing ones.
9. Every finding carries a severity, a file or URL, the issue, and a specific fix.

---

### Anti-patterns

| Anti-pattern | Fix |
| --- | --- |
| Keyword stuffing | Write for users first |
| Thin near-duplicate pages | Consolidate or differentiate them |
| Schema for content that is not on the page | Match schema to reality |
| Content advice without reading the page | Read the real page first |
| Generic "improve SEO" output | Tie every recommendation to a page or asset |
| Chasing a lab score past the thresholds | Measure field data at the 75th percentile |

---

### Related skills

- `nextjs-app-router-patterns` for `generateMetadata`, canonical URLs, sitemaps, and route handlers that serve them.
- `performance-optimization` for the profiling and remediation behind Core Web Vitals.
- `web-accessibility` for heading structure, alt text, and language attributes as assistive-technology requirements.
- `react-patterns` for the components that render the marked-up content.
- `frontend-design` for the marketing surfaces the copy sits on.
- `markdown-writer` for long-form content structure and an honest voice.

---

### Checklist

- No important page is blocked by `robots.txt` or carrying an unintended `noindex`.
- Every canonical is self-consistent and non-looping, and no redirect chain runs to three hops or more.
- The sitemap matches the intended public surface, and hreflang is correct where it exists.
- Each URL owns one primary intent, with no two pages competing for the same query.
- Every title is roughly 50 to 60 characters and every description roughly 120 to 160, written for a human reader.
- One `H1` per page, with heading levels following content rather than styling.
- Structured data describes content that is actually rendered.
- Field LCP, INP, and CLS clear their thresholds at the 75th percentile.
- Internal anchors describe their destination.
- Every finding names a file or URL, states the issue, and proposes a specific fix.
