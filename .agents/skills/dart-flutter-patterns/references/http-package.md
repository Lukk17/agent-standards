# package:http

Calling a REST API with `package:http`. Open this when `pubspec.yaml` lists `http`. The rules that hold for every client, and the table that picks one, are in [http-and-json.md](http-and-json.md).

---

### The short form

```dart
final response = await client.get(Uri.https('api.example.com', '/users/$id'));
if (response.statusCode != 200) {
  throw HttpException('GET /users/$id failed');
}
final user = User.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
```

---

### A service class

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
