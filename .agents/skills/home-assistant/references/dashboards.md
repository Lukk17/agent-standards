# Dashboards

Companion reference for the [home-assistant](../SKILL.md) skill. Load it to build or change a dashboard, to choose cards, or to check a dashboard after an entity rename.

VERIFIED means read in the Home Assistant documentation source, github.com/home-assistant/home-assistant.io on branch `current`, in the file named. UNVERIFIED means taken from the best-practices skill that the ha-mcp server ships, `home-assistant-best-practices` in homeassistant-ai/skills, and not checked against a primary source.

---

### Layout

1. Use the sections view, which is the default view type. VERIFIED, `source/_dashboards/sections.markdown`, titled "Sections (default)". Masonry, panel and sidebar views remain for special cases.
2. Start each section with a heading card instead of a section `title`. A new section gets one by itself. VERIFIED, same file: "A heading card will be automatically added to the top of the section." That the section `title` is deprecated is UNVERIFIED.
3. Use tile cards as the main card type, in place of the older entity, light and climate cards. UNVERIFIED.
4. Size a card with its `grid_options` (`columns` and `rows`) on the 12-column section grid. `layout_options` is the old key. UNVERIFIED.
5. Split a large home into several views with explicit `path` values, and use `subview: true` with a `back_path` for a drill-down, rather than one long page. UNVERIFIED.
6. Prefer the built-in cards. A HACS card is one more piece of code to keep working through upgrades, so add one only when no built-in card does the job, and record it the way [operations.md](operations.md) records a HACS integration.

---

### Strategy dashboards

The generated Overview dashboard is a strategy dashboard: its stored config holds a `strategy:` key and no cards. To edit its cards, take control of it first from its menu, which turns it into a normal dashboard that no longer follows new entities and areas, and cannot be undone. Ask the user before taking control. UNVERIFIED.

---

### Writing a dashboard

1. A new dashboard `url_path` needs a hyphen, such as `my-home`. UNVERIFIED.
2. A dashboard edited in the UI lives in storage and changes only through the Lovelace WebSocket calls `lovelace/config` and `lovelace/config/save`, never by editing `.storage/lovelace*` by hand. Read the config first and keep it, so writing it back is the undo. UNVERIFIED for the call names.
3. Every entity reference uses the full entity ID, `light.living_room`, not `living_room`. UNVERIFIED.
4. A tile feature works only on its own domain, for example `light-brightness` only on a `light`. UNVERIFIED.
5. A custom card served from `/local/` is cached by the browser, so change a version query on the resource URL, such as `?v=2`, after updating the file. UNVERIFIED.

---

### After a rename

An entity registry rename does not update a dashboard edited in the UI. Search the whole dashboard config, not only the cards: badges, the view header and footer, `tap_action` and `hold_action`, conditional cards and Markdown card templates all hold entity IDs. The full rename steps are in [renames-and-refactoring.md](renames-and-refactoring.md). UNVERIFIED.

---

### Looking at the result

Render the dashboard and look at it instead of reasoning about the JSON. Use a screenshot tool of the connected MCP server when it has one, or a browser on `<base-url>/<url-path>`. Read the base address from the instance and never assume port 8123. Charts fill in a few seconds after the page loads, so wait before calling one broken. UNVERIFIED.
