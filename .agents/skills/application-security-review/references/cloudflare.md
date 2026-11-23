# CDN Security on Cloudflare

The Cloudflare form of the CDN and edge checks: security headers set in a Worker, and the WAF managed rules. Open this when the application sits behind Cloudflare. The checks themselves are in [cloud-infrastructure-security.md](cloud-infrastructure-security.md).

---

### Security headers in a Worker

```typescript
// PASS: CORRECT: Cloudflare Workers with security headers
export default {
  async fetch(request: Request): Promise<Response> {
    const response = await fetch(request);

    // Add security headers
    const headers = new Headers(response.headers);
    headers.set('X-Frame-Options', 'DENY');
    headers.set('X-Content-Type-Options', 'nosniff');
    headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    headers.set('Permissions-Policy', 'geolocation=(), microphone=()');

    return new Response(response.body, {
      status: response.status,
      headers
    });
  }
};
```

---

### WAF rules

```bash
# Enable Cloudflare WAF managed rules
# - OWASP Core Ruleset
# - Cloudflare Managed Ruleset
# - Rate limiting rules
# - Bot protection
```

---

### Resources

- [Cloudflare Security Documentation](https://developers.cloudflare.com/security/)
