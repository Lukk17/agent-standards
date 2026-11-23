# UI Toolkit and UGUI

Which of the two UI systems a screen uses. Open this when starting a screen, an editor window or an in-world label. The rules for per-frame code live in [SKILL.md](../SKILL.md).

---

### UI Toolkit or UGUI

Use UI Toolkit (`UIElements`) for all new editor tooling and custom Editor windows, and for runtime UI in new
Unity 6 projects.

Use UGUI (`Canvas`-based) for in-world spatial UI, a health bar above a character or a world-space label, and for
extending a legacy UGUI system where a full rewrite is not justified.

Do not mix the two in one screen context. Choose one system per context and record the choice. Define all visual
styles in USS files rather than inline in C#, so a designer can change them without a recompile.
