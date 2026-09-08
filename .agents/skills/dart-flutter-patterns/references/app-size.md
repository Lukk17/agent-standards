# App Size and Runtime Performance

Measuring what the bundle actually contains, cutting it down, and the runtime performance work that lives next to
it.

---

### Size concepts

- Never measure a debug build. Debug includes VM overhead, skips ahead-of-time compilation, and does no tree
  shaking. Only profile and release builds tell you anything.
- Upload size is not download size. The stores strip native library architectures and asset densities the target
  device does not need, so an APK, AAB, or IPA is always larger than what a user downloads.
- The AOT compiler tree-shakes unreachable code in profile and release mode automatically.
- `--analyze-size` writes a `*-code-size-analysis_*.json` breaking the binary down by package, library, class, and
  function.

---

### Generating a size report

Android App Bundle:

```bash
flutter build appbundle --analyze-size --target-platform=android-arm64
```

Android APK:

```bash
flutter build apk --analyze-size --target-platform=android-arm64
```

iOS. This produces a `.app` useful for relative content sizing but not for projecting the App Store download:

```bash
flutter build ios --analyze-size
```

Desktop, substituting `windows`, `macos`, or `linux`:

```bash
flutter build linux --analyze-size
```

The JSON lands under `build/`.

---

### Reading the report

```bash
dart devtools
```

Open the app size tool from the DevTools landing page and upload the JSON. Work the treemap top down:

1. Find the largest contributors, package by package.
2. Ask whether each one is strictly necessary at that size.
3. Remove, replace, or trim it.
4. Regenerate the JSON and compare old against new in the DevTools Diff tab. Without the diff you are guessing
   about whether the change helped.

---

### Estimating the real iOS download size

1. Set the version and build number in `pubspec.yaml`.
2. Build an archive:

```bash
flutter build ipa --export-method development
```

3. Open `build/ios/archive/*.xcarchive` in Xcode.
4. Click Distribute App and choose Development.
5. In App Thinning, select all compatible device variants, and check Strip Swift symbols.
6. Sign and export.
7. Read `App Thinning Size Report.txt` in the exported directory.

```text
Variant: Runner-7433FC8E-1DF4-4299-A7E8-E00768671BEB.ipa
Supported variant descriptors: [device: iPhone12,1, os-version: 13.0]
App + On Demand Resources size: 5.4 MB compressed, 13.7 MB uncompressed
App size: 5.4 MB compressed, 13.7 MB uncompressed
```

Compressed is what the user downloads. Uncompressed is the on-device footprint.

---

### Reducing size

Split the debug symbols out of the binary and keep them for symbolicating crash reports:

```bash
flutter build apk --obfuscate --split-debug-info=build/app/outputs/symbols
```

Archive that symbols directory alongside the release. Without it an obfuscated stack trace is unreadable.

Then work through the usual suspects:

- Unused assets. Audit `pubspec.yaml` and `assets/`, and delete every image, font, and file no longer referenced.
- Heavy dependencies. A package that ships a full icon set or every locale, when you use three icons and two
  locales, is worth replacing or forking down.
- Uncompressed media. Run PNG and JPEG assets through `pngquant`, `imageoptim`, or a WebP conversion before
  bundling.
- Font subsetting. Flutter subsets icon fonts automatically in release builds. Do not disable it with
  `--no-tree-shake-icons` unless icon code points are computed at runtime, which is itself worth removing.
- Multiple image densities where one vector would do.

---

### Runtime performance

Size and speed share a toolchain, so treat them as one pass.

- Profile in profile mode on a real device. The debug build's numbers mean nothing, and a simulator's mean less.
- Use the DevTools Performance view to find the janky frame, then read its timeline to see whether the cost is in
  build, layout, or raster.
- Wrap a subtree that repaints independently, such as a spinner or a video surface, in `RepaintBoundary` so its
  repaints do not drag the whole layer along.
- Turn on the Highlight Repaints overlay during development. Anything flashing that should be static is a rebuild
  you can remove.
- Missing `const` is a lint error, enforced by `flutter analyze`. Keep it that way.
- Impeller is the default renderer on iOS and Android. Profile against Impeller, and report shader or raster
  regressions against it rather than assuming the old Skia behaviour.

---

### Checklist

- [ ] Size was measured on a release build, never debug.
- [ ] The size analysis JSON was diffed against the previous build, not just eyeballed.
- [ ] iOS download size came from an App Thinning report, not from the IPA file size.
- [ ] Release builds run with `--obfuscate` and `--split-debug-info`, and the symbols are archived.
- [ ] The asset directory contains nothing the code does not reference.
- [ ] Images are compressed and shipped at the densities actually used.
- [ ] Icon tree shaking is on.
- [ ] Jank was profiled in profile mode on a physical device against Impeller.
- [ ] Independently repainting subtrees sit behind a `RepaintBoundary`.
