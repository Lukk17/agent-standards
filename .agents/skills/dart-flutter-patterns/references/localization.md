# Localization

Configuring `gen-l10n`, writing ARB resources, wiring the delegates, formatting plurals and dates, and the traps
that bite on iOS and in tests.

---

### Configuration

Add the localization dependencies and turn on generation in `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_localizations:
    sdk: flutter
  intl: any

flutter:
  generate: true
```

Add `l10n.yaml` at the project root:

```yaml
arb-dir: lib/l10n
template-arb-file: app_en.arb
output-localization-file: app_localizations.dart
```

The `flutter_gen` synthetic package is removed. The generator writes ordinary Dart files into `arb-dir` (or into
`output-dir` if you set one), so the import is your own package:

```dart
import 'package:my_app/l10n/app_localizations.dart';
```

Never `import 'package:flutter_gen/gen_l10n/app_localizations.dart';`. A `synthetic-package: true` line in
`l10n.yaml` now fails the build outright, and `synthetic-package: false` only prints a warning telling you to
delete it.

---

### ARB resources

The template file carries the strings and their metadata. Translation files carry only the values.

`lib/l10n/app_en.arb`:

```json
{
  "helloWorld": "Hello World!",
  "@helloWorld": {
    "description": "The conventional newborn programmer greeting"
  }
}
```

`lib/l10n/app_es.arb`:

```json
{
  "helloWorld": "Hola Mundo!"
}
```

Write a `description` for every key. It is the only context a translator gets, and without it "Open" becomes a
coin flip between the verb and the adjective.

---

### App integration

```dart
return MaterialApp(
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: const [Locale('en'), Locale('es')],
  home: const MyHomePage(),
);
```

Read a value with `AppLocalizations.of(context)`. Set `nullable-getter: false` in `l10n.yaml` so the getter returns
a non-nullable object and no call site needs `!`.

With `WidgetsApp` instead of `MaterialApp`, drop `GlobalMaterialLocalizations.delegate`.

---

### Placeholders, plurals, and selects

Placeholders:

```json
"hello": "Hello {userName}",
"@hello": {
  "description": "A greeting addressed to the signed-in user",
  "placeholders": {
    "userName": { "type": "String", "example": "Bob" }
  }
}
```

Plurals. Do not build these by concatenating a count and a noun, because the plural rules differ per language and
several languages have more than two forms:

```json
"nWombats": "{count, plural, =0{no wombats} =1{1 wombat} other{{count} wombats}}",
"@nWombats": {
  "placeholders": {
    "count": { "type": "num", "format": "compact" }
  }
}
```

Selects, for gender or a small enum:

```json
"pronoun": "{gender, select, male{he} female{she} other{they}}",
"@pronoun": {
  "placeholders": {
    "gender": { "type": "String" }
  }
}
```

Dates and numbers, formatted through `intl` rather than by hand:

```json
"dateMessage": "Date: {date}",
"@dateMessage": {
  "placeholders": {
    "date": { "type": "DateTime", "format": "yMd" }
  }
}
```

---

### Adding a language

1. Create the new `.arb` file in `arb-dir`, for example `app_fr.arb`.
2. Translate every key from the template file.
3. Add the `Locale` to `supportedLocales`.
4. Regenerate and check the ARB syntax:

```bash
flutter gen-l10n
```

5. Fix any missing placeholder or malformed plural or select the generator reports, then regenerate.
6. On iOS, add the language to the bundle as well. Open `ios/Runner.xcodeproj` in Xcode, select the `Runner`
   project, go to the Info tab, and add the locale under Localizations. Without it the App Store listing and the
   system settings do not know the app supports the language, even though the runtime does.

Point `untranslated-messages-file` at a path in `l10n.yaml` and the generator writes out every key still missing a
translation, which is the cheapest way to keep locales from silently drifting.

---

### Troubleshooting

Missing Localizations ancestor. `TextField`, `CupertinoTabBar`, and friends need `MaterialLocalizations` or
`CupertinoLocalizations` above them. Inside `MaterialApp` or `CupertinoApp` that is automatic. In a test or a bare
`WidgetsApp`, wrap the subtree:

```dart
Localizations(
  locale: const Locale('en', 'US'),
  delegates: const [
    DefaultWidgetsLocalizations.delegate,
    DefaultMaterialLocalizations.delegate,
    DefaultCupertinoLocalizations.delegate,
  ],
  child: child,
)
```

Wrong script variant. For a language written in several scripts, name the script and country explicitly so Flutter
does not resolve to something unexpected:

```dart
supportedLocales: const [
  Locale.fromSubtags(languageCode: 'zh', scriptCode: 'Hans', countryCode: 'CN'),
  Locale.fromSubtags(languageCode: 'zh', scriptCode: 'Hant', countryCode: 'TW'),
]
```

Layout breaks in another language. German and Finnish strings run roughly 30% longer than English, and Arabic and
Hebrew flip the direction. Test with a long-string locale and with `Directionality(textDirection: TextDirection.rtl)`
before shipping.

---

### Checklist

- [ ] `generate: true` is in `pubspec.yaml` and `l10n.yaml` exists at the project root.
- [ ] No `flutter_gen` import and no `synthetic-package` key anywhere.
- [ ] `nullable-getter: false` is set, so no call site force-unwraps `AppLocalizations.of`.
- [ ] Every key in the template file has a `description`.
- [ ] Counts go through ICU `plural`, never through string concatenation.
- [ ] Dates and numbers are formatted through `intl` placeholders.
- [ ] Every user-facing string in widgets, validators, semantics labels, and error messages resolves through
      `AppLocalizations`.
- [ ] New locales are registered in `supportedLocales` and in the iOS bundle.
- [ ] The layout was checked with a long-string locale and in right-to-left.
