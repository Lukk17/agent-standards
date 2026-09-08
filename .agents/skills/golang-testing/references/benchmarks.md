# Benchmarks, Fuzzing, and Coverage

Turning a performance claim into a number, finding the input nobody thought of, and reading a coverage profile.
Open this before optimising anything or when a parser handles untrusted bytes.

Baseline: Go 1.25, so `b.Loop` is available and is the form to use.

---

### Write the benchmark with b.Loop

`b.Loop` runs the body the right number of times, keeps the setup outside the measured region, and stops the compiler
from optimising away a result nobody uses. It replaces the older `for i := 0; i < b.N; i++` form and the manual
`b.ResetTimer` that went with it.

Pass:

```go
func BenchmarkProcess(b *testing.B) {
    data := generateTestData(1000)

    for b.Loop() {
        Process(data)
    }
}
```

Fail:

```go
func BenchmarkProcess(b *testing.B) {
    for i := 0; i < b.N; i++ {
        data := generateTestData(1000)
        Process(data)
    }
}
```

The failing version measures the fixture generation as well as the function, so the number answers a question nobody
asked.

---

### Report allocations, because they are usually the answer

Allocation count moves more than nanoseconds do, and it is stable across machines.

```bash
go test -bench=. -benchmem ./...
```

Add `b.ReportAllocs()` to a benchmark that should always report them, so the flag cannot be forgotten.

```go
func BenchmarkEncode(b *testing.B) {
    b.ReportAllocs()
    for b.Loop() {
        _ = Encode(payload)
    }
}
```

---

### Compare implementations with sub-benchmarks

Sub-benchmarks put competing implementations, or the same implementation at several sizes, in one output block where
they can be read against each other.

```go
func BenchmarkJoin(b *testing.B) {
    parts := []string{"hello", "world", "foo", "bar", "baz"}

    b.Run("concat", func(b *testing.B) {
        for b.Loop() {
            var s string
            for _, p := range parts {
                s += p
            }
        }
    })

    b.Run("builder", func(b *testing.B) {
        for b.Loop() {
            var sb strings.Builder
            for _, p := range parts {
                sb.WriteString(p)
            }
            _ = sb.String()
        }
    })

    b.Run("join", func(b *testing.B) {
        for b.Loop() {
            _ = strings.Join(parts, "")
        }
    })
}
```

Size sweeps follow the same shape, with `b.Run(fmt.Sprintf("size=%d", size), ...)` inside a loop over the sizes.

---

### Compare runs with benchstat, not by eye

A single run is noise. Take several runs of each version and let `benchstat` tell you whether the difference is real.

```bash
go test -bench=Process -benchmem -count=10 ./... > old.txt
```

```bash
benchstat old.txt new.txt
```

A change with a wide confidence interval is not a result. Quiet the machine, raise `-count`, and measure again before
claiming an improvement.

---

### Profile when the benchmark says there is something to find

The benchmark says how slow. The profile says where.

```bash
go test -bench=Process -cpuprofile=cpu.out ./internal/pipeline
```

```bash
go tool pprof -http=:8080 cpu.out
```

`-memprofile` does the same for allocations. Profile the benchmark rather than production first, because it is
reproducible and costs nothing to rerun.

---

### Fuzz anything that parses untrusted input

A fuzz target takes a seed corpus and generates variations, keeping any input that crashes or violates a property.
It is the cheapest way to find the parser bug that a table of hand-written cases never reaches.

```go
func FuzzParseJSON(f *testing.F) {
    f.Add(`{"name": "test"}`)
    f.Add(`{"count": 123}`)
    f.Add(`[]`)

    f.Fuzz(func(t *testing.T, input string) {
        var result map[string]any
        if err := json.Unmarshal([]byte(input), &result); err != nil {
            return
        }
        if _, err := json.Marshal(result); err != nil {
            t.Errorf("marshal failed after successful unmarshal: %v", err)
        }
    })
}
```

Run it for a bounded time in development:

```bash
go test -fuzz=FuzzParseJSON -fuzztime=30s ./...
```

Assert a property rather than an exact value, since you do not know the input. Round-tripping, ordering, and never
panicking are the usual three.

```go
f.Fuzz(func(t *testing.T, a, b string) {
    if Compare(a, b) != -Compare(b, a) {
        t.Errorf("Compare is not antisymmetric for %q and %q", a, b)
    }
})
```

A failing input is written to `testdata/fuzz/` and becomes a permanent regression test. Commit it.

---

### Read the coverage profile, not the headline

The percentage tells you nothing about which branch is untested. The per-function view does.

```bash
go test -race -coverprofile=coverage.out ./...
```

```bash
go tool cover -func=coverage.out
```

```bash
go tool cover -html=coverage.out
```

The target is around 90 percent of the real logic, 100 percent on critical business logic. Excluding code from
coverage is only for generated output such as protobuf stubs and generated mocks, never for hand-written logic.

Adding `-race` to the coverage run costs some time and finds the class of bug that no assertion will. Keep them
together in CI.

---

### Detect a flaky test by repeating it

Run each test several times and shuffle the order to expose a hidden dependency between them.

```bash
go test -count=10 ./...
```

```bash
go test -shuffle=on ./...
```

A test that fails under either is a defect in the test, not in the runner. Fix it or delete it, and never retry it
into passing.
