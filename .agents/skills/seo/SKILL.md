---
name: seo
description: 'Technical and on-page SEO, structured data, keyword mapping and internal links. Use when the user says "audit this site for SEO" or "why is this page not indexed". Not for speed fixes, use `performance-optimization`.'
license: Apache-2.0
metadata:
  version: "1.1.0"
---

# SEO

Improve search visibility through technical correctness, performance, and content relevance, not gimmicks. Every recommendation here ties to a specific page or asset, because advice that names no URL cannot be implemented.

Written for search guidance built on mobile-first indexing and the Core Web Vitals set of LCP, INP, and CLS.

---

### When not to activate

- Profiling and fixing the performance problems behind a failing vital, use `performance-optimization`.
- Implementing `generateMetadata`, sitemaps or route handlers in Next.js, use `nextjs-app-router-patterns`.
- Heading semantics for assistive technology rather than for crawlers, use `web-accessibility`.

---

### Rules

1. Fix technical blockers before content, in order: crawlability, indexability, performance, content.
2. Crawlable means `robots.txt` allows what matters, no unintended `noindex`, shallow click depth, redirect chains under three hops, and self-consistent, non-looping canonicals. Indexable means one URL format, correct hreflang, a sitemap matching the public surface, and no uncontrolled duplicates.
3. One primary keyword or theme maps to one URL. Map by intent, variants, priority, one theme per URL, then check for cannibalisation before publishing. Consolidate or differentiate thin near-duplicate pages.
4. Titles run about 50 to 60 characters with the primary concept first (`Primary Topic - Specific Modifier | Brand`), descriptions about 120 to 160 characters describing the page honestly. Write for users first, never stuff keywords.
5. One `H1` per page, with heading levels following the content hierarchy, never font size.
6. Structured data describes only what the page renders, with the schema type matched to the page, and `FAQPage` only for real questions and answers.
7. Treat the vitals as thresholds on field data at the 75th percentile: LCP under 2.5s, INP under 200ms, CLS under 0.1. Measurement and profiling belong to `performance-optimization`.
8. Internal anchors describe their destination. Link from strong pages to the pages you want to rank, and from new pages to relevant existing ones.
9. Read the real page before advising on its content. Every finding carries a severity, a file or URL, the issue, and a specific fix.

---

### Reference files

| Task | Open |
| --- | --- |
| Crawlability and indexability definitions, keyword mapping steps, title shapes, schema types per page, pass and fail examples for every rule, and the anti-pattern table | [references/seo-examples.md](references/seo-examples.md) |
| Before calling an SEO audit or an SEO change done | [references/checklist.md](references/checklist.md) |
