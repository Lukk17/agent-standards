---
name: unity
description: Unity and C# standards for allocation-free per-frame code, object pooling, Addressables load and release pairing, cached component lookups, script execution order, ScriptableObject architecture, and the Unity Test Framework. Use when you say "why does my game stutter every few seconds", "pool these bullets", "load this asset with Addressables", "cache this GetComponent call", or "write an edit mode test for this". Not for engine-agnostic C# and SOLID rules, use `coding-standards`.
---

# Unity Game Development Standards

How a Unity project keeps a stable frame time and stays testable: nothing allocates in the per-frame path, nothing
is looked up by search at runtime, and configuration lives in assets rather than in code. Most Unity stutter is a
garbage collection pause caused by a single allocating line inside `Update`.

Baseline: Unity 6.3 LTS, the current supported LTS (verified locally as 6000.3). Everything below assumes the
Addressables, Input System, and Test Framework packages from that release.

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

- Language-level C# design, SOLID, naming, and error handling, use `coding-standards`.
- Designing the backend a multiplayer or live-ops game talks to, use `backend-patterns`.
- Building the CI pipeline itself rather than the Unity build settings, use `deployment-patterns`.
- Writing the test strategy and coverage policy, use `tdd-workflow`.
- Profiling a non-Unity application, use `performance-optimization`.

---

### Nothing allocates per frame

Any managed allocation inside `Update`, `FixedUpdate`, or `LateUpdate` accumulates until the collector runs, and the
collector running mid-frame is the stutter. Build strings with `StringBuilder`, never with `+` in a loop.

Pass:

```csharp
private readonly StringBuilder _hud = new StringBuilder(64);

private void Update()
{
    _hud.Clear();
    _hud.Append("HP ").Append(_health);
    _hudLabel.text = _hud.ToString();
}
```

Fail:

```csharp
private void Update() => _hudLabel.text = "HP " + _health + " / " + _maxHealth;
```

Use `GarbageCollector.GCMode.Manual` only for a critical, predictable segment with a bounded allocation budget, a
racing lap for example, and always re-enable incremental GC afterwards. Leaving it off invites the operating system
to kill the process for memory pressure.

---

### Pool instead of Instantiate

`Instantiate` and `Destroy` during gameplay allocate and produce garbage. Pre-warm a pool at scene load and
activate out of it.

Pass:

```csharp
for (int i = 0; i < poolSize; i++)
    _pool.Enqueue(Instantiate(prefab));

var obj = _pool.Count > 0 ? _pool.Dequeue() : Instantiate(prefab);
obj.SetActive(true);
```

Release by deactivating and returning to the pool, never by destroying:

```csharp
obj.SetActive(false);
_pool.Enqueue(obj);
```

Fail:

```csharp
private void Fire() => Destroy(Instantiate(bulletPrefab), 3f);
```

---

### Addressables, and every load has a release

`Resources.Load` pulls its whole folder into the build and gives no control over memory. Use Addressables, and pair
every `LoadAssetAsync` with a `Release` when the asset is no longer needed, so the reference count reaches zero and
the bundle actually unloads.

Pass:

```csharp
var handle = Addressables.LoadAssetAsync<Sprite>("ui/icons/health");
await handle.Task;
_healthIcon.sprite = handle.Result;
```

Then release it when the screen closes:

```csharp
Addressables.Release(handle);
```

Fail:

```csharp
_healthIcon.sprite = Resources.Load<Sprite>("icons/health");
```

Organise groups by load context, `UI`, `Level_01`, `Shared_Audio`, so a download is scoped to what the player is
about to need and content updates stay incremental.

---

### Cache component lookups

`GetComponent<T>()` and the `FindObjectOfType<T>()` family are searches. Run them once in `Awake` or `Start` and
hold the reference.

Pass:

```csharp
private Rigidbody _rb;

private void Awake() => _rb = GetComponent<Rigidbody>();
```

Fail:

```csharp
private void Update() => GetComponent<Rigidbody>().AddForce(Vector3.up);
```

Keep heavy initialisation out of `Awake` unless it is synchronous and fast, defer the rest to `Start` or an async
path so scene loading is not blocked. Null-check a cached reference in `OnEnable` where the component can be
destroyed and re-enabled, because the reference does not survive a scene reload.

---

### Make execution order explicit

Systems that produce data, input and physics results, must run before the systems that consume them. Relying on
Unity's arbitrary default order produces a one-frame lag that only shows up under load.

Pass:

```csharp
[DefaultExecutionOrder(-100)]
public class InputManager : MonoBehaviour { }
```

Fail:

```csharp
public class InputManager : MonoBehaviour { }
```

Project Settings, Script Execution Order does the same job for cases where the attribute is impractical. Use one of
the two, not neither.

---

### Physics without allocation

`Physics.RaycastAll` allocates an array per call. The `NonAlloc` variants write into a buffer you own.

Pass:

