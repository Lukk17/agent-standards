# Provider and ChangeNotifier

State management with `ChangeNotifier` exposed through `Provider`. Open this when the project already uses it, or for one screen's local state. The rule that a feature uses one state manager is in [SKILL.md](../SKILL.md), and the table that picks between the options is in [architecture.md](architecture.md).

---

### When it fits

`ChangeNotifier` with `Provider` fits small apps and a single screen's local state. It is a first-class Flutter
class, not a deprecated one. It mutates in place, so keep the notified value immutable and replace it wholesale.

---

### The short form

```dart
class CartModel extends ChangeNotifier {
  List<CartItem> _items = const [];
  List<CartItem> get items => _items;
  void clear() { _items = const []; notifyListeners(); }
}
```

---

### A worked example

The example drives the same user profile screen as the ones in [riverpod.md](riverpod.md) and [bloc.md](bloc.md).

`ChangeNotifier` with `Provider`, for a small app or one screen's local state. It is a supported Flutter class, so
the only real constraint is that it mutates in place: hold an immutable value and replace it wholesale.

```dart
class UserModel extends ChangeNotifier {
  UserModel(this._repository);
  final UserRepository _repository;

  UserState _state = UserLoading();
  UserState get state => _state;

  Future<void> loadUser(String userId) async {
    _state = UserLoading();
    notifyListeners();
    try {
      _state = UserLoaded(await _repository.getUser(userId));
    } on Exception catch (e) {
      _state = UserFailed(e.toString());
    }
    notifyListeners();
  }
}

class UserProfileView extends StatelessWidget {
  const UserProfileView({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<UserModel>().state;
    return switch (state) {
      UserLoading() => const CircularProgressIndicator(),
      UserLoaded(:final user) => Text(AppLocalizations.of(context).greeting(user.name)),
      UserFailed(:final message) => ErrorView(message: message),
    };
  }
}
```
