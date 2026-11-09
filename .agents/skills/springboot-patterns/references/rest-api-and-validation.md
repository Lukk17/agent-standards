# REST API, Validation, and Documentation

Full examples for the controller layer: request and response types, validation, the pagination envelope, the
global exception handler, and the OpenAPI setup. Open this when building an endpoint from scratch or when a
response shape needs to be settled.

---

### Contents

- Controller
- Request and response types
- Pagination envelope
- Global exception handler
- Version in the path, and deprecate with a real date
- OpenAPI

---

### Controller

```java
@RestController
@RequestMapping("/api/v1/markets")
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
exception message reaching a client is an information leak, and the scan phase in
[verification-pipeline.md](verification-pipeline.md) greps for exactly that.

---

### Version in the path, and deprecate with a real date

Put the version in the URI as `/api/v1/resource`. When a version is going away, mark the controller `@Deprecated`,
send a `Deprecation` header, and send a `Sunset` header holding a date at least one full release cycle ahead of the
announcement. Compute that date when you write the deprecation rather than copying one from an example, because a
sunset date already in the past tells a client the endpoint is gone while it is still serving traffic.

Pass: `.header("Sunset", sunsetDate.format(DateTimeFormatter.RFC_1123_DATE_TIME))` on a `@Deprecated` controller,
where `sunsetDate` is computed from the release calendar rather than typed in.

Fail: a hardcoded sunset date nobody revisits, or a version removed in the release that announced its deprecation.

---

### OpenAPI

Add `springdoc-openapi-starter-webmvc-ui`, taking the version from the project version catalog, and annotate the controllers. The response annotations are not repeated on every method. Declare them once as composable meta-annotations in a shared `openapi` package, and put the matching ones on every endpoint, so the spec is complete and a change to an error description is one edit.

```java
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@ApiResponse(responseCode = "400", description = "Invalid request",
        content = @Content(mediaType = "application/problem+json", schema = @Schema(implementation = ApiProblem.class)))
@ApiResponse(responseCode = "500", description = "Unexpected server error",
        content = @Content(mediaType = "application/problem+json", schema = @Schema(implementation = ApiProblem.class)))
public @interface ApiCommonErrorResponses {}
```

A useful set, each its own file: `ApiCommonSuccessResponses` (200), `ApiCreatedResponses` (201), `ApiAcceptedResponses` (202), `ApiNoContentResponses` (204), `ApiRedirectResponses` (302), `ApiCommonErrorResponses` (400, 500), `ApiSecuredResponses` (401, 403), `ApiNotFoundResponses` (404), `ApiConflictResponses` (409), and `ApiTooManyRequestsResponses` (429). Compose them per endpoint:

```java
@Tag(name = "Users", description = "User management")
@RestController
class UserController {

    @Operation(summary = "Create a user")
    @ApiCreatedResponses
    @ApiCommonErrorResponses
    @ApiSecuredResponses
    @ApiConflictResponses
    @PostMapping("/api/v1/users")
    @ResponseStatus(HttpStatus.CREATED)
    UserDto create(@Valid @RequestBody CreateUserRequest request) { ... }
}
```

Two rules keep the spec honest. The success annotation matches what the endpoint really returns: a `@ResponseStatus(CREATED)` method declares 201, a method returning nothing declares 204, an accepted asynchronous job 202, a redirect 302, never a blanket 200. And every error response references the schema of what the project actually sends: the project's own problem record (`ApiProblem` above, carrying `type`, `title`, `status`, `detail`, `instance` and whatever extra members such as `traceId` or field errors the handler adds) with media type `application/problem+json`. Point at Spring's `ProblemDetail` only when the wire shape is exactly that class, because a generated client deserialises what the spec says, not what the server sends.

Pass: `@ApiNoContentResponses` on a `DELETE` that returns `204`, and errors described as `application/problem+json` with the project's problem schema.

Fail: one `@ApiResponse(responseCode = "200")` copied onto a `201` endpoint, and error responses declared as `application/json` with no schema.

Commit the generated `openapi.yaml` so a contract change shows up as a reviewable diff rather than as a surprise in
a consumer. Generate it from the running application at the path `springdoc.api-docs.path` exposes.
