# Endpoint example in Django REST Framework

The create-user endpoint as a Django REST Framework view set in Python, called by an authenticated administrator: a 400 problem body when the `Idempotency-Key` header is missing or the body is not JSON, schema validation, a 422 problem body on failure, and a 201 with a `Location` header on success. Read this when you want a concrete shape to copy rather than the rule behind it. The same endpoint as a Next.js route handler is in [nextjs.md](nextjs.md), and in Go in [go.md](go.md).

---

### Python, Django REST Framework

```python
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.response import Response


class MissingIdempotencyKey(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Send an Idempotency-Key header so this request is safe to retry."
    default_code = "idempotency_key_missing"


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
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            raise MissingIdempotencyKey()

        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserService.create(**serializer.validated_data, idempotency_key=idempotency_key)
        return Response(
            {"data": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/users/{user.id}"},
        )
```

Configure an exception handler that renders `application/problem+json`, otherwise DRF returns its own error shape and
the contract splits in two.
