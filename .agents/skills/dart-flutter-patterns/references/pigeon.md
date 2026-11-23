# Pigeon

Type-safe platform channels generated from a Dart interface definition. Open this when a channel grows beyond one or two methods. Choosing between a channel, Pigeon, FFI and a platform view is in [native-interop-and-platform-views.md](native-interop-and-platform-views.md).

---

### Generate the channel

Prefer Pigeon over hand-written channels for anything beyond one or two methods. It removes the string method
names, the manual argument packing, and the drift between the two sides.

1. Add `pigeon` to `dev_dependencies`.
2. Define the data classes and an `@HostApi()` abstract class in `pigeons/messages.dart`.
3. Run the generator to emit the Dart, Kotlin, and Swift files.
4. Implement the generated interface in `MainActivity.kt` or your plugin class on Android.
5. Implement the generated protocol in `AppDelegate.swift` or your plugin class on iOS.
6. Import the generated Dart file and call the methods.
