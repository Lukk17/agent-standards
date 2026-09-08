# Animation

The typed animation system, choosing implicit against explicit, shared element and physics motion, and how to
test something that moves.

---

### Core types

Never compute frames by hand. The framework owns the ticker and the interpolation.

- `Animation<T>` is a value that changes over time. It holds status (forward, completed, dismissed) and notifies
  listeners. It knows nothing about the UI.
- `AnimationController` drives the animation, generating values (0.0 to 1.0 by default) tied to the refresh rate.
  It needs a `vsync`, normally from `SingleTickerProviderStateMixin`, so it stops consuming resources off screen.
  It must be disposed.
- `Tween<T>` maps the controller's range onto an output type such as `Color`, `Offset`, or `double`. Attach it
  with `.animate()`.
- `Curve` applies non-linear timing through `CurvedAnimation` or `CurveTween`.

---

### Choosing an approach

| Need | Approach |
| --- | --- |
| A property changes and should ease to the new value, no playback control | Implicit: `AnimatedContainer`, `AnimatedOpacity`, `TweenAnimationBuilder` |
| Play, pause, reverse, loop, or coordinate several properties | Explicit: `AnimationController` with `AnimatedBuilder` |
| An element flies between two routes | `Hero` |
| Motion that models the physical world, such as snapping back after a drag | `SpringSimulation` driven by `animateWith` |
| Several motions overlapping or delayed against each other | One controller, several tweens, `Interval` curves |

Reach for the implicit widget first. It is one property and a duration, and it cannot leak a controller.

---

### Implicit animation

Swap the static widget for its animated counterpart, give it a `duration` and optionally a `curve`, then change
the property inside `setState`. There is nothing to dispose.

```dart
AnimatedContainer(
  duration: const Duration(milliseconds: 300),
  curve: Curves.easeOut,
  width: _expanded ? 200 : 50,
  color: _expanded ? Colors.red : Colors.blue,
)
```

---

### Explicit animation

Add `SingleTickerProviderStateMixin` (or `TickerProviderStateMixin` for several controllers), build the controller
in `initState`, drive the UI from `AnimatedBuilder`, and dispose the controller.

Staggering is one controller with `Interval` curves rather than several controllers, so the phases cannot drift.

```dart
class _StaggeredDemoState extends State<StaggeredDemo> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    duration: const Duration(seconds: 2),
    vsync: this,
  );

  late final Animation<double> _width = Tween<double>(begin: 50, end: 200).animate(
    CurvedAnimation(parent: _controller, curve: const Interval(0.0, 0.5, curve: Curves.easeIn)),
  );

  late final Animation<Color?> _color = ColorTween(begin: Colors.blue, end: Colors.red).animate(
    CurvedAnimation(parent: _controller, curve: const Interval(0.5, 1.0, curve: Curves.easeOut)),
  );

  @override
  void initState() {
    super.initState();
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) => Container(width: _width.value, height: 50, color: _color.value),
    );
  }
}
```

Pass the unchanging subtree through `AnimatedBuilder`'s `child` argument and use it inside the builder. That
subtree is then built once instead of on every frame.

---

### Hero transitions

Wrap the source widget in a `Hero` with a unique, data-driven `tag`, wrap the destination widget in a `Hero` with
the identical tag, and push the route normally. Keep the two subtrees visually similar or the flight reads as a
jump. A tag reused by two visible widgets on the same screen throws.

---

### Physics-based motion

Do not set a duration on the controller. Capture the gesture velocity, convert it into the animating property's
coordinate space, build a `SpringSimulation`, and hand it to `animateWith`.

```dart
void _onPanEnd(DragEndDetails details) {
  final simulation = SpringSimulation(
    const SpringDescription(mass: 1, stiffness: 500, damping: 25),
    _controller.value,
    0,
    -details.velocity.pixelsPerSecond.dy / MediaQuery.sizeOf(context).height,
  );
  _controller.animateWith(simulation);
}
```

---

### Custom route transitions

```dart
Route<T> slideUpRoute<T>(Widget destination) {
  return PageRouteBuilder<T>(
    pageBuilder: (context, animation, secondaryAnimation) => destination,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      final tween = Tween(begin: const Offset(0, 1), end: Offset.zero)
          .chain(CurveTween(curve: Curves.easeOut));
      return SlideTransition(position: animation.drive(tween), child: child);
    },
  );
}
```

---

### Accessibility and motion

Honour the OS reduce-motion setting. Check `MediaQuery.disableAnimationsOf(context)` and jump to the end state
instead of animating, rather than shipping motion a user has explicitly asked not to see.

---

### Testing animated state

`pumpAndSettle` waits until no frames are scheduled, so it hangs forever on a `repeat()` loop or an infinite
`SpringSimulation`. Advance the clock explicitly instead.

- Finite animation: `await tester.pumpAndSettle();` then assert the final state.
- Infinite or long animation: `await tester.pump(const Duration(milliseconds: 150));` to step to a known frame,
  then assert the intermediate state.
- Assert the widget state or a property value, not a pixel, unless you are deliberately writing a golden test.

See [testing.md](testing.md).

---

### Checklist

- [ ] Every `AnimationController` has a `vsync` and is disposed.
- [ ] Implicit animations were considered before an explicit controller was written.
- [ ] Staggered phases share one controller with `Interval` curves.
- [ ] `AnimatedBuilder` receives the static subtree through `child` rather than rebuilding it per frame.
- [ ] `Hero` tags are unique per screen and data-driven.
- [ ] Physics controllers have no fixed duration.
- [ ] Reduce-motion is honoured through `MediaQuery.disableAnimationsOf`.
- [ ] Tests never call `pumpAndSettle` on an animation that does not settle.
