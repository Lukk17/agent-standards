# OAuth 2.1 and JWT Validation

Flow rules, token lifetimes, and claim validation for a Spring Boot resource server or client. Open this when
wiring an authorization code flow, rotating refresh tokens, or writing the filter that turns a bearer token into an
`Authentication`.

---

### OAuth 2.1 flow requirements

- Mandate PKCE on every authorization code flow, public and confidential clients alike.
- The implicit grant is removed in OAuth 2.1. Do not offer it and do not accept it.
- Resource owner password credentials is removed too. A client that wants it wants your users' passwords.
- Rotate refresh tokens: issue a new one on every use and invalidate the old one immediately. A replayed old
  refresh token is the signal that a token was stolen, so treat reuse as a breach of that session and revoke the
  whole family.
- Access token lifetime is fifteen minutes at most. Short lifetimes are what make a revocation list tractable.

---

### Claims a resource server must check

| Claim | Rule |
| --- | --- |
| `alg` | Reject `none` explicitly. Accept only the algorithms the issuer actually signs with. |
| `exp` | Reject expired tokens with no grace beyond a small, fixed clock skew. |
| `nbf` | Reject tokens presented before they are valid. |
| `iss` | Must equal the expected issuer string, compared exactly. |
| `aud` | Must contain this API's identifier. Spring's default validator does not check this one. |

Spring's `JwtValidators.createDefaultWithIssuer` covers `exp`, `nbf`, and `iss`. Audience is yours to add.

```java
NimbusJwtDecoder decoder = NimbusJwtDecoder.withPublicKey(publicKey).build();
OAuth2TokenValidator<Jwt> audience = new JwtClaimValidator<List<String>>(
    JwtClaimNames.AUD, aud -> aud != null && aud.contains("my-api"));
decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
    JwtValidators.createDefaultWithIssuer("https://auth.example.com"),
    audience));
```

Prefer the Spring Security resource server support over a hand-written filter wherever the token is a standard JWT,
because it already handles key rotation from the JWK set, caching, and the error responses.

---

### Hand-written authentication filter

Where the token is not a standard JWT, or the service has to accept an opaque token against a revocation list, one
filter does the work for every endpoint.

```java
@Component
public class JwtAuthFilter extends OncePerRequestFilter {
  private final JwtService jwtService;

  public JwtAuthFilter(JwtService jwtService) {
    this.jwtService = jwtService;
  }

  @Override
  protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
      FilterChain chain) throws ServletException, IOException {
    String header = request.getHeader(HttpHeaders.AUTHORIZATION);
    if (header != null && header.startsWith("Bearer ")) {
      String token = header.substring(7);
      Authentication auth = jwtService.authenticate(token);
      SecurityContextHolder.getContext().setAuthentication(auth);
    }
    chain.doFilter(request, response);
  }
}
```

The filter authenticates and nothing else. It never decides whether the caller may reach the endpoint, because that
decision belongs next to the method, and a filter that also authorizes has to be kept in sync with every new route.

An invalid token leaves the context empty rather than throwing, so the entry point returns a clean 401 instead of a
500 from inside the chain.

---

### Session cookies, where sessions are unavoidable

- `httpOnly`, so script cannot read the cookie.
- `Secure`, so it never travels over plain HTTP.
- `SameSite=Strict`, or `Lax` only when a cross-site top-level navigation genuinely has to carry the session.
- Regenerate the session identifier on login, so a fixated identifier is worthless.
- Keep CSRF protection enabled, because a cookie is an ambient credential the browser attaches on its own.