```csharp
private readonly RaycastHit[] _hits = new RaycastHit[10];

private void Update()
{
    int count = Physics.RaycastNonAlloc(transform.position, transform.forward, _hits, 10f);
    for (int i = 0; i < count; i++) { /* process _hits[i] */ }
}
```

Fail:

```csharp
private void Update()
{
    foreach (var hit in Physics.RaycastAll(transform.position, transform.forward, 10f)) { }
}
```

Set position and rotation together with `Transform.SetPositionAndRotation()` rather than assigning each, which
triggers two internal transform updates. Pass custom structs in tight math loops by `ref` or `in` to avoid copying.

---

### C# naming

A `MonoBehaviour` class name matches its filename exactly, or Unity cannot bind the script. Expose Inspector fields
with `[SerializeField] private`, never by making a field public.

Pass:

```csharp
[SerializeField] private float _moveSpeed = 5f;
```

Fail:

```csharp
public float moveSpeed = 5f;
```

Wrap every script in a project namespace such as `MyGame.Core` or `MyGame.UI`. Private fields are `_camelCase`,
public properties are `PascalCase`, constants and `static readonly` are `PascalCase` rather than
`UPPER_SNAKE_CASE`, interfaces are prefixed `I`, abstract bases are prefixed `Base`.

---

### Doc Comments

Default to none. A doc comment is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named method, rename the parameters so they carry their own meaning, and tighten the
types. Do that first and most doc comments have nothing left to say, which is the outcome you want. Code that explains
itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `<param>` and `<returns>` and `<exception>` alike, and only appears when it genuinely adds something: if the
note does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in. Keep `<summary>` on
one physical line, the expanded three-line form says no more and reads as filler.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `<param>` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or
   who owns the object afterwards (whether the caller must return it to the pool is exactly that). `<param
   name="speed">The speed.</param>` is noise, delete it.
3. `<returns>` only when it is non-obvious.
4. `<exception>` always, for every exception a caller can act on. C# keeps throwing out of the signature, so this one
   is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

Pass, single-line summary, then only what the signature cannot say:

```csharp
/// <summary>Spawns a pooled projectile at the muzzle and arms it.</summary>
/// <param name="speed">Metres per second, clamped to the weapon maximum.</param>
/// <exception cref="InvalidOperationException">Thrown when the pool is exhausted.</exception>
public Projectile Fire(float speed) { }
```

Fail, three lines to say what the method name already said:

```csharp
/// <summary>
/// Fires a projectile.
/// </summary>
/// <param name="speed">The speed.</param>
/// <returns>A projectile.</returns>
public Projectile Fire(float speed) { }
```

---

### ScriptableObject architecture

Put configuration in ScriptableObject assets rather than hardcoding it in MonoBehaviours, so a designer can tune it
without a recompile, and use ScriptableObject event channels to decouple systems instead of direct references or
static events. Never store runtime mutable state in one: it persists between Play Mode sessions in the Editor and
produces a bug that only reproduces on the second run. Full data-container and event-channel examples are in
[references/architecture-and-testing.md](references/architecture-and-testing.md).

Pass:

```csharp
[CreateAssetMenu(menuName = "Game/WeaponData")]
public class WeaponData : ScriptableObject { public float damage; public float fireRate; }
```

Fail:

```csharp
[CreateAssetMenu(menuName = "Game/PlayerState")]
public class PlayerState : ScriptableObject { public int currentHealth; }
```

---

### Testing with the Unity Test Framework

Tests live in a dedicated `Tests/` assembly definition. Edit Mode for pure logic, ScriptableObject configuration,
utilities, and data validation, which need no scene and run fastest. Play Mode for gameplay, physics, coroutines,
component lifecycle, and integration. Mock through interfaces and hand-written doubles, and build a minimal scene
per test rather than loading a production one, which breaks whenever a designer moves something.

Pass:

```csharp
[Test]
public void WeaponData_DamageIsPositive() => Assert.Greater(_weaponData.damage, 0f);
```

Fail:

```csharp
[UnityTest]
public IEnumerator Player_TakesDamage() { SceneManager.LoadScene("Level_01_Production"); yield return null; }
```

---

### Reference files

| Open this | For |
|---|---|
| [references/project-and-build.md](references/project-and-build.md) | Git and LFS setup, serialisation mode, IL2CPP and stripping, the CI build matrix, the Input System, and UI Toolkit versus UGUI |
| [references/architecture-and-testing.md](references/architecture-and-testing.md) | Full ScriptableObject data-container and event-channel examples, and Edit Mode versus Play Mode test structure |

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
- [ ] Every `GetComponent` and `FindObjectOfType` cached in `Awake` or `Start`.
- [ ] Producer systems ordered ahead of consumers with `[DefaultExecutionOrder]` or the project setting.
- [ ] `NonAlloc` physics queries with a field-level buffer.
- [ ] Inspector fields are `[SerializeField] private`, every script in a project namespace.
- [ ] Configuration lives in ScriptableObjects, no runtime mutable state in them.
- [ ] Tests sit in their own assembly definition and build their own minimal scenes.
