# Unity Checklist

Run it before calling a Unity change done. The rules behind each item are in [SKILL.md](../SKILL.md).

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
