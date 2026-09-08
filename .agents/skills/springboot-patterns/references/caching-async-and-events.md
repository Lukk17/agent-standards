# Caching, Async Work, Events, and Filters

Configuration for the parts of a Spring Boot service that run beside the request. Open this when adding a cache,
moving work off the request thread, decoupling components with events, or adding a servlet filter.

---

### Redis cache manager

Caching needs `@EnableCaching` on a configuration class. Give every cache a time to live and disable null caching,
so a lookup miss does not become a poisoned entry.

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

Write the eviction alongside the cache, in the same change. A cache added today with "we will add invalidation
later" serves stale data from tomorrow.

Caching is proxy-based, so a call from inside the same bean skips the cache entirely, exactly as it skips a
transaction.

---

### Asynchronous work

`@EnableAsync` turns the annotation on. Return `CompletableFuture` rather than void where the caller needs to know
the work finished or failed, because an exception thrown from a void async method reaches nobody.

```java
@Service
public class NotificationService {
  @Async
  public CompletableFuture<Void> sendAsync(Notification notification) {
    return CompletableFuture.completedFuture(null);
  }
}
```

Define the executor rather than accepting the default. On Java 21 and later a virtual thread executor fits
I/O-bound work, and a bounded pool fits CPU-bound work. Sizing and composition rules are in the
`java-coding-standards` concurrency reference.

---

### Intra-service events

`ApplicationEventPublisher` decouples components inside one service without introducing a broker.

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final ApplicationEventPublisher events;

    @Transactional
    public Order createOrder(CreateOrderCommand cmd) {
        Order order = repository.save(Order.from(cmd));
        events.publishEvent(new OrderCreatedEvent(order.getId()));
        return order;
    }
}
```

```java
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void onOrderCreated(OrderCreatedEvent event) {
    notificationService.sendConfirmation(event.orderId());
}
```

Carry an identifier in the event rather than the entity. An entity published across a transaction boundary is
detached by the time the listener runs, and touching a lazy association on it throws.

---

### Background jobs

Use `@Scheduled` for periodic work in a single instance, and a queue such as Kafka, SQS, or RabbitMQ once the work
has to survive a restart or spread across instances. Keep every handler idempotent, because at-least-once delivery
means a handler will see the same message twice.

Guard `@Scheduled` in a multi-instance deployment with a shared lock, otherwise every instance runs the job at the
same moment.

Instrument every job with a duration metric and a last-success timestamp. A scheduled job that silently stops
running is invisible without one.

---

### Request filters

A filter is the right place for cross-cutting request concerns: correlation identifiers, request logging, and rate
limiting. Extend `OncePerRequestFilter` so the logic runs once per request rather than once per dispatch.

```java
@Component
@Slf4j
public class RequestLoggingFilter extends OncePerRequestFilter {

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

The measurement and the log line go in a `finally` block, so a failed request is still recorded. Never put business
rules in a filter, because a filter has no view of which handler will run and no way to return a typed error.
