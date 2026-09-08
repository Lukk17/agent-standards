# Native Interop and Platform Views

Talking to platform APIs through channels and Pigeon, binding C and C++ with FFI, embedding native views in the
widget tree, and the web and WebAssembly rules.

---

### Terminology

- Platform channel. The asynchronous message-passing bridge (`MethodChannel`, `EventChannel`,
  `BasicMessageChannel`) between Dart and the host platform.
- Pigeon. A code generator that produces type-safe channels from a Dart interface definition.
- FFI. `dart:ffi`, a direct synchronous binding to C and C++ with no channel overhead.
- Platform view. A native `View` (Android) or `UIView` (iOS) embedded in the Flutter widget tree.
- JS interop. `package:web` with `dart:js_interop`, the WebAssembly-compatible way to reach JavaScript and the DOM.

---

### Choosing a mechanism

| Need | Mechanism |
| --- | --- |
| Call an OS service written in Kotlin or Swift, occasionally | `MethodChannel` |
| Call platform APIs across a real surface, or from a plugin | Pigeon |
| Receive a continuous native stream (sensor, location) | `EventChannel` |
| Call an existing C or C++ library, or run hot native code | `dart:ffi` with `package:ffigen` |
| Show a native map, camera preview, or web view | Platform view |

---

### A platform channel handler pair

The smallest complete example: a battery-level query, Dart side and Android side. Both halves must agree on the
channel name and the method name, so declare the channel name as a constant on each side.

Dart:

```dart
import 'package:flutter/services.dart';

class BatteryService {
  static const MethodChannel _channel = MethodChannel('com.example.app/battery');

  Future<int> getBatteryLevel() async {
    try {
      final level = await _channel.invokeMethod<int>('getBatteryLevel');
      if (level == null) throw const BatteryUnavailableException('no level returned');
      return level;
    } on PlatformException catch (e) {
      throw BatteryUnavailableException(e.message ?? e.code);
    } on MissingPluginException {
      throw const BatteryUnavailableException('channel not registered on this platform');
    }
  }
}
```

Kotlin, in `MainActivity.kt`:

```kotlin
package com.example.app

import android.content.Context
import android.os.BatteryManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val channelName = "com.example.app/battery"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "getBatteryLevel" -> {
                        val manager = getSystemService(Context.BATTERY_SERVICE) as BatteryManager
                        val level = manager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
                        if (level >= 0) {
                            result.success(level)
                        } else {
                            result.error("UNAVAILABLE", "Battery level not available", null)
                        }
                    }
                    else -> result.notImplemented()
                }
            }
    }
}
```

Three things the Dart side must handle and usually does not: `PlatformException` for a native `result.error`,
`MissingPluginException` when the platform has no handler at all (which is what a web or desktop build sees), and
a null payload from a method typed to return a value.

Handle the `else` branch with `notImplemented()` rather than silently succeeding, so a Dart-side typo surfaces as
a `MissingPluginException` instead of a mysterious null.

---

### Pigeon

Prefer Pigeon over hand-written channels for anything beyond one or two methods. It removes the string method
names, the manual argument packing, and the drift between the two sides.

1. Add `pigeon` to `dev_dependencies`.
2. Define the data classes and an `@HostApi()` abstract class in `pigeons/messages.dart`.
3. Run the generator to emit the Dart, Kotlin, and Swift files.
4. Implement the generated interface in `MainActivity.kt` or your plugin class on Android.
5. Implement the generated protocol in `AppDelegate.swift` or your plugin class on iOS.
6. Import the generated Dart file and call the methods.

---

### Threading

- Channel methods destined for Flutter must be invoked on the platform's main thread.
- To run a channel handler on a background thread, use the task queue API (`makeBackgroundTaskQueue()`).
- To use a plugin or channel from a Dart background isolate, first call
  `BackgroundIsolateBinaryMessenger.ensureInitialized(rootIsolateToken)` with a `RootIsolateToken` captured on the
  main isolate.

---

### FFI

Use FFI for existing C or C++ libraries and for hot native code, where a channel's asynchronous hop would dominate.

`package_ffi` is the current template. It compiles native code through `build.dart` hooks, so there are no
per-platform CMake, Gradle, or podspec files to maintain. `plugin_ffi` is marked deprecated by `flutter create`
in Flutter 3.44 and points at `package_ffi`, so use it only when you genuinely need the Flutter plugin API or
Play Services alongside the native code.

```bash
flutter create --template=package_ffi my_native_package
```

Then:

- Mark every exported C++ symbol so link-time optimization cannot discard it:
  `extern "C" __attribute__((visibility("default"))) __attribute__((used))`.
- On Apple platforms, produce the identical dynamic library filename for every architecture and SDK. Do not append
  an architecture suffix to the `.dylib` or `.framework` name.
- Generate the Dart bindings with `package:ffigen`, configured in `ffigen.yaml`, rather than writing them by hand.

```bash
dart run ffigen
```

---

### Platform views on Android

Two composition modes, and the choice is a real trade-off.

