# Addressables

Loading, releasing and grouping assets with the Addressables package. Open this when a change loads an asset at runtime or organises asset groups. The rule it serves is in [SKILL.md](../SKILL.md).

---

### Every load has a release

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
