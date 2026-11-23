# Unity Test Framework

Where the tests live, what Edit Mode and Play Mode each cover, and how a test builds its own scene. Open this when writing or reviewing a Unity test. The rule it serves is in [SKILL.md](../SKILL.md).

---

### Edit Mode and Play Mode

Tests live in a dedicated `Tests/` assembly definition. Edit Mode for pure logic, ScriptableObject configuration,
utilities, and data validation, which need no scene and run fastest. Play Mode for gameplay, physics, coroutines,
component lifecycle, and integration. Mock through interfaces and hand-written doubles, and build a minimal scene
per test rather than loading a production one, which breaks whenever a designer moves something.

Pass:

```csharp
[Test]
public void WeaponData_DamageIsPositive() => Assert.Greater(_weaponData.Damage, 0f);
```

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
