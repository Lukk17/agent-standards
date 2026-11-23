---
name: unity
description: 'Unity and C# standards: allocation-free frames, pooling, asset loading, ScriptableObjects. Use when the user says "why does my game stutter" or "pool these bullets". Not for plain C#, use `coding-standards`.'
metadata:
  version: "1.1.0"
---

# Unity Game Development Standards

How a Unity project keeps a stable frame time and stays testable: nothing allocates in the per-frame path, nothing is looked up by search at runtime, and configuration lives in assets rather than in code. Most Unity stutter is a garbage collection pause caused by a single allocating line inside `Update`.

Written for Unity 6 LTS, with the Addressables, Input System, and Test Framework packages that ship for it.

---

### When not to activate

- Engine-agnostic C# design, SOLID and error handling, use `coding-standards`. Unity-specific C# naming is owned here.
- Designing the backend a multiplayer or live-ops game talks to, use `backend-patterns`.
- Writing the test strategy and coverage policy, use `tdd-workflow`.

---

### Rules

1. Nothing allocates in `Update`, `FixedUpdate` or `LateUpdate`, because the collector running mid-frame is the stutter. Build strings with a reused `StringBuilder`, never with `+` in a loop.
2. Switch the collector to manual only for a critical, predictable segment with a bounded allocation budget, and always re-enable incremental collection afterwards.
3. No `Instantiate` or `Destroy` during gameplay. Pre-warm a pool at scene load, activate out of it, and release by returning to it. An empty pool is a sizing defect, never a reason to fall back to `Instantiate`.
4. No `Resources.Load`. Load assets by address, pair every load with a release so the bundle unloads, and group assets by load context.
5. A component lookup or an object search runs once in `Awake` or `Start`, and the reference is held. Keep heavy initialisation out of `Awake`.
6. Producers (input, physics results) run before consumers. Set the order with `[DefaultExecutionOrder]` or the Script Execution Order setting, one of the two and never neither.
7. Use the `NonAlloc` physics queries with a field-level buffer, set position and rotation in one call, and pass custom structs in tight math loops by `ref` or `in`.
8. A `MonoBehaviour` class name matches its filename exactly, or Unity cannot bind the script. Expose Inspector fields with `[SerializeField] private`, never a public field.
9. Wrap every script in a project namespace. Private fields are `_camelCase`, public properties `PascalCase`, constants and `static readonly` `PascalCase`, interfaces prefixed `I`, abstract bases prefixed `Base`.
10. Put configuration in ScriptableObject assets and decouple systems with ScriptableObject event channels. Never store runtime mutable state in one.
11. Tests live in a dedicated `Tests/` assembly definition. Mock through interfaces and hand-written doubles, and build a minimal scene per test.
12. XML doc comments follow "Doc Comments" in `coding-standards`: `<summary>` on one physical line, `<exception>` for every exception a caller can act on, and `<param>` for pool ownership.

---

### Reference files

| Open this | When |
| --- | --- |
| [rules-and-examples.md](references/rules-and-examples.md) | A rule above needs its Pass and Fail code or its reasoning. |
| [addressables.md](references/addressables.md) | Loading, releasing or grouping assets with Addressables. |
| [test-framework.md](references/test-framework.md) | Writing Edit Mode or Play Mode tests with the Unity Test Framework. |
| [input-system.md](references/input-system.md) | Reading player input or adding an input action. |
| [ui-toolkit-and-ugui.md](references/ui-toolkit-and-ugui.md) | Choosing between UI Toolkit and UGUI for a screen. |
| [project-and-build.md](references/project-and-build.md) | Git and LFS setup, serialisation mode, IL2CPP and stripping, the CI build matrix. |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job. |
| [checklist.md](references/checklist.md) | Before calling a Unity change done. |
