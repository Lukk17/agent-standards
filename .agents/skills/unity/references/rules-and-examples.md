# Unity rules with examples

Open this for the Pass and Fail code behind any rule in [SKILL.md](../SKILL.md), and the reasoning behind each rule. Asset loading is in [addressables.md](addressables.md) and the test rules are in [test-framework.md](test-framework.md).

---

### Contents

- [Nothing allocates per frame](#nothing-allocates-per-frame)
- [Pool instead of Instantiate](#pool-instead-of-instantiate)
- [Cache component lookups](#cache-component-lookups)
- [Make execution order explicit](#make-execution-order-explicit)
- [Physics without allocation](#physics-without-allocation)
- [C# naming](#c-naming)
- [Doc Comments](#doc-comments)
- [ScriptableObject architecture](#scriptableobject-architecture)

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
activate out of it. An empty pool is a sizing defect: log it and raise the pool size, never fall back to
`Instantiate`.

Pass:

```csharp
for (int i = 0; i < poolSize; i++)
    _pool.Enqueue(Instantiate(prefab));

if (_pool.Count == 0)
{
    Debug.LogWarning($"{prefab.name} pool is empty, raise poolSize");
    return;
}
var obj = _pool.Dequeue();
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

### Cache component lookups

`GetComponent<T>()`, `FindFirstObjectByType<T>()` and `FindAnyObjectByType<T>()` are searches. Run them once in
`Awake` or `Start` and hold the reference. `FindObjectOfType<T>()` is deprecated in Unity 6: use
`FindFirstObjectByType<T>()`, or the faster `FindAnyObjectByType<T>()` when any instance will do.

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

XML doc comments follow "Doc Comments" in `coding-standards`. The C# delta: keep `<summary>` on one physical line,
because the expanded three-line form says no more, write `<exception>` for every exception a caller can act on, since
C# keeps throwing out of the signature, and use `<param>` for pool ownership, whether the caller must return the
object to the pool being exactly the kind of fact the signature cannot carry.

```csharp
/// <summary>Spawns a pooled projectile at the muzzle and arms it.</summary>
/// <param name="speed">Metres per second, clamped to the weapon maximum.</param>
/// <exception cref="InvalidOperationException">Thrown when the pool is exhausted.</exception>
public Projectile Fire(float speed) { }
```

---

### ScriptableObject architecture

Put configuration in ScriptableObject assets rather than hardcoding it in MonoBehaviours, so a designer can tune it
without a recompile, and use ScriptableObject event channels to decouple systems instead of direct references or
static events. Never store runtime mutable state in one: it persists between Play Mode sessions in the Editor and
produces a bug that only reproduces on the second run.

Pass, a data container and an event channel:

```csharp
[CreateAssetMenu(menuName = "Game/WeaponData")]
public class WeaponData : ScriptableObject
{
    [SerializeField] private float _damage;
    [SerializeField] private float _fireRate;
    [SerializeField] private AudioClip _shootSound;

    public float Damage => _damage;
    public float FireRate => _fireRate;
    public AudioClip ShootSound => _shootSound;
}

[CreateAssetMenu(menuName = "Events/GameEvent")]
public class GameEvent : ScriptableObject
{
    private readonly List<GameEventListener> _listeners = new();
    public void Raise() => _listeners.ForEach(l => l.OnEventRaised());
    public void Register(GameEventListener l) => _listeners.Add(l);
    public void Unregister(GameEventListener l) => _listeners.Remove(l);
}
```

Fail, runtime state in a ScriptableObject, which persists between Play Mode sessions in the Editor and produces a
bug that only reproduces on the second run:

```csharp
[CreateAssetMenu(menuName = "Game/PlayerState")]
public class PlayerState : ScriptableObject { public int currentHealth; }
```
