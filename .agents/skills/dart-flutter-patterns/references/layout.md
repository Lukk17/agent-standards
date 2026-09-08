# Flutter Layout

The constraint model, the structural widgets that express it, and how to make one layout work across phone,
tablet, and desktop.

---

### The constraint rule

Constraints go down, sizes go up, the parent sets position.

- A parent passes minimum and maximum width and height to each child. A widget cannot choose a size outside them.
- The child picks a size inside those constraints and reports it back up.
- The parent decides the child's `x` and `y`. A child never knows where it is on screen.
- Unbounded constraints (`double.infinity`) on the main axis of a `Row` or `Column`, or inside a scrollable, throw
  a render exception. Bound them.

---

### Structural widgets

| Need | Widget |
| --- | --- |
| Horizontal or vertical linear arrangement | `Row`, `Column`, with `mainAxisAlignment` and `crossAxisAlignment` |
| Child fills the remaining space | `Expanded` |
| Child sizes itself but no larger than available | `Flexible` |
| Padding, margin, border, or background | `Container`, or `Padding` and `DecoratedBox` when only one applies |
| Overlapping children on the Z axis | `Stack`, anchored with `Positioned` |
| A hard, tight size | `SizedBox` with explicit `width` and `height` |
| A size derived from the parent's constraints | `LayoutBuilder` |

Prefer the narrow widget over `Container` when only one property is needed. `Padding` and `DecoratedBox` say what
they do, and `const` works on them more often.

---

### Unbounded constraints in a flex box

A `ListView` inside a `Column` receives infinite height and throws. Bound it with `Expanded`, or with
`shrinkWrap: true` when the list is short and genuinely should size to its content.

```dart
// BAD, throws an unbounded height exception
Column(
  children: [
    const Text('Header'),
    ListView(children: items),
  ],
)

// GOOD, the list gets the space the header did not use
Column(
  children: [
    const Text('Header'),
    Expanded(child: ListView(children: items)),
  ],
)
```

---

### Responsive versus adaptive

Responsive means fitting the same UI into different space: `LayoutBuilder`, `Expanded`, `Flexible`, and `Wrap`
resize and reflow the same structure.

Adaptive means swapping the structure for the form factor: a bottom navigation bar on a phone, a
`NavigationRail` on a tablet, a permanent `Drawer` on desktop.

```dart
class AdaptiveShell extends StatelessWidget {
  const AdaptiveShell({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth > 600) {
          return Row(
            children: [
              const SizedBox(width: 250, child: AppSidebar()),
              Expanded(child: child),
            ],
          );
        }
        return Column(
          children: [
            Expanded(child: child),
            const AppBottomNavigationBar(),
          ],
        );
      },
    );
  }
}
```

Branch on `constraints.maxWidth` from `LayoutBuilder`, not on `MediaQuery.sizeOf(context).width`, whenever the
widget occupies less than the whole window. `MediaQuery` reports the window, `LayoutBuilder` reports the box the
widget actually got.

---

### Building a complex layout

1. Deconstruct the design into rows, columns, and grids. Mark the overlapping regions as `Stack` and the
   scrolling regions as `ListView`, `GridView`, or `CustomScrollView`.
2. Decide per widget whether it needs a tight constraint (fixed size) or a loose one (flexible), and flag every
   scrollable that will sit inside a flex box.
3. Build outside in, starting at `Scaffold`. Extract each nested section into its own stateless widget class as
   soon as the indentation passes about three levels.
4. Run it, open the Flutter Inspector, turn on Debug Paint, and look for the yellow and black overflow stripes.
   Fix an overflow by wrapping in `Expanded` inside a flex box, or by making the parent scrollable.

---

### Checklist

- [ ] No scrollable sits directly inside a `Row` or `Column` without `Expanded`, `Flexible`, or `shrinkWrap`.
- [ ] No hardcoded pixel height stands in for a real constraint.
- [ ] Nested sections deeper than about three levels are extracted into widget classes.
- [ ] Width branches read `LayoutBuilder` constraints, not `MediaQuery`, unless the widget fills the window.
- [ ] The layout was checked at the largest OS font scale with no clipping.
- [ ] No overflow stripes appear at the smallest and largest supported window sizes.
