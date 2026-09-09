# Spring Boot Security

Authentication, authorization, and the hardening around them for a Spring Boot service. Open this when adding
authentication, locking an endpoint down, validating input at the edge, setting response headers or CORS, handling
secrets, or rate limiting. Every rule assumes Spring Security 6.x on the baseline in the hub.

---

### Authenticate statelessly, validate every claim

Prefer a stateless bearer token, or an opaque token with a revocation list. Where sessions are unavoidable, mark the
cookie `httpOnly`, `Secure`, and `SameSite=Strict`. Validate the token in a resource server or a single
`OncePerRequestFilter`, never per controller.

Pass: the decoder rejects `none` as an algorithm and checks `exp`, `iss`, and `aud`, with the audience validator
configured explicitly because the default validator does not check it.

```java
NimbusJwtDecoder decoder = NimbusJwtDecoder.withPublicKey(publicKey).build();
decoder.setJwtValidator(JwtValidators.createDefaultWithIssuer("https://auth.example.com"));
```

Fail: a filter that reads the subject out of an unverified token, or a decoder left on defaults so any issuer with
a valid signature is accepted.

Access tokens live fifteen minutes at most. Full flow requirements, refresh token rotation, and the filter skeleton
are in [oauth2-and-jwt.md](oauth2-and-jwt.md).

---

### Deny by default, then authorize per method

Turn on method security and put the rule next to the method it guards, so a new endpoint is closed until somebody
opens it.

Pass: `@EnableMethodSecurity`, role checks for coarse access, and a named authorization bean for ownership.

```java
@PreAuthorize("hasRole('ADMIN')")
@GetMapping("/users")
public List<UserDto> listUsers() {
  return userService.findAll();
}

@PreAuthorize("@authz.isOwner(#id, authentication)")
@DeleteMapping("/users/{id}")
public ResponseEntity<Void> deleteUser(@PathVariable Long id) {
  userService.delete(id);
  return ResponseEntity.noContent().build();
}
```

Fail: an ownership check written inside the method body, which every later caller of that service method skips.

---

### Validate input at the edge

Constrain the DTO and let Bean Validation reject the request before any business code runs. Sanitise HTML against
an allow list before it is ever rendered.

Pass: a constrained record plus `@Valid` on the parameter.

```java
public record CreateUserDto(
    @NotBlank @Size(max = 100) String name,
    @NotBlank @Email String email,
    @NotNull @Min(0) @Max(150) Integer age
) {}
```

```java
@PostMapping("/users")
public ResponseEntity<UserDto> createUser(@Valid @RequestBody CreateUserDto dto) {
  return ResponseEntity.status(HttpStatus.CREATED).body(userService.create(dto));
}
```

Fail: `createUser(@RequestBody UserDto dto)` with no constraints, where the first thing to notice a bad value is a
constraint violation from the database.

---

### Parameterise every query

Spring Data derived queries and named bindings are parameterised for you. String concatenation into a query is a
SQL injection, whatever the surrounding validation claims.

Pass: `@Query(value = "SELECT * FROM users WHERE name = :name", nativeQuery = true)` with a `@Param` binding, or a
Spring Data derived query such as `findByEmailAndActiveTrue`.

Fail: `@Query(value = "SELECT * FROM users WHERE name = '" + name + "'", nativeQuery = true)`.

---

### Hash passwords with a memory-hard function

Argon2id is the primary choice, and BCrypt at work factor 12 or higher is the acceptable fallback. MD5, the SHA
family, unsalted hashes, and PBKDF2 under 100,000 iterations are prohibited.

Pass: `new Argon2PasswordEncoder(16, 32, 1, 65536, 3)` as the `PasswordEncoder` bean, meaning salt length 16, hash
length 32, parallelism 1, memory 65536, and 3 iterations.

Fail: any digest function used directly, or a BCrypt encoder left on the default work factor.

---

### Pick a CSRF posture and write down why

A browser app with session cookies keeps CSRF protection on and carries the token in forms and headers. A pure API
authenticated with bearer tokens has no ambient credential to abuse, so CSRF can be disabled, and the reason
belongs in the code.

Pass: `http.csrf(csrf -> csrf.disable())` alongside
`http.sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))`, on an API that only
accepts bearer tokens.

Fail: CSRF disabled on an app that still authenticates browsers with a session cookie.

---

### Set response headers, and leave the ones Spring already decides

Configure the headers that carry a policy decision: CSP with no `unsafe-inline` and no `unsafe-eval`, HSTS,
frame-ancestors, referrer policy, and permissions policy.

Pass: the policy headers set explicitly, with nonces where an inline script is genuinely unavoidable.

```java
http.headers(headers -> headers
    .contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'self'; frame-ancestors 'none'"))
    .frameOptions(HeadersConfigurer.FrameOptionsConfig::deny)
    .httpStrictTransportSecurity(hsts -> hsts.maxAgeInSeconds(63072000).includeSubDomains(true).preload(true)));
```

