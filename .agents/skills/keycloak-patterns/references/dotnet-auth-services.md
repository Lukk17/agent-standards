# Keycloak.AuthServices Implementation Guide

Contents:

- [Packages Overview](#packages-overview)
- [Minimal Web API Setup](#minimal-web-api-setup)
- [Configuration Section](#configuration-section)
- [Adding Authorization (RBAC)](#adding-authorization-rbac)
- [Adding Authorization Server (Resource Protection)](#adding-authorization-server-resource-protection)
- [Adding Admin SDK](#adding-admin-sdk)
- [Essential Patterns](#essential-patterns)
- [Where to go next](#where-to-go-next)
- [Checklist](#checklist)

Wiring the Keycloak.AuthServices packages into an ASP.NET Core application: authentication, authorization, resource
protection, and the SDKs that talk back to Keycloak. This is the client side of the identity boundary, and it assumes
the realm and clients already exist.

Written for Keycloak.AuthServices 2 against Keycloak 26, on .NET 8 or newer.

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
    "verify-token-audience": true
  }
}
```

The client secret stays out of the committed file. In development keep it in user secrets:

```bash
dotnet user-secrets set "Keycloak:credentials:secret" "<client-secret>"
```

In a deployed environment set the `Keycloak__credentials__secret` environment variable from the platform's secret
store. Both bind into the same `Keycloak` section.

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
