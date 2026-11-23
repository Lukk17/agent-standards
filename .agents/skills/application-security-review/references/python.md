# Application Controls in Python

The pass and fail code for the application controls in Python: upload validation with `import magic`, password hashing with `argon2-cffi`, and JWT validation with `import jwt`. Open this when the code under review is Python. The reasoning behind each control is in [application-controls.md](application-controls.md) and [platform-security.md](platform-security.md).

---

### Upload validation

Fail: extension only.

```python
def validate_upload(filename: str) -> bool:
    return filename.lower().endswith((".jpg", ".png"))
```

Pass: every check, none sufficient alone. The server or proxy caps the request body before it is read, so an oversized
upload never reaches this function, and the signature is read from the first bytes only.

```python
import magic

ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif")
SIGNATURE_BYTES = 2048


def validate_upload(head: bytes, filename: str, declared_type: str, allowed_types: set[str]) -> bool:
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        return False
    if declared_type not in allowed_types:
        return False
    return magic.from_buffer(head[:SIGNATURE_BYTES], mime=True) in allowed_types
```

---

### Password hashing

Argon2id is the primary choice, and `argon2-cffi` provides it in Python.

```python
from argon2 import PasswordHasher

hasher = PasswordHasher()
stored = hasher.hash(password)
hasher.verify(stored, password)
```

---

### JWT validation

Validate `alg`, `exp`, `iss` and `aud` on every request, and pin the algorithm explicitly.

```python
import jwt

def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        options={"require": ["exp", "iss", "aud"]},
        audience="my-api",
        issuer="https://auth.example.com",
    )
```

Passing a wildcard or the token's own `alg` value into `algorithms` is the algorithm-confusion vulnerability: an
attacker re-signs the token with the public key as an HMAC secret and the library accepts it.
