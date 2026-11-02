# Outbound HTTP and Resilience

Configuration for calling another service and surviving its bad days. Open this when adding an HTTP client, tuning
retries, or deciding what a circuit breaker should do when it opens.

---

### RestClient bean

```java
@Bean
public RestClient marketApiClient(RestClient.Builder builder) {
    SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
    factory.setConnectTimeout(Duration.ofSeconds(2));
    factory.setReadTimeout(Duration.ofSeconds(5));
    return builder
        .baseUrl("https://api.example.com")
        .requestFactory(factory)
        .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
        .build();
}
```

```java
ResponseEntity<UserDto> response = marketApiClient.get()
    .uri("/users/{id}", userId)
    .retrieve()
    .toEntity(UserDto.class);
```

Both timeouts are mandatory. A client with no read timeout waits forever, so one slow dependency consumes every
request thread and the outage propagates to callers that never touched that dependency.

Declare one bean per upstream, each with its own base URL and its own timeouts, rather than one shared client whose
settings are a compromise between unrelated services.

---

### Retry and circuit breaker

```java
@Service
public class ExternalApiClient {
    @Retry(name = "externalApi")
    @CircuitBreaker(name = "externalApi", fallbackMethod = "fallback")
    public ResponseEntity<String> call() {
        return restClient.get().uri("/endpoint").retrieve().toEntity(String.class);
    }

    public ResponseEntity<String> fallback(Exception ex) {
        return ResponseEntity.status(503).body("Service unavailable");
    }
}
```

```yaml
resilience4j:
  retry:
    instances:
      externalApi:
        max-attempts: 3
        wait-duration: 500ms
        enable-exponential-backoff: true
        exponential-backoff-multiplier: 2
        enable-randomized-wait: true
        randomized-wait-factor: 0.5
  circuitbreaker:
    instances:
      externalApi:
        sliding-window-size: 10
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
```

What each setting is doing:

- `max-attempts: 3` means one call and two retries. More attempts against a failing dependency multiply the load
  that is already breaking it.
- Exponential backoff spreads the retries apart, and the randomized wait factor keeps a hundred callers from
  retrying in the same millisecond after a shared failure.
- The circuit opens once half the calls in the sliding window fail, so the caller stops waiting on a dependency
  that is clearly down and starts failing fast instead.
- `wait-duration-in-open-state` is how long the circuit stays open before it lets a probe through.

Retry only idempotent operations. Retrying a payment or a non-idempotent POST creates duplicates, so make the
operation idempotent first, with an idempotency key, and only then add the retry.

---

### What a fallback should do

A fallback degrades the response, it does not fake success. Returning cached or partial data with a clear status is
useful. Returning an empty list that looks like a legitimate "no results" is worse than an error, because the
caller acts on it.

Emit a metric from the fallback so a permanently open circuit is visible rather than silently absorbed. The metric
and alert wiring belong to `observability-and-logging`.
