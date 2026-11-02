# ScriptableObject architecture and the Unity Test Framework

Full examples for the two rules that need more than a snippet. The rules themselves live in
[SKILL.md](../SKILL.md).

---

### ScriptableObject architecture

Put configuration in ScriptableObject assets rather than hardcoding it in MonoBehaviours, so a designer can tune it
without a recompile. Use ScriptableObject event channels to decouple systems, replacing direct references and static
events.

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

---

### Testing with the Unity Test Framework

Put tests in a dedicated `Tests/` assembly definition. Edit Mode for pure logic, ScriptableObject configuration,
utilities, and data validation, which need no scene and run fastest. Play Mode for gameplay mechanics, physics,
coroutines, component lifecycle, and integration.

Pass, an Edit Mode test that sets the private serialized field through `SerializedObject`, the way the Inspector
does:

```csharp
[Test]
public void WeaponData_DamageIsPositive()
{
    var data = ScriptableObject.CreateInstance<WeaponData>();
    var serialized = new SerializedObject(data);
    serialized.FindProperty("_damage").floatValue = 25f;
    serialized.ApplyModifiedPropertiesWithoutUndo();
    Assert.Greater(data.Damage, 0f);
}
```

Fail, a test that loads the shipping scene and therefore breaks whenever a designer moves something:

```csharp
[UnityTest]
public IEnumerator Player_TakesDamage()
{
    SceneManager.LoadScene("Level_01_Production");
    yield return null;
}
```

Mock dependencies with interfaces and hand-written test doubles, and build a minimal scene per test rather than
reusing a production one.

---
