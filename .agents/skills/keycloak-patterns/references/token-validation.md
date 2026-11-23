# Token Validation on Any Platform

How a platform with no Keycloak client library validates a Keycloak token: the JWKS and discovery endpoints and the manual steps, plus which skill owns Spring Boot and Node.js. Open it when the consumer is not .NET. The .NET snippets are in [dotnet-integration-examples.md](dotnet-integration-examples.md).

---

### Token Validation (Any Platform)

#### JWKS Endpoint

All platforms can validate tokens using the JWKS endpoint:

```
GET {AuthServerUrl}/realms/{realm}/protocol/openid-connect/certs
```

#### Discovery Endpoint

Get all endpoints and configuration:

```
GET {AuthServerUrl}/realms/{realm}/.well-known/openid-configuration
```

#### Manual Token Validation Steps

1. Fetch JWKS from realm
2. Decode JWT header to get `kid` (key ID)
3. Find matching public key in JWKS
4. Verify signature
5. Validate claims: `iss`, `aud`, `exp`, `nbf`

---

### Spring Boot and Node.js

Spring Security resource-server configuration against a Keycloak realm belongs to `springboot-patterns`, and
verifying a Keycloak JWT inside a Node service belongs to `node-backend-patterns`. Point either one at the realm
issuer, `{AuthServerUrl}/realms/{realm}`, and read the client secret from the environment, never from source.
