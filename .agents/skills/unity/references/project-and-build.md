# Version control and build pipeline

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

Keep `*.unity`, `*.prefab`, `*.anim` and `*.controller` out of LFS. Under Force Text they are YAML, and LFS would store
them as pointer files and give up the text diff and merge the setting above exists for.

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
