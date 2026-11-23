# Scope

Companion reference for the [unity](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing a MonoBehaviour, a ScriptableObject, or gameplay C#.
- Chasing a frame-time spike, a GC pause, or a memory growth over a session.
- Loading, releasing, or organising assets and bundles.
- Deciding how systems talk to each other without direct references.
- Writing Edit Mode or Play Mode tests.
- Setting up the project's serialisation, LFS tracking, or build configuration.
- The user says "why does my game stutter every few seconds", "pool these bullets" or "load this asset with Addressables".

---

### When not to activate

- Engine-agnostic C# design, SOLID and error handling, use `coding-standards`. Unity-specific C# naming is owned here.
- Designing the backend a multiplayer or live-ops game talks to, use `backend-patterns`.
- Building the CI pipeline itself rather than the Unity build settings, use `deployment-patterns`.
- Writing the test strategy and coverage policy, use `tdd-workflow`.
- Profiling a non-Unity application, use `performance-optimization`.

---

### Related skills

- `coding-standards` for the C# design and naming floor underneath these rules.
- `tdd-workflow` for the test strategy the Unity Test Framework implements.
- `performance-optimization` for the measure-first method behind the frame-budget rules.
- `deployment-patterns` for the CI pipeline that runs the build matrix.
- `backend-patterns` for the services a live game talks to.
