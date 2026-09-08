# HTTP and JSON

Calling REST APIs with either `package:http` or `package:dio`, serializing JSON with code generation, and keeping
large payloads off the UI isolate.

---

### Rules that apply to both clients

- Use HTTPS. iOS and Android block cleartext by default. If a debug build genuinely needs plain HTTP, scope it to
  one host through `network_security_config.xml` on Android and `NSAppTransportSecurity` on iOS, and never ship it.
- Build URLs with `Uri.https(authority, path, queryParameters)`. String concatenation gets the encoding wrong the
  first time someone passes a space or an ampersand.
- Check the status code and throw a typed exception. Never return `null` to mean failure, because the caller has
  no way to tell it apart from a legitimately absent value.
- Keep tokens out of source. Read them from secure storage at request time, and inject the base URL through
  `--dart-define`.
- Parse anything large on a background isolate. See [concurrency.md](concurrency.md).

---

### Choosing the client

Match what the project already uses. If `pubspec.yaml` has neither, pick on this basis:

| Consideration | `package:http` | `package:dio` |
| --- | --- | --- |
| Size and dependency weight | Smaller | Larger |
| Documented by the Flutter team | Yes | No |
| Interceptors for auth, logging, retry | Write your own wrapper | Built in |
| Request cancellation | Not built in | `CancelToken` |
| Typed errors with the failed request attached | Manual | `DioException` |
| Form data, multipart, download progress | Manual | Built in |

`http` is the right default for a handful of endpoints. `dio` earns its weight once you need token refresh,
per-request cancellation, or uniform logging.

---

### package:http

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class AlbumApi {
  const AlbumApi(this._client);
  final http.Client _client;

  Future<Album> fetch(int id) async {
    final uri = Uri.https('jsonplaceholder.typicode.com', '/albums/$id');
    final response = await _client.get(uri);
    if (response.statusCode != 200) {
      throw ApiException('GET $uri failed with ${response.statusCode}');
    }
    return Album.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<Album> create(String title) async {
    final uri = Uri.https('jsonplaceholder.typicode.com', '/albums');
    final response = await _client.post(
      uri,
      headers: const {'Content-Type': 'application/json; charset=UTF-8'},
      body: jsonEncode({'title': title}),
    );
    if (response.statusCode != 201) {
      throw ApiException('POST $uri failed with ${response.statusCode}');
    }
    return Album.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }
}
```

Inject `http.Client` rather than calling the top-level `http.get`. It is what makes the class testable and it lets
you close the connection pool on dispose.

Add the internet permission to `AndroidManifest.xml` and the macOS entitlements before the first request, because
the failure mode on macOS is a confusing socket error rather than a permission message.

---

### package:dio

```dart
final dio = Dio(BaseOptions(
  baseUrl: const String.fromEnvironment('API_URL'),
  connectTimeout: const Duration(seconds: 10),
  receiveTimeout: const Duration(seconds: 30),
  headers: const {'Content-Type': 'application/json'},
));

dio.interceptors.add(InterceptorsWrapper(
  onRequest: (options, handler) async {
    final token = await secureStorage.read(key: 'auth_token');
    if (token != null) options.headers['Authorization'] = 'Bearer $token';
    handler.next(options);
  },
  onError: (error, handler) async {
    final isRetry = error.requestOptions.extra['_isRetry'] == true;
    if (!isRetry && error.response?.statusCode == 401) {
      final refreshed = await attemptTokenRefresh();
      if (refreshed) {
        error.requestOptions.extra['_isRetry'] = true;
        return handler.resolve(await dio.fetch(error.requestOptions));
      }
    }
    handler.next(error);
  },
));

class UserApiDataSource {
  const UserApiDataSource(this._dio);
  final Dio _dio;

  Future<User> getById(String id) async {
    final response = await _dio.get<Map<String, dynamic>>('/users/$id');
    final data = response.data;
    if (data == null) throw ApiException('GET /users/$id returned no body');
    return User.fromJson(data);
  }
}
```

The `_isRetry` flag is the important detail. Without it a refresh that itself returns 401 recurses until the app
runs out of stack.

---

### JSON serialization

Generate it. `json_serializable`, or `freezed` which wraps it, keeps `fromJson`, `toJson`, and `==` in sync as
fields change. Hand-written `fromJson` is an escape hatch for a throwaway prototype model, and the moment that
model is kept or grows a nested field it should be generated.

```dart
import 'package:json_annotation/json_annotation.dart';

part 'user.g.dart';

@JsonSerializable(explicitToJson: true)
class User {
  const User(this.name, this.registrationDateMillis);

  final String name;

  @JsonKey(name: 'registration_date_millis')
  final int registrationDateMillis;

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
  Map<String, dynamic> toJson() => _$UserToJson(this);
}
```

Set `explicitToJson: true` whenever the class holds a nested model, otherwise the nested object serializes as an
instance reference rather than a map. Store and transmit timestamps in UTC and convert to local time only at the
UI edge.

Add the runtime annotation package once:

```bash
flutter pub add json_annotation
```

Add the generator to dev dependencies:

```bash
flutter pub add -d build_runner json_serializable
```

Then regenerate after every model change:

```bash
dart run build_runner build --delete-conflicting-outputs
```

---

### Parsing large payloads off the main isolate

Anything that takes more than a frame to decode belongs on another isolate. The parse function must be top-level
or static so it can be sent across the isolate boundary.

```dart
List<Photo> parsePhotos(String responseBody) {
  final parsed = (jsonDecode(responseBody) as List<Object?>).cast<Map<String, Object?>>();
  return parsed.map(Photo.fromJson).toList();
}

Future<List<Photo>> fetchPhotos(http.Client client) async {
  final uri = Uri.https('jsonplaceholder.typicode.com', '/photos');
  final response = await client.get(uri);
  if (response.statusCode != 200) throw ApiException('GET $uri failed');
  return Isolate.run(() => parsePhotos(response.body));
}
```

`compute` still works and reads slightly better in a widget-facing API. `Isolate.run` is the general-purpose
version and does not need `package:flutter/foundation.dart`.

---

### Checklist

- [ ] One HTTP client across the app, matching `pubspec.yaml`.
- [ ] Every URL is built with `Uri.https`, never concatenated.
- [ ] Every non-success status code throws a typed exception rather than returning null.
- [ ] The client is injected, not called as a top-level function, so tests can substitute it.
- [ ] Token refresh has a retry guard so a failing refresh cannot loop.
- [ ] Models are generated with `json_serializable` or `freezed`, with `explicitToJson` where nested.
- [ ] Decodes larger than a frame budget run through `Isolate.run` or `compute`.
- [ ] No base URL, API key, or token is written into source.
