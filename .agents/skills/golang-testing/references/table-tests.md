# Table Tests, Subtests, and Golden Files

Table shapes for the cases a hub example does not cover: error paths, comparison of structs, grouped subtests, and
output compared against a checked-in file. Open this when a table is getting awkward.

Baseline: Go 1.25, so range variables are per-iteration and no `tt := tt` copy is needed.

---

### The standard table

Field order is name, inputs, expectations. A `want` field beats an `expected` field only because it lines up with the
`got X; want Y` failure message, and consistency there is worth more than the word.

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name string
        a, b int
        want int
    }{
        {"positive numbers", 2, 3, 5},
        {"negative numbers", -1, -2, -3},
        {"zero values", 0, 0, 0},
        {"mixed signs", -1, 1, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            if got := Add(tt.a, tt.b); got != tt.want {
                t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, got, tt.want)
            }
        })
    }
}
```

Use a map keyed by name instead of a slice when the order genuinely does not matter and you want Go to shuffle it for
you. Use a slice when a reader benefits from the cases being in a deliberate order.

---

### Error cases in the same table

Carry the expected error in the table rather than splitting the test in two. A `wantErr error` field matched with
`errors.Is` says more than a `wantErr bool`, because it checks which error rather than that there was one.

Pass:

```go
tests := []struct {
    name    string
    input   string
    want    *Config
    wantErr error
}{
    {name: "valid", input: `{"port": 8080}`, want: &Config{Port: 8080}},
    {name: "invalid JSON", input: `{oops}`, wantErr: ErrMalformed},
    {name: "empty input", input: "", wantErr: ErrEmpty},
}

for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        got, err := ParseConfig(tt.input)

        if !errors.Is(err, tt.wantErr) {
            t.Fatalf("ParseConfig(%q) error = %v; want %v", tt.input, err, tt.wantErr)
        }
        if tt.wantErr != nil {
            return
        }
        if diff := cmp.Diff(tt.want, got); diff != "" {
            t.Errorf("ParseConfig(%q) mismatch (-want +got):\n%s", tt.input, diff)
        }
    })
}
```

Fail:

```go
{name: "invalid JSON", input: `{oops}`, wantErr: true},
```

`errors.Is(nil, nil)` is true, so the same check covers the success cases and no separate branch is needed.

---

### Compare structs with cmp.Diff, not DeepEqual

`reflect.DeepEqual` answers yes or no. `cmp.Diff` prints the field that differs, which is the difference between a
one-minute fix and a debugging session. It also lets you ignore fields that are legitimately not comparable.

```go
if diff := cmp.Diff(want, got, cmpopts.IgnoreFields(User{}, "CreatedAt")); diff != "" {
    t.Errorf("mismatch (-want +got):\n%s", diff)
}
```

`cmp.Diff` panics on unexported fields unless you pass `cmp.AllowUnexported` or the type provides an `Equal` method.
Adding `Equal` to the type is usually the better answer, because production code benefits from it too.

---

### Group related subtests when they share setup

When several behaviours act on one expensive fixture, group them under one test function with nested `t.Run` calls.
The subtests run in order and share the fixture, which is the trade you are making.

```go
func TestUserStore(t *testing.T) {
    store := newStore(t)

    t.Run("create assigns an ID", func(t *testing.T) {
        user := &User{Name: "Alice"}
        if err := store.Create(t.Context(), user); err != nil {
            t.Fatalf("create: %v", err)
        }
        if user.ID == "" {
            t.Error("ID was not assigned")
        }
    })

    t.Run("get returns the created user", func(t *testing.T) {
        got, err := store.Get(t.Context(), "alice-id")
        if err != nil {
            t.Fatalf("get: %v", err)
        }
        if got.Name != "Alice" {
            t.Errorf("Name = %q; want %q", got.Name, "Alice")
        }
    })
}
```

Ordered subtests that depend on each other are a deliberate choice, not an accident. Say so in the subtest names, and
do not add `t.Parallel` to them.

---

### Golden files for large output

Comparing rendered output against a file in `testdata/` keeps the expectation readable and reviewable in a diff. The
`-update` flag regenerates it, so a deliberate change is one command and a reviewed diff.

```go
var update = flag.Bool("update", false, "update golden files")

func TestRender(t *testing.T) {
    tests := []struct {
        name  string
        input Template
    }{
        {"simple", Template{Name: "test"}},
        {"with items", Template{Name: "test", Items: []string{"a", "b"}}},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Render(tt.input)
            golden := filepath.Join("testdata", tt.name+".golden")

            if *update {
                if err := os.WriteFile(golden, got, 0o644); err != nil {
                    t.Fatalf("update golden: %v", err)
                }
            }

            want, err := os.ReadFile(golden)
            if err != nil {
                t.Fatalf("read golden: %v", err)
            }
            if !bytes.Equal(got, want) {
                t.Errorf("output mismatch:\ngot:\n%s\nwant:\n%s", got, want)
            }
        })
    }
}
```

Regenerate deliberately, then read the diff before committing:

```bash
go test ./... -update
```

`testdata/` is ignored by the Go tool, so anything in it is test material and never gets compiled or vendored. A
golden file that nobody reads in review is a rubber stamp, so keep them small enough to read.

---

### Keep the table declarative

The loop body is the test. When a case needs its own setup, put a function in the table rather than an `if` in the
body, or the table stops being a table.

Pass:

```go
tests := []struct {
    name  string
    setup func(t *testing.T) *Store
    want  int
}{
    {"empty store", newEmptyStore, 0},
    {"seeded store", newSeededStore, 3},
}
```

Fail:

```go
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        var store *Store
        if tt.name == "seeded store" {
            store = newSeededStore(t)
        } else {
            store = newEmptyStore(t)
        }
        ...
    })
}
```

Branching on the case name means the loop now encodes behaviour the table was supposed to describe.
