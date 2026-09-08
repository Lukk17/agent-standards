# REST API, Validation, and Documentation

Full examples for the controller layer: request and response types, validation, the pagination envelope, the
global exception handler, and the OpenAPI setup. Open this when building an endpoint from scratch or when a
response shape needs to be settled.

---

### Controller

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
  ResponseEntity<PageResponse<MarketResponse>> list(
      @RequestParam(defaultValue = "0") int page,
      @RequestParam(defaultValue = "20") int size) {
    PageResponse<MarketResponse> markets = marketService.list(PageRequest.of(page, size));
    return ResponseEntity.ok(markets);
  }

  @PostMapping
  ResponseEntity<MarketResponse> create(@Valid @RequestBody CreateMarketRequest request) {
    Market market = marketService.create(request);
    return ResponseEntity.status(HttpStatus.CREATED).body(MarketResponse.from(market));
  }
}
```

The class and its methods are package-private. Spring does not need them public, and keeping them package-private
stops anything outside the web package from calling a controller directly.

---

### Request and response types

Constraints live on the request record, so an invalid payload never reaches the service.

```java
public record CreateMarketRequest(
    @NotBlank @Size(max = 200) String name,
    @NotBlank @Size(max = 2000) String description,
    @NotNull @FutureOrPresent Instant endDate,
    @NotEmpty List<@NotBlank String> categories) {}
```

```java
public record MarketResponse(Long id, String name, MarketStatus status) {
  static MarketResponse from(Market market) {
    return new MarketResponse(market.id(), market.name(), market.status());
  }
}
```

---

### Pagination envelope

The project owns the paged response shape, so Spring Data's `Page` stays inside the service layer.

```java
public record PageResponse<T>(
    List<T> content,
    int page,
    int size,
    long totalElements,
    int totalPages) {

  static <S, T> PageResponse<T> from(Page<S> source, Function<S, T> mapper) {
    return new PageResponse<>(
        source.getContent().stream().map(mapper).toList(),
        source.getNumber(),
        source.getSize(),
        source.getTotalElements(),
        source.getTotalPages());
  }
}
```

Build the page request with an explicit sort, otherwise page two can repeat a row from page one.

```java
PageRequest page = PageRequest.of(pageNumber, pageSize, Sort.by("createdAt").descending());
```

---

### Global exception handler

```java
@ControllerAdvice
class GlobalExceptionHandler {
  @ExceptionHandler(MethodArgumentNotValidException.class)
  ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
    ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
    problem.setType(URI.create("https://example.com/problems/validation"));
    problem.setTitle("Validation failed");
    problem.setDetail("One or more fields are invalid");
    Map<String, String> fieldErrors = ex.getBindingResult().getFieldErrors().stream()
        .collect(Collectors.toMap(FieldError::getField, FieldError::getDefaultMessage, (a, b) -> a));
    problem.setProperty("errors", fieldErrors);
    return problem;
  }

  @ExceptionHandler(AccessDeniedException.class)
  ProblemDetail handleAccessDenied() {
    ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.FORBIDDEN);
    problem.setTitle("Forbidden");
    return problem;
  }

  @ExceptionHandler(Exception.class)
  ProblemDetail handleGeneric(Exception ex) {
    ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.INTERNAL_SERVER_ERROR);
    problem.setTitle("Internal server error");
    return problem;
  }
}
```

The catch-all handler logs the exception with its stack trace and returns a body with no detail from it. An
exception message reaching a client is an information leak, and `springboot-verification` greps for exactly that.

---

### OpenAPI

Add `springdoc-openapi-starter-webmvc-ui`, taking the version from the project version catalog, and annotate the
controllers.

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

Commit the generated `openapi.yaml` so a contract change shows up as a reviewable diff rather than as a surprise in
a consumer. Generate it from the running application at the path `springdoc.api-docs.path` exposes.