Fail: re-enabling the legacy XSS auditor with `.xssProtection(Customizer.withDefaults())`. Spring Security 6 sends
`X-XSS-Protection: 0` on purpose, because the browser auditors that header controlled were themselves exploitable
and every current browser has removed them. Turning it back on asks for a filter that no longer exists and signals
the wrong thing to a reviewer. CSP is the control that replaced it.

The full header block, the CORS source bean, and mutual TLS for service-to-service calls are in
[headers-cors-mtls.md](headers-cors-mtls.md).

---

### Rate limit with Bucket4j, refilling greedily

This is the one rate limiting implementation in the standards. It lives here, and no other file carries a second
copy of it.

Refill greedily rather than at interval boundaries. A greedy bandwidth returns tokens continuously across the
window, so a client that exhausts its quota recovers a little at a time. Interval refill returns the whole bucket
at each boundary, which synchronises every throttled client on the node into one burst the instant the window
turns over, and that burst lands on the upstream the limiter exists to protect. Greedy refill keeps the same
average rate with none of that clustering.

Pass: one bucket per client key, greedy refill, 429 with a `Retry-After` the client can act on.

```java
@Component
public class RateLimitFilter extends OncePerRequestFilter {
  private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

  private Bucket createBucket() {
    return Bucket.builder()
        .addLimit(limit -> limit.capacity(100).refillGreedy(100, Duration.ofMinutes(1)))
        .build();
  }

  @Override
  protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
      FilterChain chain) throws ServletException, IOException {
    Bucket bucket = buckets.computeIfAbsent(request.getRemoteAddr(), key -> createBucket());
    ConsumptionProbe probe = bucket.tryConsumeAndReturnRemaining(1);

    if (probe.isConsumed()) {
      chain.doFilter(request, response);
      return;
    }
    long retryAfterSeconds = Duration.ofNanos(probe.getNanosToWaitForRefill()).toSeconds() + 1;
    response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
    response.setHeader(HttpHeaders.RETRY_AFTER, String.valueOf(retryAfterSeconds));
  }
}
```

Fail: `Refill.intervally(...)`, an unbounded map that grows one entry per client address forever, or a 429 with no
`Retry-After`, which leaves a well-behaved client guessing.

Take the client key from `request.getRemoteAddr()`. It is the immediate connection address, which is the only value
a client cannot forge. Behind a reverse proxy, make that address correct by configuring
`server.forward-headers-strategy` and registering `ForwardedHeaderFilter`, and make sure the proxy overwrites
rather than appends `X-Forwarded-For`. Never read that header directly in application code.

Bound the map with an eviction policy, or move the buckets into a distributed store, before this filter meets real
traffic. Alert on sustained 429 rates, because a limiter firing constantly is either under attack or misconfigured.

---

### Keep secrets out of the source tree

Configuration files carry placeholders, and the value arrives from the environment or a vault at runtime. Rotate
tokens and database credentials on a schedule.

Pass: `password: ${DB_PASSWORD}` in `application.yml`, or a Spring Cloud Vault backend supplying the value.

Fail: `password: mySecretPassword123` written into the file that gets committed.

Never log a secret, a token, a password, or full card data, and redact sensitive fields before they reach a
structured log line.

---

### Validate uploads before you store them

Check size, declared content type, and extension, and store the file outside the web root. Scan it where the
threat model calls for it.

Pass: a size cap, an allow list of types, and a generated storage name.

Fail: writing the client-supplied filename straight into a served directory.

---

### Keep dependencies patched

Run a dependency vulnerability scan in CI and fail the build on a known CVE at or above the project threshold. Stay
on supported Spring Boot and Spring Security lines, because an unsupported line stops receiving the fixes entirely.
The pipeline that runs the scan is in [verification-pipeline.md](verification-pipeline.md).

Pass: a scheduled, reviewed upgrade with the scan as a gate.

Fail: a suppression file with no expiry dates.

---

### Checklist

- [ ] Tokens are validated for algorithm, expiry, issuer, and audience, and `none` is rejected.
- [ ] Every sensitive path carries an authorization rule, and the default is deny.
- [ ] Every request body is a constrained DTO validated with `@Valid`.
- [ ] No query is built by string concatenation.
- [ ] Passwords are hashed with Argon2id, or BCrypt at work factor 12 or higher.
- [ ] The CSRF posture matches the app type, and a disabled CSRF says why in the code.
- [ ] CSP has no `unsafe-inline` and no `unsafe-eval`, HSTS is set, and nothing re-enables `X-XSS-Protection`.
- [ ] Rate limiting is in place, refills greedily, returns `Retry-After`, and its bucket map is bounded.
- [ ] No secret is committed, and no secret reaches a log line.
- [ ] Uploads are size, type, and extension checked, and stored outside the web root.
- [ ] The dependency scan is green, and every suppression has an expiry.
