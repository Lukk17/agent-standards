# Input System

Reading player input through the Input System package. Open this when a change reads input or adds an action. The rules for per-frame code live in [SKILL.md](../SKILL.md).

---

### Actions asset and generated wrapper

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
