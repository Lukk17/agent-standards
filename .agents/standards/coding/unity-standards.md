### AI Unity MCP Development Standards

---

### Core Execution Directives

- Treat all LLM generated C# code, memory management paradigms, and Unity asset structures as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every Unity architectural decision.
- Append a Zero-Trust directive demanding mandatory web searches for current Unity API documentation, specifically regarding Addressables, Garbage Collection, and Script Execution.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official Unity documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every Unity method, configuration property, and memory optimization provided.
- Mandate direct, working links to the official Unity documentation used to ground the code.

---

### Memory Management and Garbage Collection

- Prevent CPU spikes and frame rate drops by avoiding any dynamic memory allocations within the Update, FixedUpdate, and LateUpdate methods. [Confidence: 100%]
- Reuse objects via Object Pooling instead of using Instantiate and Destroy during active gameplay loops. [Confidence: 100%]
- Use GarbageCollector.GCMode.Manual or GarbageCollector.Mode.Disabled only for critical, predictable gameplay segments with strict allocation bounds to prevent OS-level memory shutdowns. [Confidence: 100%]
- Prevent string manipulation in tight loops. Mandate the use of StringBuilder instead of direct string concatenation to prevent managed heap fragmentation. [Confidence: 100%]

---

### Asset Management and Addressables

- Reject the use of Resources.Load. Mandate the Addressables system for dynamic asset loading to optimize memory footprint and bundle sizes. [Confidence: 100%]
- Prevent memory leaks by strictly enforcing mirrored load and release calls. Every Addressables.LoadAssetAsync call must be paired with an Addressables.Release call. [Confidence: 100%]
  - Link: https://docs.unity3d.com/Packages/com.unity.addressables@2.0/manual/MemoryManagement.html
  - Quote: "a"
- Unload Addressable bundles explicitly by decrementing the reference count to zero, ensuring that memory utilized by AsyncOperationHandle structs is properly freed. [Confidence: 100%]

---

### Script Execution and Lifecycle

- Explicitly define the execution sequence using Unity Script Execution Order settings instead of relying on arbitrary load orders. [Confidence: 100%]
  - Link: https://docs.unity3d.com/Manual/class-MonoManager.html
  - Quote: "Order"
- Do not place heavy initialization logic in Awake. Defer non-critical setup to Start or use asynchronous operations to prevent blocking the main thread during scene loads. [Confidence: 100%]
- Cache all GetComponent and FindObjectOfType calls in the Awake or Start methods. Strictly prohibit their use inside Update loops due to severe performance penalties. [Confidence: 100%]

---

### Performance and Physics

- Use non-allocating physics casts like Physics.RaycastNonAlloc instead of Physics.RaycastAll to eliminate GC allocation during collision checks. [Confidence: 100%]
- Modify Transform properties such as position and rotation in a single operation using Transform.SetPositionAndRotation rather than setting them sequentially to avoid redundant internal transform updates. [Confidence: 100%]
- Ensure all custom structs used in tight physics or math loops are passed by reference using the ref or in keywords to prevent unnecessary stack copying. [Confidence: 100%]

---

### C# Naming Conventions in Unity

- MonoBehaviour class names must match their filename exactly. [Confidence: 100%]
- Use `[SerializeField] private` for Inspector-exposed fields; never use `public` fields solely for Inspector visibility. [Confidence: 100%]
- Wrap all scripts in a project-specific namespace (e.g., `MyGame.Core`); do not use the global namespace. [Confidence: 100%]
- Prefix interfaces with `I` (`IInteractable`); prefix abstract base classes with `Base` or `Abstract` (`BaseDamageable`). [Confidence: 100%]
- Private fields: `_camelCase`; public properties: `PascalCase`; constants: `PascalCase` (C# convention — not `UPPER_SNAKE_CASE`). [Confidence: 100%]

---

### Architecture: ScriptableObject-Based Design

- Use **ScriptableObjects** as data containers for configuration (weapon stats, level parameters, audio clips) instead of hardcoding values in MonoBehaviours. [Confidence: 100%]
  - Link: https://docs.unity3d.com/Manual/class-ScriptableObject.html
  - Quote: "independent"
- Use **ScriptableObject-based event channels** (`GameEvent`, `GameEventListener`) for decoupled communication between systems instead of direct MonoBehaviour references or static events. [Confidence: 100%]
- Never store runtime game state in ScriptableObjects that persist between Play Mode sessions in the Editor; use them only for configuration data or events.

---

### Testing

- Use the **Unity Test Framework** for all automated tests; organise tests in an `Tests/` assembly definition (`*.asmdef`). [Confidence: 100%]
  - Link: https://docs.unity3d.com/Packages/com.unity.test-framework@1.4/manual/index.html
  - Quote: "framework"
- Use **Edit Mode tests** for pure logic, ScriptableObject configuration, and utility functions (no scene required).
- Use **Play Mode tests** for gameplay mechanics, physics interactions, and component lifecycle behaviour.
- Mock dependencies using interfaces and manual test doubles; do not use the game's production scene in automated tests.

---

### Version Control

- Commit a `.gitignore` that excludes: `Library/`, `Temp/`, `Logs/`, `Builds/`, `UserSettings/`. [Confidence: 100%]
- Set **Force Text** serialisation in Project Settings → Editor → Asset Serialization to produce human-readable YAML diffs for scene and prefab files.
- Use **Git LFS** for all binary assets: textures, audio, models, and animations (track by extension: `*.png`, `*.wav`, `*.fbx`, `*.anim`).

---

### Build Pipeline

- Choose **IL2CPP** over Mono for release builds on mobile and console platforms (better runtime performance, code stripping). [Confidence: 100%]
- Use Mono for development builds only (faster iteration times).
- Configure the CI build matrix to produce builds for all target platforms (Android AAB, iOS IPA, Windows standalone) on every merge to the main branch.
- Use **Unity Cloud Build** or a self-hosted runner with the correct Unity license activated.

---

### Input System

- Use the **New Input System** (`com.unity.inputsystem`) for all new projects. Do not use the legacy `Input` class. [Confidence: 100%]
  - Link: https://docs.unity3d.com/Packages/com.unity.inputsystem@1.8/manual/index.html
  - Quote: "system"
- Define all input actions in an **Input Actions asset** (`.inputactions`); never hardcode key bindings in MonoBehaviours.
- Generate a C# class from the Input Actions asset for type-safe access.

---

### UI Standards

- Use **UI Toolkit** (`UIElements`) for all new editor tooling and for runtime UI in new projects targeting Unity 2023+. [Confidence: 100%]
- Use **UGUI** (`Canvas`-based) only for in-world spatial UI (e.g., health bars above characters) or when porting a legacy UI system.
- Do not mix UI Toolkit and UGUI in the same screen; choose one system per UI context.