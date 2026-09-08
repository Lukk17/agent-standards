# Version control, build pipeline, input, and UI

Project-level setup rather than per-script rules. The runtime performance and architecture rules live in
[SKILL.md](../SKILL.md).

---

### Version control

Commit a `.gitignore` excluding `Library/`, `Temp/`, `Logs/`, `Builds/`, `UserSettings/`, `*.csproj`, and `*.sln`,
unless CI genuinely needs the project files.

Set Force Text serialisation in Project Settings, Editor, Asset Serialization. Scenes and prefabs then diff as
readable YAML, which is the difference between resolving a merge conflict and re-doing someone's work.

Track binaries with Git LFS by extension:

| Pattern | Content |
|---|---|
| `*.png *.jpg *.psd *.tga` | Textures |
| `*.wav *.mp3 *.ogg` | Audio |
| `*.fbx *.obj *.blend` | 3D models |
| `*.anim *.controller` | Animation assets |
| `*.unity *.prefab` | Scenes and prefabs, optional, worth it once they get large |

---

### Build pipeline, IL2CPP and CI

Use IL2CPP as the scripting backend for every release build on mobile and console. It gives better runtime
performance and it is what enables code stripping. Use Mono for development builds only, where script reload time
matters more than runtime speed.

Enable Managed Code Stripping for release builds, `Strip Engine Code: true` and `Managed Stripping Level: High`, and
maintain a `link.xml` preserving anything resolved by reflection. Stripping removes what the static analyser cannot
see being used, and reflection is exactly that case.

Configure the CI matrix to produce every target, Android AAB, iOS IPA, Windows standalone, on every merge to the
main branch. Use Unity Cloud Build or a self-hosted runner with the licence activated and the platform build modules
installed.

---

### Input System

Use the Input System package for all new projects. The legacy `Input` class (`Input.GetKey`, `Input.GetAxis`) has no
rebinding support and no device abstraction.

Define every action in an Input Actions asset and generate a C# wrapper from it (Project Settings, Input System
Package, Generate C# Class), so bindings are type-safe and discoverable rather than string keys.

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

The `OnEnable` and `OnDisable` pair matters: an actions asset left enabled on a disabled object keeps consuming
input and firing callbacks into a component that is no longer participating.

---

### UI Toolkit or UGUI

Use UI Toolkit (`UIElements`) for all new editor tooling and custom Editor windows, and for runtime UI in new
projects on the current LTS.

Use UGUI (`Canvas`-based) for in-world spatial UI, a health bar above a character or a world-space label, and for
extending a legacy UGUI system where a full rewrite is not justified.

Do not mix the two in one screen context. Choose one system per context and record the choice. Define all visual
styles in USS files rather than inline in C#, so a designer can change them without a recompile.
