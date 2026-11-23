# Go Tooling

The commands a Go project runs. Open this when setting a repository up. The linter those commands sit beside, and the
configuration that backs it, are in [golangci-lint.md](golangci-lint.md).

Written for Go 1.27. Confirm with `go version` before assuming.

---

### Contents

- [Build, run, and format](#build-run-and-format)
- [Vet](#vet)
- [Modernise after a toolchain bump](#modernise-after-a-toolchain-bump)
- [Test and race](#test-and-race)
- [Modules and supply chain](#modules-and-supply-chain)
- [CI gate](#ci-gate)

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

### Vet

`go vet` ships with the toolchain and catches the mistakes the compiler allows, such as a printf verb that does not
match its argument:

```bash
go vet ./...
```

`golangci-lint` runs the wider set, including `go vet` itself. Its commands and configuration are in
[golangci-lint.md](golangci-lint.md).

---

### Modernise after a toolchain bump

`go fix` is the home of Go's modernizers. After raising the `go` line in `go.mod`, run it once and review the diff as its own commit, so its rewrites to the newer idioms and library APIs are not buried in a feature change:

```bash
go fix ./...
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
