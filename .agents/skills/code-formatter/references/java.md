# Java Formatting Examples

Contents:

- [Brace every inline exit](#brace-every-inline-exit)
- [Blank line after a wrapped signature](#blank-line-after-a-wrapped-signature)
- [Empty lines around try, catch and finally](#empty-lines-around-try-catch-and-finally)
- [Empty line above a standalone async call](#empty-line-above-a-standalone-async-call)
- [Empty line above a closing return](#empty-line-above-a-closing-return)
- [Blank line below a return inside a try with clauses](#blank-line-below-a-return-inside-a-try-with-clauses)
- [Empty line above an operation-terminating call](#empty-line-above-an-operation-terminating-call)
- [Comments above the line, never trailing](#comments-above-the-line-never-trailing)
- [Doc comments sit on their declaration](#doc-comments-sit-on-their-declaration)
- [One concept per blank-separated paragraph](#one-concept-per-blank-separated-paragraph)
- [One chain step per line](#one-chain-step-per-line)
- [Single-expression bodies stay on one line](#single-expression-bodies-stay-on-one-line)
- [What the rules look like together](#what-the-rules-look-like-together)

The wrong and right form of each formatting rule in Java. Each section carries the name of its rule in SKILL.md, and the full body and reasoning of every rule is in [rules-in-depth.md](rules-in-depth.md). Where the project runs google-java-format and it rewrites a construct, its output wins and the rule yields.

---

### Brace every inline exit

Wrong:

```java
if (rows.isEmpty()) return null;
```

Right:

```java
if (rows.isEmpty()) {
    return null;
}
```

### Blank line after a wrapped signature

Wrong:

```java
public Page<ForumThreadResponse> listThreads(
        @PathVariable UUID categoryId,
        @ParameterObject @Valid PageRequestDto pageRequest,
        @AuthenticationPrincipal OwnerPrincipal owner) {
    var visibleCategory = forumAccess.requireVisible(categoryId, owner);
    return forumThreads.list(visibleCategory, pageRequest.toPageable());
}
```

Right:

```java
public Page<ForumThreadResponse> listThreads(
        @PathVariable UUID categoryId,
        @ParameterObject @Valid PageRequestDto pageRequest,
        @AuthenticationPrincipal OwnerPrincipal owner) {

    var visibleCategory = forumAccess.requireVisible(categoryId, owner);

    return forumThreads.list(visibleCategory, pageRequest.toPageable());
}
```

### Empty lines around try, catch and finally

```java
var logger = LoggerFactory.getLogger(getClass());

try {
    service.backup();

    logger.info("backup complete");
} catch (BackupException e) {
    logger.error("backup failed", e);
}
```

### Empty line above a standalone async call

```java
state = state.toBuilder().running(true).build();

gateway.show(1001, "Rest over", "Time to lift").join();

logger.info("alarm fired");
```

### Empty line above a closing return

```java
public Optional<WorkLog> findFor(Exercise e, LocalDate date) {
    var list = dao.getForDate(date);

    for (var w : list) {
        if (w.exercise().name().equals(e.name())) {
            dao.merge(w);

            return Optional.of(w);
        }
    }

    return Optional.empty();
}
```

### Blank line below a return inside a try with clauses

Wrong:

```java
try {
    String xml = xmlGenerationService.generateXml(documents);

    log.info("audit xml.generation success documentType={} subject={} bytes={}", documentType, subject, xml.length());

    return xml;
} catch (XmlMappingException ex) {
    ...
} finally {
    ...
}
```

Right:

```java
try {
    String xml = xmlGenerationService.generateXml(documents);

    log.info("audit xml.generation success documentType={} subject={} bytes={}", documentType, subject, xml.length());

    return xml;

} catch (XmlMappingException ex) {
    ...
} finally {
    ...
}
```

### Empty line above an operation-terminating call

Operation-terminators in Java: `dialog.dismiss()`, `httpClient.send(...)`, `logger.info("phase done", ...)`, `eventBus.publish(...)`.

```java
var normalized = startOfDay(day);
state.setSelectedDate(normalized);
logger.info("Chosen date: {}", normalized);

dialog.dismiss();
```

### Comments above the line, never trailing

Wrong:

```java
var delay = computeBackoff(retryCount); // exponential, max 30s
```

Right:

```java
// Exponential backoff, capped at 30s to avoid hammering the server.
var delay = computeBackoff(retryCount);
```

### Doc comments sit on their declaration

A tag line is `@param`, `@return` or `@throws` in Javadoc, each on one physical line.

```java
// GOOD: sits on the declaration, one line per tag
/**
 * Reserves stock and holds it until the payment window closes.
 *
 * @param holdFor how long the reservation survives, at most 15 minutes
 * @throws InsufficientStockException when the warehouse cannot cover the order
 */
public Reservation reserve(OrderId orderId, Duration holdFor) { ... }

// BAD: blank line under the block, and a tag hard-wrapped to fit a width
/**
 * Reserves stock.
 *
 * @param holdFor how long the reservation survives, at most 15 minutes, after
 *                which the hold is released by the sweeper
 */

public Reservation reserve(OrderId orderId, Duration holdFor) { ... }
```

### One concept per blank-separated paragraph

```java
public void save() {
    var navigator = activity.getNavigator();
    var selectedDate = repository.getSelectedDate();

    var updated = original.toBuilder()
        .name(nameField.getText())
        .bodyParts(form.getPrimary())
        .build();
    dao.replace(updated);

    if (isDestroyed()) {
        return;
    }

    eventBus.publish(new ExercisesInvalidated());

    navigator.pop();
}
```

### One chain step per line

google-java-format reflows a chain to fit the line, joining a short one back onto a single line, so where it runs, its output wins and this rule does not apply.

```java
var activeNames = exercises.stream()
    .filter(Exercise::isActive)
    .map(Exercise::name)
    .toList();
```

### Single-expression bodies stay on one line

```java
Function<Integer, Integer> doubled = x -> x * 2;
Comparator<Exercise> byName = Comparator.comparing(Exercise::name);
```

A Java method body keeps its braces on their own lines, as Google Java Style requires, so only a lambda stays on one
line.

---

### What the rules look like together

Pass:

```java
public Optional<Receipt> settle(Order order) {
    if (order.isEmpty()) {
        return Optional.empty();
    }

    var total = pricing.total(order);
    var payload = mapper.toPayload(order, total);

    var response = paymentClient.send(payload);

    logger.info("settled order {}", order.id());

    return Optional.of(Receipt.from(response));
}
```

Fail:

```java
public Optional<Receipt> settle(Order order) {
    if (order.isEmpty()) return Optional.empty();
    var total = pricing.total(order); // price it
    var payload = mapper.toPayload(order, total);
    var response = paymentClient.send(payload);
    logger.info("settled order {}", order.id());
    return Optional.of(Receipt.from(response));
}
```

The failing version is what most default formatters produce and leave alone. Nothing in it is wrong to a compiler.
It is harder to read because the exit, the network call and the return all sit at the same visual weight as the
local arithmetic around them.
