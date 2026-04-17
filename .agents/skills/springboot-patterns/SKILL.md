---
name: springboot-patterns
description: Spring Boot architecture patterns, REST API design, layered services, data access, caching, async processing, and logging. Use for Java Spring Boot backend work.
origin: ECC
---

# Spring Boot Development Patterns

Spring Boot architecture and API patterns for scalable, production-grade services.

## When to Activate

- Building REST APIs with Spring MVC or WebFlux
- Structuring controller → service → repository layers
- Configuring Spring Data JPA, caching, or async processing
- Adding validation, exception handling, or pagination
- Setting up profiles for dev/staging/production environments
- Implementing event-driven patterns with Spring Events or Kafka

## REST API Structure

```java
@RestController
@RequestMapping("/api/markets")
@Validated
class MarketController {
  private final MarketService marketService;

  MarketController(MarketService marketService) {
    this.marketService = marketService;
  }

  @GetMapping
  ResponseEntity<Page<MarketResponse>> list(
      @RequestParam(defaultValue = "0") int page,
      @RequestParam(defaultValue = "20") int size) {
    Page<Market> markets = marketService.list(PageRequest.of(page, size));
    return ResponseEntity.ok(markets.map(MarketResponse::from));
  }

  @PostMapping
  ResponseEntity<MarketResponse> create(@Valid @RequestBody CreateMarketRequest request) {
    Market market = marketService.create(request);
    return ResponseEntity.status(HttpStatus.CREATED).body(MarketResponse.from(market));
  }
}
```

## Repository Pattern (Spring Data JPA)

```java
public interface MarketRepository extends JpaRepository<MarketEntity, Long> {
  @Query("select m from MarketEntity m where m.status = :status order by m.volume desc")
  List<MarketEntity> findActive(@Param("status") MarketStatus status, Pageable pageable);
}
```

## Service Layer with Transactions

```java
@Service
public class MarketService {
  private final MarketRepository repo;

  public MarketService(MarketRepository repo) {
    this.repo = repo;
  }

  @Transactional
  public Market create(CreateMarketRequest request) {
    MarketEntity entity = MarketEntity.from(request);
    MarketEntity saved = repo.save(entity);
    return Market.from(saved);
  }
}
```

## DTOs and Validation

```java
public record CreateMarketRequest(
    @NotBlank @Size(max = 200) String name,
    @NotBlank @Size(max = 2000) String description,
    @NotNull @FutureOrPresent Instant endDate,
    @NotEmpty List<@NotBlank String> categories) {}

public record MarketResponse(Long id, String name, MarketStatus status) {
  static MarketResponse from(Market market) {
    return new MarketResponse(market.id(), market.name(), market.status());
  }
}
```

## Exception Handling

```java
@ControllerAdvice
class GlobalExceptionHandler {
  @ExceptionHandler(MethodArgumentNotValidException.class)
  ResponseEntity<ApiError> handleValidation(MethodArgumentNotValidException ex) {
    String message = ex.getBindingResult().getFieldErrors().stream()
        .map(e -> e.getField() + ": " + e.getDefaultMessage())
        .collect(Collectors.joining(", "));
    return ResponseEntity.badRequest().body(ApiError.validation(message));
  }

  @ExceptionHandler(AccessDeniedException.class)
  ResponseEntity<ApiError> handleAccessDenied() {
    return ResponseEntity.status(HttpStatus.FORBIDDEN).body(ApiError.of("Forbidden"));
  }

  @ExceptionHandler(Exception.class)
  ResponseEntity<ApiError> handleGeneric(Exception ex) {
    // Log unexpected errors with stack traces
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
        .body(ApiError.of("Internal server error"));
  }
}
```

## HTTP Client

Use `RestClient` for all synchronous HTTP calls (Spring 6.1+):

```java
@Bean
public RestClient restClient(RestClient.Builder builder) {
    return builder
        .baseUrl("https://api.example.com")
        .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
        .build();
}

// Usage:
ResponseEntity<UserDto> response = restClient.get()
    .uri("/users/{id}", userId)
    .retrieve()
    .toEntity(UserDto.class);
```

- Do NOT use `RestTemplate` — it is deprecated
- Do NOT use `WebClient` unless the application is fully reactive (Spring WebFlux)

## Error-Resilient External Calls

Never use `Thread.sleep()` for retry logic. Use Resilience4j `@Retry` with exponential backoff + jitter. Never use fixed-interval retries.

