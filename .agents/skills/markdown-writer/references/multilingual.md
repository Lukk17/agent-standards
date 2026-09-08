# Translated Copies of a Document

Rules for adding and maintaining a locale copy of a README or docs page without letting it drift from the source.
Load this file when the user asks for a translated document, or when an existing translation needs refreshing.

---

### File naming and the language switcher

Keep the English `README.md` as the canonical source and add locale-suffixed siblings using BCP-47 tags, for example
`README.es.md`, `README.zh-CN.md`, `README.pt-BR.md`. Put a one-line language switcher at the very top of every
variant, linking across all locales, and put the same line in the canonical file.

---

### What to translate

Translate prose, headings, badge alt text, table headers, and status labels.

Leave untranslated:

- Code inside fenced blocks
- File paths, environment variable names and CLI flags
- Mermaid node labels that carry an identifier, such as a port number, class name or package path, translating only
  the natural-language labels in a diagram
- URL fragments and anchors
- shields.io badge query strings, whose visible text is URL-encoded ASCII

---

### Anchors

Most hosts build a heading anchor from the heading text, so translating a heading breaks every in-document link that
pointed at it. Two repairs work. Rewrite all in-document anchor links to the localized slug, or insert an explicit
anchor element above the translated heading so the original English anchor still resolves.

Prefer the explicit anchor. It lets the English document link into the translation without knowing the locale.

---

### Drift control

End every translated file with a footer naming the source and the commit it was translated from, and stating that the
English version wins when the two disagree.

```text
Translated from README.md at commit <sha>. If they diverge, the English version is authoritative.
```

On any future change to the canonical document, refresh the same sections in every locale file in the same commit. A
translation updated one commit later is a translation nobody trusts.
