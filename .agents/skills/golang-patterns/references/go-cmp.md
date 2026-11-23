# go-cmp

Comparing structs in a test with `cmp.Diff` from `github.com/google/go-cmp`. Open this when a test compares more than a scalar. The table shapes it is used in are in [table-tests.md](table-tests.md).

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
