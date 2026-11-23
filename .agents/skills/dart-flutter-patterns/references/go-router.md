# GoRouter

Declarative navigation with `go_router`: the route table, a reactive auth guard, shell routes and path parameters. Open this when the project uses GoRouter or needs deep links. Imperative navigation, nested navigators and the deep-link rules are in [routing-and-navigation.md](routing-and-navigation.md).

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
    if (!isLoggedIn && !isGoingToLogin) {
      return '/login';
    }
    if (isLoggedIn && isGoingToLogin) {
      return '/';
    }
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