```java
// WRONG — never do this:
// int attempts = 0;
// while (attempts < 3) { try { ... } catch ... Thread.sleep(...) }

// CORRECT — Resilience4j with exponential backoff + jitter:
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
# application.yml
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

## Hexagonal Architecture (Ports & Adapters)

Layer naming:

| Layer | Package | Annotation stereotype |
|---|---|---|
| Domain | `domain.model`, `domain.service` | none (pure Java) |
| Application Service | `application.port.in`, `application.port.out` | `@UseCase` |
| REST Adapter (in) | `adapter.in.rest` | `@WebAdapter` |
| Persistence Adapter (out) | `adapter.out.persistence` | `@PersistenceAdapter` |

Rules:
- Domain layer has ZERO dependencies on Spring or infrastructure
- Application services implement use case ports, call out-ports
- Adapters implement/use ports — never call each other directly

```java
// Application port (interface)
public interface CreateOrderUseCase {
    Order createOrder(CreateOrderCommand command);
}

// Use case implementation
@UseCase
@RequiredArgsConstructor
public class CreateOrderService implements CreateOrderUseCase {
    private final SaveOrderPort saveOrderPort;
    // ...
}

// REST adapter calls use case via port
@WebAdapter
@RestController
@RequiredArgsConstructor
public class OrderController {
    private final CreateOrderUseCase createOrderUseCase;
}
```

## API Versioning

- URI path versioning: `/api/v1/resource`
- When deprecating: add `@Deprecated` to controller, return `Deprecation` header with sunset date
- Maintain deprecated version for minimum one full release cycle before removal

```java
@GetMapping("/api/v1/users/{id}")
@Deprecated
// Response includes: Deprecation: true, Sunset: Sat, 01 Jan 2026 00:00:00 GMT
public ResponseEntity<UserDto> getUserV1(@PathVariable Long id) { ... }
```

## OpenAPI / Swagger

Add `springdoc-openapi-starter-webmvc-ui` dependency. Annotate controllers:

```java
@Tag(name = "Users", description = "User management")
@RestController
public class UserController {

    @Operation(summary = "Get user by ID")
    @ApiResponse(responseCode = "200", description = "User found")
    @ApiResponse(responseCode = "404", description = "User not found")
    @GetMapping("/api/v1/users/{id}")
    public UserDto getUser(@PathVariable Long id) { ... }
}
```

Commit `openapi.yaml` to the repository (generate with springdoc `springdoc.api-docs.path=/v3/api-docs`).

## Caching

Requires `@EnableCaching` on a configuration class.

- Always specify explicit TTL and max-size eviction policy — never use unbounded caches
- Never cache mutable shared state without an invalidation strategy

```java
@Bean
public CacheManager cacheManager(RedisConnectionFactory factory) {
    RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
        .entryTtl(Duration.ofMinutes(10))
        .disableCachingNullValues();
    return RedisCacheManager.builder(factory).cacheDefaults(config).build();
}
```

```java
@Service
public class MarketCacheService {
  private final MarketRepository repo;

  public MarketCacheService(MarketRepository repo) {
    this.repo = repo;
  }

  @Cacheable(value = "market", key = "#id")
  public Market getById(Long id) {
    return repo.findById(id)
        .map(Market::from)
        .orElseThrow(() -> new EntityNotFoundException("Market not found"));
  }

  @CacheEvict(value = "market", key = "#id")
  public void evict(Long id) {}
}
```

## Async Processing

Requires `@EnableAsync` on a configuration class.

```java
@Service
public class NotificationService {
  @Async
  public CompletableFuture<Void> sendAsync(Notification notification) {
    // send email/SMS
    return CompletableFuture.completedFuture(null);
  }
}
```

## Transaction Management

- Place `@Transactional` on **service layer methods only** — never on controllers or repository methods
- Use `readOnly = true` for query-only methods (improves performance with Hibernate)
- **Self-invocation bypass**: calling a `@Transactional` method from within the same bean bypasses the proxy — extract to a separate bean if needed

```java
@Service
public class OrderService {
    @Transactional(readOnly = true)
    public Order findById(Long id) { ... }

    @Transactional
    public Order createOrder(CreateOrderCommand cmd) { ... }
}
```

## Intra-Service Events

Use Spring's `ApplicationEventPublisher` for decoupling within a service:

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final ApplicationEventPublisher events;

    @Transactional
    public Order createOrder(CreateOrderCommand cmd) {
        Order order = // ... save
        events.publishEvent(new OrderCreatedEvent(order.getId()));
        return order;
    }
}

// Listen AFTER the transaction commits:
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void onOrderCreated(OrderCreatedEvent event) {
    notificationService.sendConfirmation(event.orderId());
}
```

## Observability

```yaml
management:
  endpoints.web.exposure.include: health,info,prometheus,metrics
  endpoint.health:
    show-details: always
    group:
      liveness.include: livenessState
      readiness.include: readinessState,db,redis
  metrics.export.otlp.endpoint: http://otel-collector:4318/v1/metrics
  tracing.sampling.probability: 1.0  # 100% in dev; reduce in prod
```

Implement custom health indicators for critical dependencies:

