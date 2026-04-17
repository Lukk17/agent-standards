---
name: unity
description: Unity game development standards for performance, memory management, asset loading, architecture patterns, testing, and build configuration.
origin: project-standards
---

# Unity Game Development Standards

## Memory Management and Garbage Collection

- **No allocations in Update, FixedUpdate, or LateUpdate.** Any dynamic memory allocation in per-frame methods causes GC spikes and frame rate drops.
- Use **Object Pooling** for all runtime instantiation. Never call `Instantiate` or `Destroy` during active gameplay loops. Pre-warm pools during scene load.
- Use `GarbageCollector.GCMode.Manual` (or `GarbageCollector.Mode.Disabled`) only for critical, predictable gameplay segments with strictly bounded allocation budgets (e.g., a racing lap). Always re-enable incremental GC afterward to prevent OS-level memory pressure shutdowns.
- Use `StringBuilder` in any loop that constructs strings. Never use `+` string concatenation inside Update or tight loops; each concatenation allocates a new managed string object.

Example pool pattern:
```csharp
// Pre-warm
for (int i = 0; i < poolSize; i++)
    _pool.Enqueue(Instantiate(prefab));

// Acquire
var obj = _pool.Count > 0 ? _pool.Dequeue() : Instantiate(prefab);
obj.SetActive(true);

// Release
obj.SetActive(false);
_pool.Enqueue(obj);
```

## Asset Management — Addressables System

- **Never use `Resources.Load`.** Use the **Addressables** system (`com.unity.addressables`) for all dynamic asset loading to optimise memory footprint and reduce bundle sizes.
- Enforce **mirrored Load/Release** calls. Every `Addressables.LoadAssetAsync<T>()` call must have a corresponding `Addressables.Release()` call when the asset is no longer needed.
- Unload Addressable bundles explicitly by decrementing the reference count to zero, ensuring that memory used by `AsyncOperationHandle` structs is properly freed.
- Organise Addressable groups by load context (e.g., `UI`, `Level_01`, `Shared_Audio`) to minimise bundle download size and enable incremental content updates.

```csharp
// Load
var handle = Addressables.LoadAssetAsync<Sprite>("ui/icons/health");
await handle.Task;
_healthIcon.sprite = handle.Result;

// Release when done
Addressables.Release(handle);
```

## Script Execution Order

- Explicitly define the execution sequence using **Script Execution Order** (Project Settings → Script Execution Order) instead of relying on arbitrary Unity load orders.
- Use `[DefaultExecutionOrder(N)]` attribute on MonoBehaviours where the execution order matters:
  ```csharp
  [DefaultExecutionOrder(-100)]
  public class InputManager : MonoBehaviour { ... }
  ```
- Systems that produce data (input, physics results) must execute before systems that consume it (character controllers, UI).

## Component Caching and Lifecycle

- Cache all `GetComponent<T>()` and `FindObjectOfType<T>()` calls in `Awake()` or `Start()`. Never call them inside `Update()` loops — they are expensive searches.
- Place heavy initialisation logic in `Awake()` only when it is synchronous and fast. Defer non-critical setup to `Start()` or use `async`/`UniTask` to prevent blocking the main thread during scene loads.
- Null-check cached references in `OnEnable` if the component may be destroyed and re-enabled; do not assume the cached reference remains valid across scene reloads.

```csharp
private Rigidbody _rb;
private Animator _animator;

private void Awake()
{
    _rb = GetComponent<Rigidbody>();
    _animator = GetComponent<Animator>();
}
```

## Performance — Physics

- Use **`Physics.RaycastNonAlloc`** instead of `Physics.RaycastAll` to eliminate GC allocation during collision checks. Pre-allocate a results buffer at field level.
- Modify Transform position and rotation in a single operation using `Transform.SetPositionAndRotation()` rather than setting `position` and `rotation` separately to avoid redundant internal transform updates.
- Pass custom structs used in tight physics or math loops **by reference** using the `ref` or `in` keywords to prevent unnecessary stack copying.

```csharp
private readonly RaycastHit[] _hits = new RaycastHit[10];

private void Update()
{
    int count = Physics.RaycastNonAlloc(transform.position, transform.forward, _hits, 10f);
    for (int i = 0; i < count; i++) { /* process _hits[i] */ }
}
```

## C# Naming Conventions

