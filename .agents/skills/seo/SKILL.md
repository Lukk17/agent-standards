---
name: seo
description: Search visibility work across technical SEO, on-page optimisation, structured data, Core Web Vitals, keyword mapping, and internal linking. Use when you say "audit this site for SEO", "why is this page not indexed", "add schema markup to the product pages", "write titles and meta descriptions for these routes", or "map these keywords to URLs". Not for the page performance work behind Core Web Vitals, use `performance-optimization`.
license: Apache-2.0
---

# SEO

Improve search visibility through technical correctness, performance, and content relevance, not gimmicks. Every
recommendation here ties to a specific page or asset, because advice that names no URL cannot be implemented.

Baseline: current stable search guidance, meaning mobile-first indexing and the Core Web Vitals set of LCP, INP, and
CLS.

---

### When to activate

- Auditing crawlability, indexability, canonicals, or redirects.
- Improving title tags, meta descriptions, and heading structure.
- Adding or validating structured data.
- Diagnosing Core Web Vitals against search requirements.
- Doing keyword research and mapping keywords to URLs.
- Planning internal linking, sitemap, or robots changes.

---

### When not to activate

- Profiling and fixing the performance problems behind a failing vital. Use `performance-optimization`.
- Implementing `generateMetadata`, sitemaps, or route handlers in Next.js. Use `nextjs-app-router-patterns`.
- Heading semantics for assistive technology rather than for crawlers. Use `web-accessibility`.
- Writing and structuring human-facing documentation. Use `markdown-writer`.
- API contract design. Use `api-design`.

---

### Fix technical blockers before touching content

A page that cannot be crawled or indexed gains nothing from a better title. Work the order: crawlability, then
indexability, then performance, then content.

```text
PASS: robots.txt allows /products/, the page returns 200, the canonical is self-referential, and it is in the
sitemap. Now the title is worth rewriting.
```

```text
FAIL: three days rewriting product copy on pages carrying noindex from a staging deploy.
```

Crawlability means `robots.txt` allows what matters and blocks low-value surfaces, no important page is
unintentionally `noindex`, important pages sit at a shallow click depth, redirect chains stay under three hops, and
canonicals are self-consistent and non-looping.

Indexability means one consistent URL format, correct hreflang where multilingual pages exist, sitemaps that reflect
the intended public surface, and no duplicate URLs competing without canonical control.

---

### Give each page one primary intent

Two pages targeting the same query compete with each other, and search engines pick one, usually not the one you
wanted. One primary keyword or theme maps to one URL.

```text
PASS: /guides/freight-insurance targets "freight insurance guide". /pricing targets "freight insurance pricing".
Different intent, different page, internal links between them.
```

```text
FAIL: /blog/freight-insurance, /guides/freight-insurance, and /freight-insurance-explained all target the same
query. Consolidate into one and redirect the rest.
```

Map keywords by defining the search intent, gathering realistic variants, prioritising by intent match, likely value,
and competition, assigning one primary theme per URL, then checking for cannibalisation before publishing.

---

### Write titles and descriptions for people

A title stuffed with keywords loses the click even when it ranks. Keep titles around 50 to 60 characters with the
primary concept near the front, and descriptions around 120 to 160 characters describing the page honestly.

```html
<!-- PASS: specific, legible, front-loaded -->
<title>Freight Insurance Pricing, Per Container and Per Route | Atlas</title>
<meta name="description" content="Compare per-container and per-route freight insurance rates, with a worked
example for a 40ft container from Gdansk to Rotterdam." />
```

```html
<!-- FAIL: stuffed, truncated, and identical to forty other pages -->
<title>Freight Insurance, Cheap Freight Insurance, Best Freight Insurance Rates Online 2026 | Atlas</title>
<meta name="description" content="Atlas is the best solution for all your needs." />
```

The shape that usually works is `Primary Topic - Specific Modifier | Brand` for a title, and action plus topic plus
value plus one supporting detail for a description.

---

### Keep headings tied to content, not to styling

One `H1` per page, with `H2` and `H3` reflecting the real hierarchy. Picking a heading level for its font size breaks
both the outline a crawler reads and the navigation a screen-reader user relies on.

```html
<!-- PASS: the outline matches the content -->
<h1>Freight insurance pricing</h1>
<h2>Per-container rates</h2>
<h3>Standard 40ft dry container</h3>
```

```html
<!-- FAIL: levels chosen by size, and a second H1 halfway down -->
<h1>Freight insurance pricing</h1>
<h4>Per-container rates</h4>
<h1>Contact us</h1>
```

---

### Emit structured data that matches the page

Schema describing content the page does not contain is a manual-action risk, not a shortcut to a rich result. Mark up
what is actually rendered.

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Freight Insurance Pricing Explained",
  "author": { "@type": "Person", "name": "Marta Nowak" },
  "publisher": { "@type": "Organization", "name": "Atlas" },
  "datePublished": "2026-04-12"
}
```

```json
{
  "@type": "FAQPage",
  "mainEntity": [{ "@type": "Question", "name": "Is this cheap?", "acceptedAnswer": { "text": "Yes" } }]
}
```

The second block is a failure when no such question and answer appear on the page. Match the type to the page:
organisation or business schema on the homepage, `Article` or `BlogPosting` on editorial pages, `Product` and `Offer`
on product pages, `BreadcrumbList` on interior pages, and `FAQPage` only when the content genuinely is a set of
questions and answers.

---

### Treat the vitals as thresholds, not scores

Three numbers decide the field assessment: LCP under 2.5s, INP under 200ms, CLS under 0.1. Chasing a synthetic score
past those thresholds buys nothing for search.

```text
PASS: LCP 2.1s after preloading the hero image and dropping a render-blocking font stylesheet. Measured on the
75th percentile of real traffic.
```

```text
FAIL: a lab score of 98 on a throttled desktop run, while field LCP sits at 4.3s on mobile.
```

Common fixes: preload the hero asset, cut render-blocking work, reserve layout space for images and embeds, and trim
the JavaScript that delays interaction. The measurement and profiling work belongs to `performance-optimization`.

---

### Link internally with descriptive anchors

Internal links pass relevance and tell a crawler what the target page is about. An anchor reading "click here" says
nothing about the destination, and reads just as badly aloud.

```html
<!-- PASS -->
<a href="/guides/freight-insurance">how freight insurance is priced</a>
```

```html
<!-- FAIL -->
<a href="/guides/freight-insurance">click here</a>
```

Link from strong pages to the pages you want to rank, and backfill links from new pages to relevant existing ones.

---

### Report findings against a real location

An audit finding without a file, a URL, and a fix cannot be actioned. Use this shape.

```text
[HIGH] Duplicate title tags on product pages
Location: src/routes/products/[slug].tsx
Issue: Dynamic titles collapse to the same default string, which weakens relevance and creates duplicate signals.
Fix: Generate a unique title per product using the product name and primary category.
```

```text
[HIGH] Improve SEO on the site
```

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
- Every canonical is self-consistent and non-looping, and no redirect chain runs past three hops.
- The sitemap matches the intended public surface, and hreflang is correct where it exists.
- Each URL owns one primary intent, with no two pages competing for the same query.
- Every title is roughly 50 to 60 characters and every description roughly 120 to 160, written for a human reader.
- One `H1` per page, with heading levels following content rather than styling.
- Structured data describes content that is actually rendered.
- Field LCP, INP, and CLS clear their thresholds at the 75th percentile.
- Internal anchors describe their destination.
- Every finding names a file or URL, states the issue, and proposes a specific fix.