- Hybrid composition (`PlatformViewLink` with `AndroidViewSurface` and
  `PlatformViewsService.initSurfaceAndroidView`). The native view joins the Android view hierarchy. Best fidelity
  and accessibility, and the only option that handles `SurfaceView` properly. It lowers overall Flutter frame
  rate, and some Flutter transforms over the view do not apply.
- Texture layer (`AndroidView`). The native view renders into a texture Flutter composites. Best Flutter
  rendering performance and every transform works. Fast scrolling over the view can drop frames, `SurfaceView` is
  problematic and breaks accessibility, and text magnifiers need Flutter rendered into a `TextureView`.

```dart
class NativeMapView extends StatelessWidget {
  const NativeMapView({super.key});

  @override
  Widget build(BuildContext context) {
    return const AndroidView(
      viewType: 'com.example.app/map',
      layoutDirection: TextDirection.ltr,
      creationParamsCodec: StandardMessageCodec(),
    );
  }
}
```

On the native side, implement `io.flutter.plugin.platform.PlatformView` to return the `android.view.View`, extend
`PlatformViewFactory` to build it, and register the factory in `configureFlutterEngine` with
`flutterEngine.platformViewsController.registry.registerViewFactory`.

If the native view uses `SurfaceView` or `SurfaceTexture`, call `invalidate` on it (or its parent) when the
content changes. Those classes do not invalidate themselves.

---

### Platform views on iOS and macOS

- iOS uses hybrid composition only. Implement `FlutterPlatformView` and `FlutterPlatformViewFactory` in Swift,
  register the factory in `application:didFinishLaunchingWithOptions:` or the plugin registrar, and use `UiKitView`
  on the Dart side.
- `ShaderMask` and `ColorFiltered` cannot be applied over an iOS platform view, and `BackdropFilter` composes with
  limitations.
- macOS uses hybrid composition over `NSView` and is not fully functional. Gesture support in particular is
  missing, so do not plan a macOS feature around it.

During a heavy Dart animation over a platform view, swap in a screenshot of the native view as a placeholder
texture and restore the live view when the animation ends.

---

### Web and WebAssembly

Compile to Wasm for better performance and real multi-threading:

```bash
flutter build web --wasm
```

- Multi-threading needs two response headers from the server: `Cross-Origin-Embedder-Policy: credentialless` (or
  `require-corp`) and `Cross-Origin-Opener-Policy: same-origin`.
- WasmGC is unavailable in iOS browsers because of a WebKit limitation. Flutter falls back to JavaScript there
  automatically, so both code paths must work.
- Write web-specific code with `package:web` and `dart:js_interop`. `dart:html`, `dart:js`, and `package:js` do
  not compile to Wasm at all.
- Inject arbitrary HTML with `HtmlElementView.fromTagName`.

---

### Embedding Flutter in a web page

Full page mode lets Flutter own the window. To constrain it without touching the bootstrap, put it in an iframe.

Embedded multi-view mode renders Flutter into specific elements. Initialize the engine with
`multiViewEnabled: true`, add and remove views from JavaScript with `app.addView()` and `app.removeView()`, and on
the Dart side replace `runApp` with `runWidget`, mapping
`WidgetsBinding.instance.platformDispatcher.views` into `View` widgets inside a `ViewCollection`.

```javascript
_flutter.loader.load({
  onEntrypointLoaded: async function (engineInitializer) {
    const engine = await engineInitializer.initializeEngine({ multiViewEnabled: true });
    const app = await engine.runApp();
    app.addView({ hostElement: document.querySelector('#flutter-host') });
  }
});
```

```dart
class _MultiViewAppState extends State<MultiViewApp> with WidgetsBindingObserver {
  Map<Object, Widget> _views = const {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _updateViews();
  }

  @override
  void didChangeMetrics() => _updateViews();

  void _updateViews() {
    final next = <Object, Widget>{};
    for (final view in WidgetsBinding.instance.platformDispatcher.views) {
      next[view.viewId] = _views[view.viewId] ??
          View(view: view, child: Builder(builder: widget.viewBuilder));
    }
    setState(() => _views = next);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) =>
      ViewCollection(views: _views.values.toList(growable: false));
}
```

---

### Checklist

- [ ] Channel names are constants on both sides and match exactly.
- [ ] The Dart side catches `PlatformException` and `MissingPluginException` and handles a null payload.
- [ ] The native handler ends with `notImplemented()` for unknown methods.
- [ ] Anything beyond a couple of methods uses Pigeon rather than a hand-written channel.
- [ ] Background isolates call `BackgroundIsolateBinaryMessenger.ensureInitialized` before touching a channel.
- [ ] FFI packages use the `package_ffi` template and generate bindings with `ffigen`.
- [ ] Exported C++ symbols carry the visibility and used attributes.
- [ ] The Android platform-view composition mode was chosen deliberately and the trade-off recorded.
- [ ] No `dart:html`, `dart:js`, or `package:js` anywhere, so the Wasm build compiles.
- [ ] The JavaScript fallback path was tested, because iOS browsers do not run WasmGC.
