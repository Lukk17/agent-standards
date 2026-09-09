# Keycloak.AuthServices Implementation Guide

Wiring the Keycloak.AuthServices packages into an ASP.NET Core application: authentication, authorization, resource
protection, and the SDKs that talk back to Keycloak. This is the client side of the identity boundary, and it assumes
the realm and clients already exist.

Baseline versions, current as of September 2026: Keycloak.AuthServices 2.x against Keycloak 26, on .NET 8 or newer.

---

### When to activate

- Adding JWT Bearer or OIDC authentication to an ASP.NET Core API or web application.
- Enforcing realm or client roles through an authorization policy.
- Protecting an endpoint with the Keycloak Authorization Server and UMA permissions.
- Calling the Keycloak Admin REST API or Protection API from C#.
- Wiring Keycloak into .NET Aspire, or instrumenting it with OpenTelemetry.

---

### When not to activate

- Creating realms, clients, flows, or federation on the server: see [administration.md](administration.md).
- Token verification in a Node service: use `node-backend-patterns`.
- Spring Security resource-server configuration: use `springboot-patterns`.
- The HTTP contract the protected endpoints expose: use `api-design`.
- Threat modelling around authentication: use `security-review`.

---

### Reference map

| Task | Open |
| --- | --- |
| OIDC web app authentication, RFC 8414 metadata discovery | [authentication.md](authentication.md) |
| RBAC, role claims transformation, token introspection | [authorization.md](authorization.md) |
| Authorization Server, protected resources, policy builder, parameter resolvers | [resource-protection.md](resource-protection.md) |
| Admin REST API, hand-written and Kiota clients, token management | [admin-sdk.md](admin-sdk.md) |
| UMA Protection API, resource and permission management | [protection-api.md](protection-api.md) |
| Organization-based multi-tenancy and membership requirements | [organization-authorization.md](organization-authorization.md) |
| .NET Aspire, project templates, OpenTelemetry | [devex.md](devex.md) |
| Every configuration option, naming conventions, adapter file | [configuration.md](configuration.md) |
| Recipes, common failures, debugging | [dotnet-troubleshooting.md](dotnet-troubleshooting.md) |

JWT Bearer authentication for a Web API is covered below and needs no reference file.

---

### Packages Overview

| Package | Purpose |
|---------|---------|
| `Keycloak.AuthServices.Authentication` | JWT Bearer (Web API) and OpenID Connect (Web App) authentication |
| `Keycloak.AuthServices.Authorization` | RBAC (realm/client roles), Authorization Server client, `[ProtectedResource]` attribute, organization authorization |
| `Keycloak.AuthServices.Sdk` | Hand-written Admin REST API + Protection API HTTP clients |
| `Keycloak.AuthServices.Sdk.Kiota` | Auto-generated (Kiota) Admin REST API client, full API coverage |
| `Keycloak.AuthServices.Common` | Shared configuration (`KeycloakInstallationOptions`), claims utilities |
| `Keycloak.AuthServices.OpenTelemetry` | Metrics and tracing instrumentation |
| `Keycloak.AuthServices.Aspire.Hosting` | .NET Aspire `KeycloakResource` integration |
| `Keycloak.AuthServices.Templates` | `dotnet new` project templates |

---

### Minimal Web API Setup

Install the authentication package:

```bash
dotnet add package Keycloak.AuthServices.Authentication
```

Install the shared configuration package:

```bash
dotnet add package Keycloak.AuthServices.Common
```

```csharp
using Keycloak.AuthServices.Authentication;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddKeycloakWebApiAuthentication(builder.Configuration);
builder.Services.AddAuthorization();

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/", () => "Hello World!").RequireAuthorization();
app.Run();
```

Bind it from the `Keycloak` section of `appsettings.json`. The kebab-case keys come from the Keycloak adapter format:

```json
{
  "Keycloak": {
    "realm": "Test",
    "auth-server-url": "http://localhost:8080/",
    "ssl-required": "none",
    "resource": "test-client",
    "verify-token-audience": true,
    "credentials": {
      "secret": "your-client-secret"
    }
  }
}
```

---

### Configuration Section

All packages bind to `"Keycloak"` config section by default. Key properties:

| Property | Description |
|----------|-------------|
| `realm` | Keycloak realm name |
| `auth-server-url` | Keycloak server URL (e.g., `http://localhost:8080/`) |
| `resource` | Client ID |
| `ssl-required` | `none`, `external`, or `all` |
| `verify-token-audience` | Validate audience claim against `resource` |
| `credentials.secret` | Client secret (confidential clients) |

Both kebab-case (Keycloak adapter format) and PascalCase are supported.

---

### Adding Authorization (RBAC)

```bash
dotnet add package Keycloak.AuthServices.Authorization
```

```csharp
builder.Services.AddKeycloakAuthorization(builder.Configuration)
    .AddAuthorizationBuilder()
    .AddPolicy("AdminOnly", policy => policy.RequireRealmRoles("admin"))
    .AddPolicy("EditorOnly", policy => policy.RequireResourceRoles("editor"));
```

---

### Adding Authorization Server (Resource Protection)

```csharp
builder.Services
    .AddKeycloakAuthorization()
    .AddAuthorizationServer(builder.Configuration);

app.MapGet("/workspaces", () => "Hello World!")
    .RequireProtectedResource("workspaces", "workspace:read");
```

---

### Adding Admin SDK

```bash
dotnet add package Keycloak.AuthServices.Sdk
```

```csharp
builder.Services.AddKeycloakAdminHttpClient(builder.Configuration);

app.MapGet("/users", async (IKeycloakUserClient client) =>
    await client.GetUsers("my-realm"));
```

---

### Essential Patterns

- Configuration section: defaults to `"Keycloak"`, override via `configSectionName` parameter
- IHttpClientBuilder: all HTTP clients return `IHttpClientBuilder` for resilience, handlers, etc.
- Token management: use `Duende.AccessTokenManagement` for service account tokens
- OpenTelemetry: `AddKeycloakAuthServicesInstrumentation()` for metrics and tracing
- Aspire: `AddKeycloakContainer("keycloak")` + `AddRealm("Test")` for local dev

---

### Where to go next

- [administration.md](administration.md) for creating the realm, clients, roles, and resources this consumes.
- `api-design` for the status codes and problem bodies an authorization failure should return.
- `security-review` for reviewing the authentication and authorization design as a whole.
- `build-dependency-management` for pinning the package versions across a multi-project solution.
- `observability-and-logging` for what the OpenTelemetry instrumentation should feed into.

---

### Checklist

- [ ] `verify-token-audience` is on, so a token minted for another client is rejected.
- [ ] `ssl-required` is `external` or `all` outside local development, never `none`.
- [ ] The client secret comes from configuration or a secret store, never from a committed `appsettings.json`.
- [ ] Authorization policies name realm or client roles explicitly, rather than checking a raw claim.
- [ ] Resource protection uses the Authorization Server where per-resource permission is genuinely needed.
- [ ] Service-account tokens are cached and refreshed through a token manager, not requested per call.
- [ ] OpenTelemetry instrumentation is registered so token failures are visible in traces.
