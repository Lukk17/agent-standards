# Go Checklist

Run it before calling a Go change or a Go review done. The rules behind each item are in [SKILL.md](../SKILL.md), and the test checklist is at the end of [testing.md](testing.md).

- [ ] Every exported type has a useful zero value, or an unexported field and a constructor.
- [ ] Functions accept interfaces and return concrete types, and interfaces are declared at the consumer.
- [ ] Every exported name has a doc comment that starts with its name, and unexported code follows the default of none.
- [ ] Every error a caller can act on is documented, including the sentinels it can match.
- [ ] Every returned error is wrapped with `%w` and a lowercase operation phrase, and none is silently dropped. An explicit `_ =` assignment appears only where nothing can be done.
- [ ] `context.Context` is the first parameter everywhere and is passed to every blocking call.
- [ ] Every goroutine has a defined way to stop, and dependencies arrive through a constructor.
- [ ] Slices are preallocated where the length is known and strings are built with a `Builder`.
- [ ] Every new behaviour has a test seen to fail, repeated cases are one table, and fakes are hand-written.
- [ ] `gofmt`, `go vet`, `golangci-lint run`, and `go test -race ./...` all pass, with around 90 percent coverage.
