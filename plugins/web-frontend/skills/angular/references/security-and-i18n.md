# Security and Internationalisation

Sanitisation, content security policy, and translation-ready templates.

---

### Do not bypass sanitisation

Angular sanitises interpolated HTML, URLs, and styles by default. `bypassSecurityTrustHtml` turns that off for the
value you pass it, which makes any untrusted content in that value a cross-site scripting hole.

```typescript
// PASS: server-generated, sanitised at the source, and the reason is recorded in the module docs
readonly article = computed(() =>
  this.sanitizer.bypassSecurityTrustHtml(this.cms.renderedHtml())
);
```

```typescript
// FAIL: user-submitted content trusted verbatim
readonly comment = this.sanitizer.bypassSecurityTrustHtml(this.userInput);
```

Bypass only when the content is generated exclusively server-side and sanitised there. Reach for `DomSanitizer` on a
URL or style binding only when nothing else works, and record why in that module's own documentation rather than in a
source comment.

---

### Set a content security policy

Angular's template compiler emits CSP-compatible code when a nonce is configured, so a strict policy is achievable
without `unsafe-inline`.

```text
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{RANDOM}'; style-src 'self' 'nonce-{RANDOM}'
```

Generate the nonce per response on the server, pass it to the application through the `ngCspNonce` attribute on the
root element, and never reuse one across requests.

---

### Extract every user-visible string

A literal in a template cannot be translated and cannot be changed without a code deploy. Use `@angular/localize`
with `i18n` attributes for static text and `$localize` tagged templates in TypeScript.

```html
<!-- PASS: extractable, with a description for the translator -->
<h1 i18n="@@dashboard.title">Your dashboard</h1>
<button i18n="Action on the profile form|@@profile.save">Save</button>
```

```html
<!-- FAIL: nothing to extract, nothing to translate -->
<h1>Your dashboard</h1>
```

```typescript
// PASS: the same rule applies in component code
const message = $localize`:@@cart.empty:Your cart is empty`;
```

Give every message a stable custom id (`@@id`). Without one the id is derived from the source text, so fixing a typo
in English silently orphans every translation of that string.

Locale-specific builds are the default with `@angular/localize`. When the product genuinely needs runtime language
switching without a reload, add `ngx-translate` alongside it rather than replacing it.

Format numbers, dates, and currency through the built-in pipes or `Intl`, never by hand.

```html
<!-- PASS -->
<p>{{ total | currency: 'EUR' }}</p>
```

```html
<!-- FAIL: a currency symbol and a decimal separator that are wrong in most locales -->
<p>€{{ total }}</p>
```

Layout has to survive translation too. Leave room for strings to grow and use CSS logical properties so a
right-to-left locale mirrors correctly. See `web-accessibility` for the full rule.
