# Application Controls in Java and Spring

The code for the application controls in Java with Spring Security. Open this when the code under review is Java. The reasoning is in [application-controls.md](application-controls.md), and Spring Security configuration and wiring belong to `springboot-patterns`.

---

### Password hashing

Argon2id is the primary choice, and `Argon2PasswordEncoder` provides it in Spring.

```java
PasswordEncoder encoder = new Argon2PasswordEncoder(16, 32, 1, 65536, 3);
String stored = encoder.encode(rawPassword);
encoder.matches(rawPassword, stored);
```

---

### Rate limiting

The Spring implementation of the rate-limit policy is in `springboot-patterns`, under `references/security.md`.
