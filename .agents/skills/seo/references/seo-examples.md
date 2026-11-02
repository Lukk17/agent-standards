# SEO Rules in Depth

Contents:

- [Fix technical blockers before touching content](#fix-technical-blockers-before-touching-content)
- [Give each page one primary intent](#give-each-page-one-primary-intent)
- [Write titles and descriptions for people](#write-titles-and-descriptions-for-people)
- [Keep headings tied to content, not to styling](#keep-headings-tied-to-content-not-to-styling)
- [Emit structured data that matches the page](#emit-structured-data-that-matches-the-page)
- [Treat the vitals as thresholds, not scores](#treat-the-vitals-as-thresholds-not-scores)
- [Link internally with descriptive anchors](#link-internally-with-descriptive-anchors)
- [Report findings against a real location](#report-findings-against-a-real-location)

Companion reference for the [seo](../SKILL.md) skill. Load it for the definitions and the pass and fail examples behind each rule: technical blockers, one intent per page, titles and descriptions, headings, structured data, the vitals, internal links, and the finding format.

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
  "datePublished": "YYYY-MM-DD"
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
