# Routing and Navigation

Choosing between imperative and declarative navigation, wiring GoRouter with a reactive auth guard, running a
nested sub-flow, and handling deep links.

---

### Core concepts

- A route is a widget. It plays the role that `Activity` plays on Android and `ViewController` on iOS.
- `Navigator` is the imperative API and manages a stack of `Route` objects. It suits small apps with no deep
  linking.
- `Router` is the declarative API. Use it, through a package such as `go_router`, whenever the app needs deep
  links, browser URL synchronization, or non-trivial redirect logic.
- Named routes (`MaterialApp.routes` with `Navigator.pushNamed`) are a dead end. Their deep-link behaviour is
  rigid and the browser forward button does not work. Use a routing package instead.
- Declarative routes are page-backed and therefore deep-linkable. Imperative pushes such as dialogs and bottom
  sheets are pageless, and removing a page-backed route removes every pageless route stacked on it.

---

### Imperative navigation

Push with `Navigator.push(context, route)` and return with `Navigator.pop(context)`. Use `pushReplacement` to
swap the current route and `pushAndRemoveUntil` to clear the stack to a predicate.

Pass data forward through the destination widget's constructor. `RouteSettings(arguments: data)` with
`ModalRoute.of(context)?.settings.arguments` works, but it is untyped, so keep it for the cases where the
destination is chosen dynamically.

Return data by passing it to `pop` and awaiting the push.

```dart
class TodoListPage extends StatelessWidget {
  const TodoListPage({super.key, required this.todos});
  final List<Todo> todos;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(AppLocalizations.of(context).todosTitle)),
      body: ListView.builder(
        itemCount: todos.length,
        itemBuilder: (context, index) => ListTile(
          title: Text(todos[index].title),
          onTap: () async {
            final edited = await Navigator.push<Todo>(
              context,
              MaterialPageRoute(builder: (_) => TodoDetailPage(todo: todos[index])),
            );
            if (edited == null) return;
            context.read<TodoCubit>().save(edited);
          },
        ),
      ),
    );
  }
}
```

---

### Declarative navigation with GoRouter

Switch `MaterialApp` to `MaterialApp.router`, define the route table once, and navigate with `context.go` for a
replace or `context.push` for a stack push.

`refreshListenable` is what makes the guard reactive: without it the `redirect` callback only runs on a
navigation, so a token expiring in the background leaves the user on a protected screen.

```dart
final router = GoRouter(
  initialLocation: '/',
  refreshListenable: GoRouterRefreshStream(authCubit.stream),
  redirect: (context, state) {
    final isLoggedIn = context.read<AuthCubit>().state is AuthAuthenticated;
    final isGoingToLogin = state.matchedLocation == '/login';
    if (!isLoggedIn && !isGoingToLogin) return '/login';
    if (isLoggedIn && isGoingToLogin) return '/';
    return null;
  },
  routes: [
    GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
    ShellRoute(
      builder: (context, state, child) => AppShell(child: child),
      routes: [
        GoRoute(path: '/', builder: (_, __) => const HomePage()),
        GoRoute(
          path: '/products/:id',
          builder: (context, state) => ProductDetailPage(
            id: state.pathParameters['id'] ?? '',
          ),
        ),
      ],
    ),
  ],
);
```

Read a path parameter through `?? ''` or an explicit guard rather than `!`. A malformed deep link is user input,
and user input must not crash the app.

---

### Nested navigation

Use a nested `Navigator` for a sub-flow that owns its own back stack, such as a multi-step setup wizard or a tab
that keeps its history. `ShellRoute` and `StatefulShellRoute` in GoRouter cover most of these cases and stay
deep-linkable, so reach for a raw nested `Navigator` only when the sub-flow genuinely should not appear in the URL.

```dart
class _SetupFlowState extends State<SetupFlow> {
  final _navigatorKey = GlobalKey<NavigatorState>();

  void _exitSetup() => Navigator.of(context).pop();

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (didPop) return;
        _exitSetup();
      },
      child: Scaffold(
        appBar: AppBar(title: Text(AppLocalizations.of(context).setupTitle)),
        body: Navigator(
          key: _navigatorKey,
          initialRoute: widget.initialRoute,
          onGenerateRoute: _onGenerateRoute,
        ),
      ),
    );
  }

  Route<Widget> _onGenerateRoute(RouteSettings settings) {
    final page = switch (settings.name) {
      'step1' => StepOnePage(onComplete: () => _navigatorKey.currentState?.pushNamed('step2')),
      'step2' => StepTwoPage(onComplete: _exitSetup),
      _ => throw StateError('Unexpected route name: ${settings.name}'),
    };
    return MaterialPageRoute(builder: (_) => page, settings: settings);
  }
}
```

`PopScope` intercepts the hardware back button so the top-level navigator does not pop the whole flow. Any exit
confirmation text goes through `AppLocalizations`, never a literal. `currentState` is nullable, so use `?.` rather
than `!`.

---

### Deep linking

- Use GoRouter path parameters for universal links (iOS) and app links (Android). The web target needs no extra
  configuration.
- Register the URL schemes in `Info.plist` on iOS and `AndroidManifest.xml` on Android.
- Test cold start (app not running) and warm start (app backgrounded) separately. They take different code paths
  and cold start is the one that usually breaks.
- Treat every path and query parameter as untrusted input. Validate before use and redirect to a safe route on
  failure.

---

### Checklist

- [ ] No named routes through `MaterialApp.routes` outside a throwaway prototype.
- [ ] `MaterialApp.router` is used wherever deep links or web URLs matter.
- [ ] The auth `redirect` is driven by a `refreshListenable`, not only by navigation events.
- [ ] Path and query parameters are read with a guard, never with `!`.
- [ ] Nested flows wrap their host in `PopScope` and pass localized confirmation text.
- [ ] Both cold-start and warm-start deep links were exercised on a real device.