```java
@Component
public class ExternalApiHealthIndicator implements HealthIndicator {
    @Override
    public Health health() {
        return isReachable() ? Health.up().build() : Health.down().withDetail("reason", "timeout").build();
    }
}
```

Additional observability:
- Structured logging (JSON) via Logback encoder
- Metrics: Micrometer + Prometheus/OTel
- Tracing: Micrometer Tracing with OpenTelemetry or Brave backend

## Logging (SLF4J)

```java
@Service
public class ReportService {
  private static final Logger log = LoggerFactory.getLogger(ReportService.class);

  public Report generate(Long marketId) {
    log.info("generate_report marketId={}", marketId);
    try {
      // logic
    } catch (Exception ex) {
      log.error("generate_report_failed marketId={}", marketId, ex);
      throw ex;
    }
    return new Report();
  }
}
```

## Middleware / Filters

```java
@Component
public class RequestLoggingFilter extends OncePerRequestFilter {
  private static final Logger log = LoggerFactory.getLogger(RequestLoggingFilter.class);

  @Override
  protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
      FilterChain filterChain) throws ServletException, IOException {
    long start = System.currentTimeMillis();
    try {
      filterChain.doFilter(request, response);
    } finally {
      long duration = System.currentTimeMillis() - start;
      log.info("req method={} uri={} status={} durationMs={}",
          request.getMethod(), request.getRequestURI(), response.getStatus(), duration);
    }
  }
}
```

## Pagination and Sorting

```java
PageRequest page = PageRequest.of(pageNumber, pageSize, Sort.by("createdAt").descending());
Page<Market> results = marketService.list(page);
```

## Rate Limiting (Filter + Bucket4j)

**Security Note**: The `X-Forwarded-For` header is untrusted by default because clients can spoof it.
Only use forwarded headers when:
1. Your app is behind a trusted reverse proxy (nginx, AWS ALB, etc.)
2. You have registered `ForwardedHeaderFilter` as a bean
3. You have configured `server.forward-headers-strategy=NATIVE` or `FRAMEWORK` in application properties
4. Your proxy is configured to overwrite (not append to) the `X-Forwarded-For` header

When `ForwardedHeaderFilter` is properly configured, `request.getRemoteAddr()` will automatically
return the correct client IP from the forwarded headers. Without this configuration, use
`request.getRemoteAddr()` directly—it returns the immediate connection IP, which is the only
trustworthy value.

```java
@Component
public class RateLimitFilter extends OncePerRequestFilter {
  private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

  /*
   * SECURITY: This filter uses request.getRemoteAddr() to identify clients for rate limiting.
   *
   * If your application is behind a reverse proxy (nginx, AWS ALB, etc.), you MUST configure
   * Spring to handle forwarded headers properly for accurate client IP detection:
   *
   * 1. Set server.forward-headers-strategy=NATIVE (for cloud platforms) or FRAMEWORK in
   *    application.properties/yaml
   * 2. If using FRAMEWORK strategy, register ForwardedHeaderFilter:
   *
   *    @Bean
   *    ForwardedHeaderFilter forwardedHeaderFilter() {
   *        return new ForwardedHeaderFilter();
   *    }
   *
   * 3. Ensure your proxy overwrites (not appends) the X-Forwarded-For header to prevent spoofing
   * 4. Configure server.tomcat.remoteip.trusted-proxies or equivalent for your container
   *
   * Without this configuration, request.getRemoteAddr() returns the proxy IP, not the client IP.
   * Do NOT read X-Forwarded-For directly—it is trivially spoofable without trusted proxy handling.
   */
  @Override
  protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
      FilterChain filterChain) throws ServletException, IOException {
    // Use getRemoteAddr() which returns the correct client IP when ForwardedHeaderFilter
    // is configured, or the direct connection IP otherwise. Never trust X-Forwarded-For
    // headers directly without proper proxy configuration.
    String clientIp = request.getRemoteAddr();

    Bucket bucket = buckets.computeIfAbsent(clientIp,
        k -> Bucket.builder()
            .addLimit(Bandwidth.classic(100, Refill.greedy(100, Duration.ofMinutes(1))))
            .build());

    if (bucket.tryConsume(1)) {
      filterChain.doFilter(request, response);
    } else {
      response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
    }
  }
}
```

## Background Jobs

Use Spring's `@Scheduled` or integrate with queues (e.g., Kafka, SQS, RabbitMQ). Keep handlers idempotent and observable.

## Production Defaults

- Prefer constructor injection, avoid field injection
- Enable `spring.mvc.problemdetails.enabled=true` for RFC 7807 errors (Spring Boot 3+)
- Configure HikariCP pool sizes for workload, set timeouts
- Use `@Transactional(readOnly = true)` for queries
- Enforce null-safety via `@NonNull` and `Optional` where appropriate

**Remember**: Keep controllers thin, services focused, repositories simple, and errors handled centrally. Optimize for maintainability and testability.
