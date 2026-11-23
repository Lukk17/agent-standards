# .NET Integration Examples

Short Keycloak.AuthServices snippets, one per feature: JWT Bearer, OIDC, roles, resource protection and the Admin SDK. Open it for the smallest working shape of a feature. Each one is covered in depth in its own .NET reference, and token validation on any other platform is in [token-validation.md](token-validation.md).

---

### .NET (Keycloak.AuthServices)

#### JWT Bearer Authentication (Web API)

```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddKeycloakWebApiAuthentication(builder.Configuration);
builder.Services.AddAuthorization();

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/protected", () => "Hello!").RequireAuthorization();
app.Run();
```

```json
// appsettings.json
{
  "Keycloak": {
    "AuthServerUrl": "https://keycloak.example.com",
    "Realm": "my-realm",
    "Resource": "my-client",
    "VerifyTokenAudience": true
  }
}
```

#### OIDC Authentication (Web App)

```csharp
builder.Services.AddKeycloakWebAppAuthentication(builder.Configuration);
```

#### Authorization with Roles

```csharp
builder.Services.AddKeycloakAuthorization(builder.Configuration)
    .AddAuthorizationBuilder()
    .AddPolicy("AdminOnly", policy => policy.RequireRealmRoles("admin"))
    .AddPolicy("EditorOnly", policy => policy.RequireResourceRoles("editor"));
```

#### Resource Protection (Authorization Server)

```csharp
builder.Services.AddAuthorizationServer(builder.Configuration);

// Attribute-based
[ProtectedResource("documents", "read")]
public class DocumentsController : ControllerBase { }
```

#### Admin SDK

```csharp
builder.Services.AddKeycloakAdminHttpClient(builder.Configuration);

// Inject and use
app.MapGet("/users", async (IKeycloakUserClient client) =>
    await client.GetUsers("my-realm"));
```
