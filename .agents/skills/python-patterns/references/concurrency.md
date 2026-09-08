# Python Concurrency

Thread pools, process pools, and asyncio, with the cancellation and error handling that make each of them safe.
Open this after the hub rule has told you which model the bottleneck calls for.

---

### Thread pool for blocking I/O

Threads are right when a library gives you no async API and the call spends its time waiting on a socket or a disk.
Bound the pool, because an unbounded one just moves the queue into the remote service.

```python
def fetch_all(urls: list[str]) -> dict[str, str | Exception]:
    results: dict[str, str | Exception] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_url, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                results[url] = future.result()
            except OSError as exc:
                results[url] = exc
    return results
```

Call `future.result()` on every future you submit. A future whose exception is never retrieved fails silently.

---

### Process pool for CPU-bound work

Processes sidestep the interpreter lock but pay for pickling every argument and every result. That trade only wins
when the computation per call is large compared with the payload.

```python
def process_all(datasets: list[list[int]]) -> list[int]:
    with ProcessPoolExecutor() as executor:
        return list(executor.map(sum_of_squares, datasets))
```

The target function must be importable at module level: a lambda or a closure cannot be pickled. On Windows and
macOS the child re-imports the module, so guard the entry point.

```python
if __name__ == "__main__":
    main()
```

---

### TaskGroup for concurrent awaits

`asyncio.TaskGroup` waits for every child, cancels the siblings when one fails, and raises an `ExceptionGroup`
carrying the failures. It replaces `asyncio.gather` for new code.

Pass:

```python
async def fetch_all(urls: list[str]) -> list[str]:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(fetch(url)) for url in urls]
    return [task.result() for task in tasks]
```

Fail:

```python
async def fetch_all(urls: list[str]) -> list[str]:
    results = await asyncio.gather(*(fetch(url) for url in urls), return_exceptions=True)
    return results
```

The failing version returns exception objects as if they were results, so the caller carries them further into the
system before anything notices.

---

### Handle the failures a TaskGroup raises

A group raises `ExceptionGroup`, not the individual error. Use `except*` to handle each kind.

```python
try:
    await load_everything()
except* TimeoutError as group:
    logger.warning("timed out: %d call(s)", len(group.exceptions))
except* HTTPError as group:
    raise UpstreamError("dependency rejected the request") from group
```

---

### Bound concurrency with a semaphore

An unbounded task group against one host is a self-inflicted denial of service. A semaphore caps in-flight work
without changing the shape of the code.

```python
async def fetch_all(urls: list[str], limit: int = 10) -> list[str]:
    semaphore = asyncio.Semaphore(limit)

    async def guarded(url: str) -> str:
        async with semaphore:
            return await fetch(url)

    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(guarded(url)) for url in urls]
    return [task.result() for task in tasks]
```

---

### Always give an await a timeout

`asyncio.timeout` cancels the block and raises `TimeoutError`, so a stalled dependency cannot pin a request forever.

```python
async def load_profile(user_id: str) -> Profile:
    async with asyncio.timeout(5):
        return await profile_client.get(user_id)
```

---

### Never block the event loop

One synchronous call inside a coroutine stalls every other task in the process. Push blocking work to a thread with
`asyncio.to_thread`.

Pass:

```python
async def hash_password(password: str) -> str:
    return await asyncio.to_thread(bcrypt_hash, password)
```

Fail:

```python
async def hash_password(password: str) -> str:
    return bcrypt_hash(password)
```

The same rule covers `time.sleep`, `requests.get`, and any ORM call that is not the async variant.

---

### Keep shared mutable state behind a lock or out of reach

Threads sharing a dict, a counter, or a cached client need a lock. The better answer is usually to have each worker
return a value and let the caller merge, so there is nothing shared to protect.

```python
class Counter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._count = 0

    def increment(self) -> None:
        with self._lock:
            self._count += 1
```

In asyncio use `asyncio.Lock`, never `threading.Lock`: the threading lock blocks the whole event loop while it waits.
