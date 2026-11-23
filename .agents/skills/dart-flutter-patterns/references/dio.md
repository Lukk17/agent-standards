# package:dio

Calling a REST API with `package:dio`, with interceptors and token refresh. Open this when `pubspec.yaml` lists `dio`. The rules that hold for every client, and the table that picks one, are in [http-and-json.md](http-and-json.md).

---

### The short form

```dart
final response = await dio.get<Map<String, dynamic>>('/users/$id');
final data = response.data;
if (data == null) {
  throw ApiException('GET /users/$id returned no body');
}
final user = User.fromJson(data);
```

---

### Interceptors, token refresh and a data source

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
    if (data == null) {
      throw ApiException('GET /users/$id returned no body');
    }
    return User.fromJson(data);
  }
}
```

The `_isRetry` flag is the important detail. Without it a refresh that itself returns 401 recurses until the app
runs out of stack.
