# Go Concurrency

Worker pools, `errgroup`, cancellation, graceful shutdown, and the leak patterns that show up in production as memory
growth. Open this when a hub rule points here or when a goroutine has no obvious way to stop.

Baseline: Go 1.25, so range variables are per-iteration and no `tt := tt` copy is needed.

---

### Worker pool over a channel

A fixed number of workers reading one job channel bounds concurrency without a semaphore. The producer closes the job
channel, the workers exit their `range`, and the `WaitGroup` tells the owner when it is safe to close the results.

```go
func WorkerPool(jobs <-chan Job, results chan<- Result, workers int) {
    var wg sync.WaitGroup
    for range workers {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobs {
                results <- process(job)
            }
        }()
    }
    wg.Wait()
    close(results)
}
```

Only the sender closes a channel, and it closes it exactly once. A second close panics, and a send on a closed
channel panics too.

---

### errgroup for coordinated work that can fail

`errgroup.WithContext` cancels the derived context as soon as any goroutine returns an error, so the siblings stop
instead of finishing work nobody will read.

```go
func FetchAll(ctx context.Context, urls []string) ([][]byte, error) {
    g, ctx := errgroup.WithContext(ctx)
    results := make([][]byte, len(urls))

    for i, url := range urls {
        g.Go(func() error {
            data, err := fetch(ctx, url)
            if err != nil {
                return fmt.Errorf("fetch %s: %w", url, err)
            }
            results[i] = data
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }
    return results, nil
}
```

Writing to distinct indices of a preallocated slice needs no mutex. Appending to a shared slice from several
goroutines does, and is the most common data race in this shape of code.

Cap concurrency with `g.SetLimit(n)` when the work fans out over a resource that will not take unbounded parallelism.

---

### Give every blocking call a context

A context with a deadline turns a hung dependency into a returned error instead of a stuck goroutine.

```go
func FetchWithTimeout(ctx context.Context, url string) ([]byte, error) {
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
    if err != nil {
        return nil, fmt.Errorf("create request: %w", err)
    }

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("fetch %s: %w", url, err)
    }
    defer resp.Body.Close()

    return io.ReadAll(resp.Body)
}
```

`defer cancel()` is not optional. Skipping it leaks the timer and the context until the parent is cancelled.

---

### Close the leak: buffer or select

An unbuffered send with no receiver blocks forever. Either buffer the channel so the send always completes, or select
on the context so the goroutine gives up when nobody is listening.

Pass:

```go
func safeFetch(ctx context.Context, url string) <-chan []byte {
    ch := make(chan []byte, 1)
    go func() {
        data, err := fetch(ctx, url)
        if err != nil {
            return
        }
        select {
        case ch <- data:
        case <-ctx.Done():
        }
    }()
    return ch
}
```

Fail:

```go
func leakyFetch(ctx context.Context, url string) <-chan []byte {
    ch := make(chan []byte)
    go func() {
        data, _ := fetch(ctx, url)
        ch <- data
    }()
    return ch
}
```

The failing version leaks one goroutine and one payload per abandoned call, which is invisible until the process is
under load.

---

### Shut down gracefully

Stop accepting new work, give in-flight work a bounded window to finish, then exit. A hard exit drops requests that
were one write away from succeeding.

```go
func Run(srv *http.Server) error {
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

    go func() {
        if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
            slog.Error("listen", "err", err)
        }
    }()

    <-quit
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    return srv.Shutdown(ctx)
}
```

The signal channel must be buffered. `signal.Notify` does not block, so an unbuffered channel drops the signal.

---

### Guard shared state, or do not share it

The zero value of `sync.Mutex` is ready to use, so a mutex next to the field it protects needs no constructor. Keep
the lock unexported and never return the protected value by pointer.

```go
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}
```

Prefer designs where nothing is shared: each goroutine returns a value and the owner merges. Run `go test -race`
in CI, because the race detector finds what review does not.

---

### Reuse buffers only after a benchmark says so

`sync.Pool` cuts allocation in a genuinely hot path and adds indirection everywhere else. Reset the object before
returning it, or the next caller inherits your data.

```go
var bufferPool = sync.Pool{
    New: func() any { return new(bytes.Buffer) },
}

func process(data []byte) []byte {
    buf := bufferPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset()
        bufferPool.Put(buf)
    }()

    buf.Write(data)
    return bytes.Clone(buf.Bytes())
}
```

Returning `buf.Bytes()` directly hands the caller memory that is about to go back in the pool, which is why the
example clones it.
