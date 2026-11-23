# Standards Checklist: Web

The standards checklist items for a diff that touches web code: components, pages, layouts, copy, locale handling, API modules or TypeScript types. Run them in Step 3, after the items in SKILL.md that every diff gets. Every item names the skill that owns the rule and its reasoning, so a finding can cite it.

---

### Web

- [ ] No user-facing string in code, admin pages, metadata titles, aria labels, placeholders and toasts included: every one is a key in each locale's catalogue, at least English plus the product's language. `react-patterns`
- [ ] Identifiers and catalogue keys are English, and no component, page or layout holds a locale literal such as `"pl"` or `"pl-PL"`: the locale comes from the one i18n config module with an environment-driven default. `react-patterns`
- [ ] The project's AST copy guard runs in lint, and new copy did not slip past it with a pragma outside tests. `react-patterns`
- [ ] API modules past the size limit are folders with one file per concern, and a barrel exists only where import paths or mocks need it. `coding-standards`
- [ ] No JSDoc explaining `T` and `D` where a descriptive type parameter such as `TRow` or `TDraft` would do. `coding-standards`
