# Performance Examples in Go

The pass and fail code in Go for running independent IO concurrently. Open this when the slow path is Go. The reasoning, and the two rules that hold in any language, are in [worked-examples.md](worked-examples.md).

---

### Run independent IO concurrently

Fail (Go): the same serial shape.

```go
profile, err := client.Profile(ctx, userID)
if err != nil {
    return err
}
orders, err := client.Orders(ctx, userID)
if err != nil {
    return err
}
```

Pass (Go): `errgroup` runs them together and returns the first error.

```go
var profile Profile
var orders []Order

g, ctx := errgroup.WithContext(ctx)
g.Go(func() (err error) { profile, err = client.Profile(ctx, userID); return err })
g.Go(func() (err error) { orders, err = client.Orders(ctx, userID); return err })
if err := g.Wait(); err != nil {
    return err
}
```
