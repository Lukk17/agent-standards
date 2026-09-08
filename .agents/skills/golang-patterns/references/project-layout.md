# Go Module and Package Layout

How a module is arranged, how packages are named, and how a constructor stays usable as its configuration grows.
Open this when starting a module or when a package has stopped having one job.

---

### Standard module layout

```text
myproject/
  cmd/myapp/main.go
  internal/handler/
  internal/service/
  internal/repository/
  internal/config/
  pkg/client/
  api/v1/
  testdata/
  go.mod
  Makefile
```

`cmd/<name>/main.go` wires dependencies and does nothing else. `internal/` is enforced by the compiler: nothing
outside the module can import it, which is the cheapest way to keep a package private until its API is settled. Use
`pkg/` only for code you intend other modules to import, and be honest about that, because everything in it is a
public commitment.

A single-binary project with a handful of files does not need this tree. Start flat and split when a package acquires
a second reason to change.

---

### Name packages for what they provide

A package name is a prefix on every identifier in it, so `user.UserService` reads as a stutter and `user.Service`
reads correctly.

Pass:

```go
package user

type Service struct{}
```

Fail:

```go
package userService

type UserService struct{}
```

Names are short, lowercase, and single-word. No underscores, no mixed case, and never `util`, `common`, `helpers`, or
`base`: a package with a name that vague accumulates everything nobody could place, and then everything imports it.

---

### Keep the import graph acyclic and shallow

Go rejects an import cycle at compile time, and the usual fix is the right one: move the shared type down into a
package both sides can import, or invert the dependency with an interface declared at the consumer.

Pass:

```go
package service

type UserStore interface {
    Get(ctx context.Context, id string) (*User, error)
}
```

Fail:

```go
package service

import "myproject/internal/repository"

type Service struct {
    repo *repository.PostgresUserRepository
}
```

The failing version binds the business logic to one storage implementation, so the test needs a database and the
package cannot be reused.

---

### Functional options for a constructor with many settings

Options keep the constructor's required arguments positional, make every optional setting named at the call site, and
let a new setting be added without breaking any caller.

```go
type Server struct {
    addr    string
    timeout time.Duration
    logger  *slog.Logger
}

type Option func(*Server)

func WithTimeout(d time.Duration) Option {
    return func(s *Server) { s.timeout = d }
}

func WithLogger(l *slog.Logger) Option {
    return func(s *Server) { s.logger = l }
}

func NewServer(addr string, opts ...Option) *Server {
    s := &Server{addr: addr, timeout: 30 * time.Second, logger: slog.Default()}
    for _, opt := range opts {
        opt(s)
    }
    return s
}
```

```go
srv := NewServer(":8080", WithTimeout(60*time.Second), WithLogger(logger))
```

Two or three settings do not need this. A config struct passed by value is simpler and is the better answer until the
option list grows or a setting has to be validated.

---

### Embed for composition, not for inheritance

Embedding promotes the embedded type's methods onto the outer type. That is composition, and it is right when the
outer type genuinely is a superset of the inner behaviour.

```go
type Server struct {
    *slog.Logger
    addr string
}
```

It is wrong when it exports methods the outer type does not want in its API, which happens the moment you embed a
large struct to save typing. Prefer a named field and explicit delegation whenever only some of the methods belong.

Pass:

```go
type Service struct {
    store UserStore
}

func (s *Service) Get(ctx context.Context, id string) (*User, error) {
    return s.store.Get(ctx, id)
}
```

Fail:

```go
type Service struct {
    UserStore
}
```

---

### Keep the exported surface small

Export a type, a function, or a field only when something outside the package calls it. Every exported name is a
promise, and unexporting one later is a breaking change.

Give each package a single `doc.go` or a package comment on one file only, so `go doc` has one description rather
than several competing ones.

---

### One module unless there is a reason for more

A multi-module repository means separate `go.mod` files, separate version tags, and a dependency between them that
has to be released to be tested. Split only when parts genuinely version independently, such as a client library
consumed by outside teams.

```bash
go mod tidy
```

Commit `go.mod` and `go.sum` together, and verify the checksums in CI:

```bash
go mod verify
```
