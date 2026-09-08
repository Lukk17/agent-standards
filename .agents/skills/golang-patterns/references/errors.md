# Go Error Handling

Sentinels, custom error types, matching, joining, and the narrow cases where a panic is correct. Open this when an
error needs to be more than a wrapped message.

---

### Define sentinels for conditions a caller branches on

A sentinel is a package-level `error` a caller can match with `errors.Is` through any depth of wrapping. Declare one
only for a condition a caller genuinely handles differently.

```go
var (
    ErrNotFound     = errors.New("resource not found")
    ErrUnauthorized = errors.New("unauthorized")
    ErrInvalidInput = errors.New("invalid input")
)
```

Name every sentinel a function can return in that function's doc comment. The signature says only `error`, so the
comment is the only contract a caller has.

---

### Use a custom type when the error carries data

A struct error carries fields the caller can read. Implement `Error() string`, and `Unwrap() error` whenever it wraps
a cause.

```go
type ValidationError struct {
    Field   string
    Message string
    cause   error
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Message)
}

func (e *ValidationError) Unwrap() error { return e.cause }
```

Return `*ValidationError` as an `error`, never as a concrete type, or a nil pointer stored in an interface makes
`err != nil` true when there is no error.

Pass:

```go
func Validate(u User) error {
    if u.Email == "" {
        return &ValidationError{Field: "email", Message: "required"}
    }
    return nil
}
```

Fail:

```go
func Validate(u User) *ValidationError {
    return nil
}
```

---

### Match with errors.Is and errors.As

`errors.Is` compares against a sentinel. `errors.As` extracts a typed error from anywhere in the chain. Neither works
on a `==` comparison once the error has been wrapped, which is why wrapping and matching go together.

```go
func handle(err error) {
    if errors.Is(err, sql.ErrNoRows) {
        return
    }

    var validationErr *ValidationError
    if errors.As(err, &validationErr) {
        slog.Warn("invalid input", "field", validationErr.Field)
        return
    }

    slog.Error("unexpected", "err", err)
}
```

Pass the address of a pointer variable to `errors.As`. Passing the value itself panics.

---

### Wrap with %w, format with %v

`%w` records the cause and keeps it matchable. `%v` renders the message and discards the chain, which is right only
when you deliberately do not want the caller to match the underlying error.

Pass:

```go
return fmt.Errorf("load config %s: %w", path, err)
```

Fail:

```go
return fmt.Errorf("load config %s: %v", path, err)
```

Wrapping a third-party error with `%w` makes that library's error types part of your package's contract. Where that
is not wanted, translate it into your own sentinel and use `%v` for the detail.

---

### Join independent failures

`errors.Join` collects several failures into one error that `errors.Is` still matches against each of them. It is the
right shape for validation, where the caller wants every problem rather than the first.

```go
func Validate(u User) error {
    var errs []error
    if u.Email == "" {
        errs = append(errs, fmt.Errorf("email: %w", ErrInvalidInput))
    }
    if u.Age < 0 {
        errs = append(errs, fmt.Errorf("age: %w", ErrInvalidInput))
    }
    return errors.Join(errs...)
}
```

`errors.Join` returns nil when every argument is nil, so the empty case needs no special handling.

---

### Return errors, do not panic

A panic crosses every boundary between the failure and the top of the goroutine, which makes it useless as control
flow and dangerous in a server. Reserve it for a programmer error that cannot be recovered from, such as an
impossible state in a constructor invoked at init time.

Pass:

```go
func GetUser(id string) (*User, error) {
    user, err := db.Find(id)
    if err != nil {
        return nil, fmt.Errorf("get user %s: %w", id, err)
    }
    return user, nil
}
```

Fail:

```go
func GetUser(id string) *User {
    user, err := db.Find(id)
    if err != nil {
        panic(err)
    }
    return user
}
```

An HTTP server should still recover at the handler boundary so one bad request cannot take the process down, and log
the stack when it does.

---

### Keep the error path unindented

Handle the failure and return, so the happy path stays at one level of indentation and reads straight down.

Pass:

```go
user, err := store.Get(ctx, id)
if err != nil {
    return nil, fmt.Errorf("get user: %w", err)
}
return user.Profile(), nil
```

Fail:

```go
user, err := store.Get(ctx, id)
if err == nil {
    return user.Profile(), nil
} else {
    return nil, err
}
```

---

### Log an error once, at the boundary

An error logged in the function that produced it and again in every caller produces one incident with five stack
traces and no single truth. Wrap on the way up, log where the request or job ends.

Pass:

```go
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    if err := h.process(r.Context()); err != nil {
        slog.ErrorContext(r.Context(), "process request", "err", err)
        http.Error(w, "internal error", http.StatusInternalServerError)
    }
}
```

Fail:

```go
func (s *Service) process(ctx context.Context) error {
    if err := s.store.Save(ctx); err != nil {
        slog.Error("save failed", "err", err)
        return err
    }
    return nil
}
```
