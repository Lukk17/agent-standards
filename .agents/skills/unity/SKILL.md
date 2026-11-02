---
name: unity
description: Unity and C# standards for allocation-free per-frame code, object pooling, Addressables load and release pairing, cached component lookups, ScriptableObject architecture and the Unity Test Framework. Use when the user says "why does my game stutter every few seconds", "pool these bullets" or "load this asset with Addressables". Not for engine-agnostic C# and SOLID rules, use `coding-standards`.
---

# Unity Game Development Standards

How a Unity project keeps a stable frame time and stays testable: nothing allocates in the per-frame path, nothing is looked up by search at runtime, and configuration lives in assets rather than in code. Most Unity stutter is a garbage collection pause caused by a single allocating line inside `Update`.

Written for Unity 6 LTS, with the Addressables, Input System, and Test Framework packages that ship for it.

| Task | Open |
|---|---|
| The Pass and Fail code behind any rule below, and the reasoning behind each rule | [references/rules-and-examples.md](references/rules-and-examples.md) |
| Full ScriptableObject data-container and event-channel examples, and Edit Mode versus Play Mode test structure | [references/architecture-and-testing.md](references/architecture-and-testing.md) |
| Git and LFS setup, serialisation mode, IL2CPP and stripping, the CI build matrix, the Input System, and UI Toolkit versus UGUI | [references/project-and-build.md](references/project-and-build.md) |

---

### When to activate

- Writing or reviewing a MonoBehaviour, a ScriptableObject, or gameplay C#.
- Chasing a frame-time spike, a GC pause, or a memory growth over a session.
- Loading, releasing, or organising assets and bundles.
- Deciding how systems talk to each other without direct references.
- Writing Edit Mode or Play Mode tests.
- Setting up the project's serialisation, LFS tracking, or build configuration.

---

### When not to activate

- Engine-agnostic C# design, SOLID and error handling, use `coding-standards`. Unity-specific C# naming is owned here.
- Designing the backend a multiplayer or live-ops game talks to, use `backend-patterns`.
- Building the CI pipeline itself rather than the Unity build settings, use `deployment-patterns`.
- Writing the test strategy and coverage policy, use `tdd-workflow`.
- Profiling a non-Unity application, use `performance-optimization`.

---

### Rules

1. Nothing allocates in `Update`, `FixedUpdate` or `LateUpdate`, because the collector running mid-frame is the stutter. Build strings with a reused `StringBuilder`, never with `+` in a loop.
2. Use `GarbageCollector.GCMode.Manual` only for a critical, predictable segment with a bounded allocation budget, such as a racing lap, and always re-enable incremental GC afterwards, or the OS may kill the process for memory pressure.
3. No `Instantiate` or `Destroy` during gameplay. Pre-warm a pool at scene load, activate out of it, and release by deactivating and returning to the pool. An empty pool is a sizing defect: log it and raise the pool size, never fall back to `Instantiate`.
4. No `Resources.Load`, which pulls its whole folder into the build. Use Addressables and pair every `LoadAssetAsync` with a `Release`, so the reference count reaches zero and the bundle unloads.
5. Organise Addressables groups by load context (`UI`, `Level_01`, `Shared_Audio`), so a download is scoped to what the player is about to need and content updates stay incremental.
6. `GetComponent<T>()`, `FindFirstObjectByType<T>()` and `FindAnyObjectByType<T>()` are searches: run them once in `Awake` or `Start` and hold the reference. `FindObjectOfType<T>()` is deprecated in Unity 6, so use `FindFirstObjectByType<T>()`, or the faster `FindAnyObjectByType<T>()` when any instance will do.
7. Keep heavy initialisation out of `Awake` unless it is synchronous and fast, and defer the rest to `Start` or an async path. Null-check a cached reference in `OnEnable` where the component can be destroyed and re-enabled, because it does not survive a scene reload.
8. Producers (input, physics results) run before consumers. Set the order with `[DefaultExecutionOrder]` or Project Settings, Script Execution Order, one of the two and never neither, or a one-frame lag shows up under load.
9. Use the `NonAlloc` physics queries with a field-level buffer, never `Physics.RaycastAll`. Set both with `Transform.SetPositionAndRotation()` rather than two assignments, and pass custom structs in tight math loops by `ref` or `in`.
10. A `MonoBehaviour` class name matches its filename exactly, or Unity cannot bind the script. Expose Inspector fields with `[SerializeField] private`, never a public field.
11. Wrap every script in a project namespace such as `MyGame.Core`. Private fields are `_camelCase`, public properties `PascalCase`, constants and `static readonly` `PascalCase` rather than `UPPER_SNAKE_CASE`, interfaces prefixed `I`, abstract bases prefixed `Base`.
12. Put configuration in ScriptableObject assets so a designer tunes it without a recompile, and decouple systems with ScriptableObject event channels instead of direct references or static events.
13. Never store runtime mutable state in a ScriptableObject: it persists between Play Mode sessions in the Editor and produces a bug that only reproduces on the second run.
14. Tests live in a dedicated `Tests/` assembly definition. Edit Mode covers pure logic, ScriptableObject configuration, utilities and data validation. Play Mode covers gameplay, physics, coroutines, component lifecycle and integration.
15. Mock through interfaces and hand-written doubles, and build a minimal scene per test rather than loading a production one, which breaks whenever a designer moves something.

---

### Doc Comments

XML doc comments follow "Doc Comments" in `coding-standards`. The C# delta: keep `<summary>` on one physical line, because the expanded three-line form says no more, write `<exception>` for every exception a caller can act on, since C# keeps throwing out of the signature, and use `<param>` for pool ownership, whether the caller must return the object to the pool being exactly the kind of fact the signature cannot carry.

---

### Related skills

- `coding-standards` for the C# design and naming floor underneath these rules.
- `tdd-workflow` for the test strategy the Unity Test Framework implements.
- `performance-optimization` for the measure-first method behind the frame-budget rules.
- `deployment-patterns` for the CI pipeline that runs the build matrix.
- `backend-patterns` for the services a live game talks to.

---

### Checklist

- [ ] No managed allocation in `Update`, `FixedUpdate`, or `LateUpdate`.
- [ ] No string concatenation in a per-frame or tight loop.
- [ ] Runtime spawning goes through a pre-warmed pool, no `Instantiate` or `Destroy` in gameplay.
- [ ] No `Resources.Load`, and every `LoadAssetAsync` has a matching `Release`.
- [ ] Every `GetComponent`, `FindFirstObjectByType` and `FindAnyObjectByType` cached in `Awake` or `Start`.
- [ ] Producer systems ordered ahead of consumers with `[DefaultExecutionOrder]` or the project setting.
- [ ] `NonAlloc` physics queries with a field-level buffer.
- [ ] Inspector fields are `[SerializeField] private`, every script in a project namespace.
- [ ] Configuration lives in ScriptableObjects, no runtime mutable state in them.
- [ ] Tests sit in their own assembly definition and build their own minimal scenes.
