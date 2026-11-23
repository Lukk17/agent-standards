# Endpoint example in Go

The create-user endpoint as a Go `net/http` handler, called by an authenticated administrator: a 400 problem body when the `Idempotency-Key` header is missing or the body is not JSON, schema validation, a 422 problem body on failure, and a 201 with a `Location` header on success. Read this when you want a concrete shape to copy rather than the rule behind it. The same endpoint as a Next.js route handler is in [nextjs.md](nextjs.md), and in Django REST Framework in [django-rest.md](django-rest.md).

---

### Go, net/http

```go
func (h *UserHandler) CreateUser(w http.ResponseWriter, r *http.Request) {
    idempotencyKey := r.Header.Get("Idempotency-Key")
    if idempotencyKey == "" {
        writeProblem(w, http.StatusBadRequest, "https://example.com/errors/idempotency-key-missing", "Idempotency-Key Required")
        return
    }

    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        writeProblem(w, http.StatusBadRequest, "https://example.com/errors/invalid-json", "Invalid Request Body")
        return
    }

    if err := req.Validate(); err != nil {
        writeProblem(w, http.StatusUnprocessableEntity, "https://example.com/errors/validation", "Validation Failed")
        return
    }

    user, err := h.service.Create(r.Context(), req, idempotencyKey)
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

The 409 for a taken email is acceptable only because an administrator calls this endpoint. On a self-service signup it
tells anyone whether an address has an account, so return 202 with the same generic message whether or not the address
exists, and send the "already registered" notice by email. OWASP's Authentication Cheat Sheet applies its generic error
message rule to account registration for the same reason.
