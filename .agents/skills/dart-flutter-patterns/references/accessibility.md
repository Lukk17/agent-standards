# Accessibility

Making a Flutter app work with screen readers, large fonts, low vision, and limited dexterity, on mobile and on
the web.

---

### Design and styling

Flutter scales font sizes from the OS accessibility settings automatically. Your job is to leave room for it.

- Font scaling. Every layout must render its full content at the maximum OS font scale. Never hardcode a height on
  a text container. Test at the largest setting, not just the default.
- Colour contrast. At least 4.5:1 for normal text and 3.0:1 for large text (18pt regular or 14pt bold and above).
- Tap targets. Minimum 48 by 48 logical pixels for anything interactive. Padding counts toward the target,
  visual size does not have to grow.
- Never signal state by colour alone. Pair it with an icon, a label, or a shape.

---

### Semantics widgets

The semantics tree is what assistive technology reads. These three widgets shape it.

- `Semantics` annotates a subtree with meaning. Assign a role from `SemanticsRole` (button, link, heading, list
  item, and so on) when building a custom component so screen readers and web ARIA map it correctly.
- `MergeSemantics` collapses a composite widget's descendants into one node, so a card announces once instead of
  five times.
- `ExcludeSemantics` drops a subtree entirely. Use it for purely decorative imagery and for text already announced
  by a parent.

Every label, hint, and value is user-facing text. Source it from `AppLocalizations` and pass it in, never a
literal. See [localization.md](localization.md).

```dart
class CustomListItem extends StatelessWidget {
  const CustomListItem({super.key, required this.text, required this.onTap});
  final String text;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      role: SemanticsRole.listItem,
      button: true,
      label: text,
      child: InkWell(
        onTap: onTap,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 48),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Text(text),
          ),
        ),
      ),
    );
  }
}
```

The `text` here has already been localized by the caller, so the `Semantics` label and the visible text stay in
sync by construction.

---

### Images and icons

- An image carrying meaning gets a localized `semanticLabel`.
- A decorative image gets `ExcludeSemantics`, or an explicitly empty label, so the screen reader does not read a
  filename.
- An `IconButton` gets a `tooltip`, which doubles as its semantic label.

---

### Web accessibility

Flutter web paints to a canvas, so structure only reaches the browser through a generated DOM layer. That layer is
off by default, and Flutter exposes an invisible button labelled "Enable accessibility" for the user to turn it
on. Do not rely on that opt-in. Force it on at startup for every web build.

```dart
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

void main() {
  if (kIsWeb) {
    SemanticsBinding.instance.ensureSemantics();
  }
  runApp(const MyApp());
}
```

Standard widgets such as `TabBar`, `MenuAnchor`, and `Table` map to ARIA roles automatically. Custom components
need an explicit `SemanticsRole`, otherwise they reach the browser as anonymous divs.

---

### Responsive and adaptive as accessibility

Responsive design refits the same UI into the available space. Adaptive design swaps the layout and the input
model for the device: touch targets and a bottom bar on a phone, keyboard shortcuts and a navigation rail on
desktop. Both are accessibility work, because a UI that only fits one form factor excludes the users on the
others. See [layout.md](layout.md).

---

### Validating

1. Turn on VoiceOver (iOS, macOS) or TalkBack (Android) and traverse the whole screen with swipe navigation only.
2. Look for elements that announce nothing, announce a raw identifier, trap focus, or are unreachable.
3. Fix by adding `Semantics`, merging or excluding nodes, loosening a constraint, or adjusting colours.
4. Repeat until the traversal order is logical and every control announces its role and its state.
5. Run `flutter test` with the accessibility guidelines matchers to catch tap-target and contrast regressions in
   CI. See [testing.md](testing.md).

---

### Checklist

- [ ] Every interactive element is at least 48 by 48 logical pixels.
- [ ] The screen renders fully at the maximum OS font scale with no clipping.
- [ ] Contrast is at least 4.5:1 for normal text and 3.0:1 for large text.
- [ ] No state is communicated by colour alone.
- [ ] Custom interactive widgets carry a `Semantics` wrapper with the right `SemanticsRole`.
- [ ] Composite widgets use `MergeSemantics`, decorative ones use `ExcludeSemantics`.
- [ ] Every semantic label, hint, and tooltip comes from `AppLocalizations`.
- [ ] Web builds call `SemanticsBinding.instance.ensureSemantics()` in `main` under `kIsWeb`.
- [ ] The screen was traversed with a real screen reader, not just an automated check.
