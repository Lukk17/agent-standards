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