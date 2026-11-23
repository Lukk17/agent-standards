# pydantic-settings

Typed settings read from the environment and validated at startup. Open this when a service or a command-line tool reads configuration or a credential.

---

### Read configuration through pydantic-settings

Settings are typed, validated at startup, and sourced from the environment. A missing or malformed variable fails the
process immediately rather than at the first request that needs it.

```python
class Settings(BaseSettings):
    database_url: str
    secret_key: SecretStr
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

Wrap every credential in `SecretStr` so it cannot leak through a repr or a log line.
