# json_serializable

Generated JSON serialization with `json_serializable`, which `freezed` wraps. Open this when a model crosses the wire. Parsing a large payload off the main isolate is in [http-and-json.md](http-and-json.md).

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
