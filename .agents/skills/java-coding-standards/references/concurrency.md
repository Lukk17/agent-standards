# Concurrency

How a Spring Boot service runs work in parallel on Java 21 or later. Open this when adding an executor, composing
asynchronous calls, or deciding whether a class is safe to share between threads.

---

### Virtual threads for anything that waits

Every I/O-bound task runs on a virtual thread. A virtual thread parks on a blocking call without holding a platform
thread, so the familiar blocking style scales to thousands of concurrent operations without a thread pool sized by
guesswork.

```java
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    List<Future<Quote>> futures = suppliers.stream()
        .map(supplier -> executor.submit(() -> client.fetchQuote(supplier)))
        .toList();
}
```

Keep platform threads for CPU-bound work, where a bounded pool sized to the available cores is still the right
shape. A virtual thread pinned to a CPU-bound loop buys nothing.

Two habits stop being harmless once virtual threads are in play. Do not pool virtual threads, because creating one
is cheap and a pool reintroduces the limit the threads exist to remove. Do not hold an intrinsic lock across a
blocking call, because that pins the carrier thread for the duration.

Spring Boot switches the web server and the task executors over with one property.

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

---

### Composing asynchronous work

Use `CompletableFuture` to compose pipelines, and always pass an explicit executor. The default `ForkJoinPool`
common pool is sized for CPU work and shared with everything else in the JVM, so an I/O task parked on it starves
unrelated code.

```java
CompletableFuture.supplyAsync(() -> fetchData(), ioExecutor)
    .thenApplyAsync(data -> transform(data), computeExecutor);
```

Terminate every chain. A `CompletableFuture` whose exceptional completion nobody handles fails silently, so end the
pipeline with `exceptionally`, `handle`, or a `join` inside a caller that reports the failure.

---

### Sharing data between threads

Pass immutable carriers. A record or a `@Value` class cannot be observed half-updated, which removes the entire
class of bug that publication and visibility rules exist to describe.

Where mutable state genuinely has to be shared, prefer the concurrent collections and the atomics in
`java.util.concurrent` over synchronising by hand, and confine the mutation to one class that owns it.

Document the thread-safety guarantee, or the absence of one, on every class reachable from more than one thread. A
reader cannot infer it, and the wrong assumption produces a defect that appears once a week under load and never in
a test.