- `MonoBehaviour` class names must **match their filename exactly**.
- Use **`[SerializeField] private`** for Inspector-exposed fields. Never use `public` fields solely for Inspector visibility.
- Wrap all scripts in a **project-specific namespace** (e.g., `MyGame.Core`, `MyGame.UI`). Do not place scripts in the global namespace.
- Naming rules:
  - Private fields: `_camelCase`
  - Public properties: `PascalCase`
  - Constants and static readonly: `PascalCase` (C# convention, not `UPPER_SNAKE_CASE`)
  - Interfaces: prefix with `I` — `IInteractable`, `IDamageable`
  - Abstract base classes: prefix with `Base` — `BaseDamageable`, `BaseWeapon`

## Architecture — ScriptableObject-Based Design

- Use **ScriptableObjects as data containers** for configuration (weapon stats, level parameters, audio clips, difficulty settings) instead of hardcoding values in MonoBehaviours.
- Use **ScriptableObject-based event channels** (`GameEvent` / `GameEventListener` pattern) for decoupled communication between systems, replacing direct MonoBehaviour references and static events.
- Never store runtime mutable game state in ScriptableObjects that persist between Play Mode sessions in the Editor. Use them only for immutable configuration data or event definitions.

```csharp
// Data container
[CreateAssetMenu(menuName = "Game/WeaponData")]
public class WeaponData : ScriptableObject
{
    public float damage;
    public float fireRate;
    public AudioClip shootSound;
}

// Event channel
[CreateAssetMenu(menuName = "Events/GameEvent")]
public class GameEvent : ScriptableObject
{
    private readonly List<GameEventListener> _listeners = new();
    public void Raise() => _listeners.ForEach(l => l.OnEventRaised());
    public void Register(GameEventListener l) => _listeners.Add(l);
    public void Unregister(GameEventListener l) => _listeners.Remove(l);
}
```

## Testing — Unity Test Framework

- Use the **Unity Test Framework** (`com.unity.test-framework`) for all automated tests. Organise tests in a dedicated `Tests/` assembly definition (`.asmdef`).
- Use **Edit Mode tests** for: pure logic, ScriptableObject configuration, utility functions, and data validation (no scene required, fastest execution).
- Use **Play Mode tests** for: gameplay mechanics, physics interactions, coroutine behaviour, component lifecycle, and integration tests requiring a running scene.
- Mock dependencies using interfaces and manual test doubles. Do not use the game's production scene in automated tests — create minimal test scenes.

```csharp
// Edit Mode test
[Test]
public void WeaponData_DamageIsPositive()
{
    var data = ScriptableObject.CreateInstance<WeaponData>();
    data.damage = 25f;
    Assert.Greater(data.damage, 0f);
}
```

## Version Control

- Commit a `.gitignore` excluding: `Library/`, `Temp/`, `Logs/`, `Builds/`, `UserSettings/`, `*.csproj`, `*.sln` (unless needed by CI).
- Set **Force Text** serialisation in Project Settings → Editor → Asset Serialization mode to produce human-readable YAML diffs for scene and prefab files, enabling meaningful Git diffs and conflict resolution.
- Use **Git LFS** for all binary assets tracked by extension:
  ```
  *.png *.jpg *.psd *.tga    # Textures
  *.wav *.mp3 *.ogg          # Audio
  *.fbx *.obj *.blend        # 3D models
  *.anim *.controller        # Animation assets
  *.unity *.prefab           # Scenes & prefabs (optional, helps with large files)
  ```

## Build Pipeline — IL2CPP and CI

- Use **IL2CPP** as the scripting backend for all release builds on mobile (Android, iOS) and console platforms. IL2CPP provides better runtime performance and enables code stripping via Managed Stripping Level settings.
- Use **Mono** for development builds only to benefit from faster iteration and script reload times.
- Configure the CI build matrix to produce builds for all target platforms (Android AAB, iOS IPA, Windows standalone) on every merge to the main branch.
- Use Unity Cloud Build or a self-hosted runner with the correct Unity license activated and the target platform build modules installed.
- Enable **Managed Code Stripping** (`Strip Engine Code: true`, `Managed Stripping Level: High`) for release builds. Maintain a `link.xml` to preserve types used via reflection.

## Input System — New Input System

- Use the **New Input System** (`com.unity.inputsystem`) for all new projects. Do not use the legacy `Input` class (`Input.GetKey`, `Input.GetAxis`, etc.).
- Define all input actions in an **Input Actions asset** (`.inputactions`). Never hardcode key bindings in MonoBehaviours.
- Generate a C# wrapper class from the Input Actions asset (Project Settings → Input System Package → Generate C# Class) for type-safe, IntelliSense-supported access.

```csharp
private PlayerInputActions _inputActions;

private void Awake()
{
    _inputActions = new PlayerInputActions();
    _inputActions.Player.Jump.performed += OnJump;
}

private void OnEnable() => _inputActions.Enable();
private void OnDisable() => _inputActions.Disable();
```

## UI Standards — UI Toolkit vs. UGUI

- Use **UI Toolkit** (`UIElements`) for:
  - All new editor tooling and custom Editor windows.
  - Runtime UI in new projects targeting Unity 2023+.
- Use **UGUI** (`Canvas`-based) only for:
  - In-world spatial UI (e.g., health bars above characters, world-space labels).
  - Porting or extending a legacy UGUI system where a full rewrite is not feasible.
- Do not mix UI Toolkit and UGUI in the same screen context. Choose one system per UI context and document the choice.
- Define all visual styles in USS (Unity Style Sheets) files, not inline in C# code.
