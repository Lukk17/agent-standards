# Go Tooling

The commands a Go project runs and the `golangci-lint` v2 configuration that backs them. Open this when setting a
repository up, or when a v1 configuration file has started failing.

Baseline: Go 1.25 and golangci-lint v2. Confirm both with `go version` and `golangci-lint version` before assuming.

---

### Build, run, and format

Build every package in the module:

```bash
go build ./...
```

Run a command:

```bash
go run ./cmd/myapp
```

Format the tree, which is not negotiable and has no options to argue about:

```bash
gofmt -w .
```

Fix and group imports as well:

```bash
goimports -w .
```

---

### Vet and lint

`go vet` ships with the toolchain and catches the mistakes the compiler allows, such as a printf verb that does not
match its argument:

```bash
go vet ./...
```

`golangci-lint` runs the wider set, including `go vet` itself:

```bash
golangci-lint run
```

Apply the fixes the enabled linters can make safely:

```bash
golangci-lint run --fix
```

---

### golangci-lint v2 configuration

Version 2 changed the schema. A v1 file fails on startup rather than degrading, so it has to be converted rather than
left alone.

```yaml
version: "2"

linters:
  default: standard
  enable:
    - misspell
    - unconvert
    - unparam
  settings:
    errcheck:
      check-type-assertions: true
    govet:
      enable:
        - shadow
  exclusions:
    presets:
      - comments
      - std-error-handling

formatters:
  enable:
    - gofmt
    - goimports
```

What changed from v1, and why a v1 file no longer loads:

| v1 | v2 |
| --- | --- |
| No `version` key | `version: "2"` is required as the first key |
| `linters-settings:` at the top level | `linters.settings:` nested under `linters` |
| `issues.exclude-use-default: false` | Removed. Default exclusions are opt-in through `linters.exclusions.presets` |
| `govet.check-shadowing: true` | Removed. Enable the analyzer with `govet.enable: [shadow]` |
| `gosimple` as its own linter | Merged into `staticcheck`, which now reports its checks |
| `gofmt` and `goimports` under `linters` | Moved to the top-level `formatters` section |

`default: standard` enables `errcheck`, `govet`, `ineffassign`, `staticcheck`, and `unused`, so those need no entry
under `enable`. Listing them again is harmless but says nothing.

Convert an existing file rather than rewriting it by hand:

```bash
golangci-lint migrate
```

---

### Test and race

Run the suite:

```bash
go test ./...
```

Run it with the race detector, which is the setting CI uses because it finds what review does not:

```bash
go test -race ./...
```

Test discipline beyond running the command, meaning table tests, fakes, benchmarks, fuzzing, and the coverage target,
is in [testing.md](testing.md) and the sibling files it lists.

---

### Modules and supply chain

Add missing requirements and drop unused ones:

```bash
go mod tidy
```

Verify that the downloaded modules match `go.sum`:

```bash
go mod verify
```

Report known vulnerabilities in the module graph and, where it can, whether your code actually reaches them:

```bash
govulncheck ./...
```

Commit `go.mod` and `go.sum` in the same change as the code that needed them. A tidy that lands separately makes the
build non-reproducible for everyone who checks out in between.

---

### CI gate

The pipeline runs the same commands a developer runs, one per step, so a failure names itself.

```yaml
- run: go build ./...
- run: go vet ./...
- run: golangci-lint run
- run: go test -race -coverprofile=coverage.out ./...
- run: govulncheck ./...
```

Pin the Go version in the workflow to the same release `go.mod` declares, so a toolchain bump is a reviewed change
rather than a surprise on a Monday.
