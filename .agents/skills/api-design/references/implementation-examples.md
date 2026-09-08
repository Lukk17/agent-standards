# Endpoint implementation examples

The same create-user endpoint in three stacks: schema validation, a 422 problem body on failure, and a 201 with a
`Location` header on success. Read this when you want a concrete shape to copy rather than the rule behind it.

---

### TypeScript, Next.js route handler

```typescript
import { z } from "zod";
import { NextRequest, NextResponse } from "next/server";

const createUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
});

export async function POST(req: NextRequest) {
  const idempotencyKey = req.headers.get("Idempotency-Key");
  const parsed = createUserSchema.safeParse(await req.json());

  if (!parsed.success) {
    return NextResponse.json({
      type: "https://example.com/errors/validation",
      title: "Validation Failed",
      status: 422,
      detail: "Request validation failed",
      errors: parsed.error.issues.map((i) => ({ field: i.path.join("."), message: i.message, code: i.code })),
    }, { status: 422, headers: { "Content-Type": "application/problem+json" } });
  }

  const user = await createUser(parsed.data, idempotencyKey);

  return NextResponse.json({ data: user }, { status: 201, headers: { Location: `/api/v1/users/${user.id}` } });
}
```

---

### Python, Django REST Framework

```python
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response


class CreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(max_length=100)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "created_at"]


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return CreateUserSerializer if self.action == "create" else UserSerializer

    def create(self, request):
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserService.create(**serializer.validated_data)
        return Response(
            {"data": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/users/{user.id}"},
        )
```

Configure an exception handler that renders `application/problem+json`, otherwise DRF returns its own error shape and
the contract splits in two.

---

### Go, net/http

```go
func (h *UserHandler) CreateUser(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeProblem(w, http.StatusBadRequest, "https://example.com/errors/invalid-json", "Invalid Request Body")
        return
    }

    if err := req.Validate(); err != nil {
        writeProblem(w, http.StatusUnprocessableEntity, "https://example.com/errors/validation", "Validation Failed")
        return
    }

    user, err := h.service.Create(r.Context(), req)
    if err != nil {
        switch {
        case errors.Is(err, domain.ErrEmailTaken):
            writeProblem(w, http.StatusConflict, "https://example.com/errors/email-taken", "Email Already Registered")
        default:
            writeProblem(w, http.StatusInternalServerError, "https://example.com/errors/internal", "Internal Server Error")
        }
        return
    }

    w.Header().Set("Location", fmt.Sprintf("/api/v1/users/%s", user.ID))
    writeJSON(w, http.StatusCreated, map[string]any{"data": user})
}
```

`writeProblem` sets `Content-Type: application/problem+json` and is the only place a Go handler builds an error body.

---

### Related skills

- `api-design` for the contract these handlers implement.
- `node-backend-patterns`, `python-patterns`, and `golang-patterns` for the surrounding service structure.
- `springboot-patterns` for the Java and Spring Boot equivalent.
