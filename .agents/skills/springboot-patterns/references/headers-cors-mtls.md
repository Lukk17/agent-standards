# Response Headers, CORS, and Mutual TLS

The full configuration blocks behind the header, CORS, and service-to-service rules in the skill. Open this when
setting the headers up for the first time, when a CSP is blocking something, or when internal services need to
authenticate each other.

---

### The full header block

```java
http.headers(headers -> headers
    .contentSecurityPolicy(csp ->
        csp.policyDirectives("default-src 'self'; script-src 'self' 'nonce-{random}'; style-src 'self' 'nonce-{random}'; img-src 'self' data:; frame-ancestors 'none'"))
    .frameOptions(HeadersConfigurer.FrameOptionsConfig::deny)
    .httpStrictTransportSecurity(hsts -> hsts
        .maxAgeInSeconds(63072000)
        .includeSubDomains(true)
        .preload(true))
    .referrerPolicy(referrer -> referrer
        .policy(ReferrerPolicyHeaderWriter.ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN))
    .permissionsPolicy(permissions -> permissions
        .policy("camera=(), microphone=(), geolocation=()")));
```

Notes that decide whether this block actually protects anything:

- No `unsafe-inline` and no `unsafe-eval`. A CSP containing either one permits the injection class it exists to
  stop. Where an inline script or style genuinely cannot be removed, generate a per-response nonce and put that
  nonce in the directive and on the tag.
- `frame-ancestors 'none'` is the modern control. `X-Frame-Options: DENY` stays as the fallback for old agents,
  which is what the `frameOptions` line above emits.
- HSTS with `preload` is a commitment. Once the domain is on a preload list, every subdomain must serve HTTPS, and
  removal takes months. Set `includeSubDomains` only when every subdomain is ready.
- Do not add `.xssProtection(Customizer.withDefaults())`. Spring Security 6 sends `X-XSS-Protection: 0`
  deliberately, because the browser auditors that header enabled were themselves exploitable and current browsers
  removed them. CSP replaced it.

---

### CORS

Configure CORS once at the security filter level. A per-controller `@CrossOrigin` scatters the policy across the
codebase and the loosest annotation becomes the real policy.

```java
@Bean
public CorsConfigurationSource corsConfigurationSource() {
  CorsConfiguration config = new CorsConfiguration();
  config.setAllowedOrigins(List.of("https://app.example.com"));
  config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
  config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
  config.setAllowCredentials(true);
  config.setMaxAge(3600L);

  UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
  source.registerCorsConfiguration("/api/**", config);
  return source;
}
```

```java
http.cors(cors -> cors.configurationSource(corsConfigurationSource()));
```

List origins explicitly. A wildcard origin is invalid alongside `allowCredentials(true)` and the specification
makes Spring reject the combination, so a wildcard here is a sign that credentials are about to be turned off to
make the error go away, which is the wrong fix.

---

### Mutual TLS between internal services

Where services talk to each other on a private network, mutual TLS gives each side a verified identity without a
shared secret in configuration.

```yaml
server:
  ssl:
    client-auth: need
    key-store: classpath:service.p12
    trust-store: classpath:trusted-cas.p12
```

`client-auth: need` rejects any connection without a client certificate. `want` accepts one and continues without,
which means the check is advisory, so use it only during a migration and put a date on it.

Keep the trust store limited to the internal certificate authority that issues service certificates. Trusting the
public CA bundle here means any certificate on the internet satisfies the check.

Rotate service certificates on a schedule, and make sure the rotation is tested. An expired internal certificate
takes down every caller at once and looks exactly like a network outage.
