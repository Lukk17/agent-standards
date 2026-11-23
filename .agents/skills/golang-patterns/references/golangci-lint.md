# golangci-lint

Running `golangci-lint` and the v2 configuration that backs it. Open this when setting the linter up, or when a v1 configuration file has started failing. The Go commands around it are in [tooling.md](tooling.md).

Written for golangci-lint v2. Confirm with `golangci-lint version` before assuming.

---

### Run the linter

`golangci-lint` runs the wider set, including `go vet` itself:

```bash
golangci-lint run
```

Apply the fixes the enabled linters can make safely:

```bash
golangci-lint run --fix
```

---

### golangci-lint v2 configuration

Version 2 changed the schema. A v1 file fails on startup rather than degrading, so it has to be converted rather than
left alone.

```yaml
version: "2"

linters:
  default: standard
  enable:
    - misspell
    - unconvert
    - unparam
  settings:
    errcheck:
      check-type-assertions: true
    govet:
      enable:
        - shadow
  exclusions:
    presets:
      - comments
      - std-error-handling

formatters:
  enable:
    - gofmt
    - goimports
```

What changed from v1, and why a v1 file no longer loads:

| v1 | v2 |
| --- | --- |
| No `version` key | `version: "2"` is required as the first key |
| `linters-settings:` at the top level | `linters.settings:` nested under `linters` |
| `issues.exclude-use-default: false` | Removed. Default exclusions are opt-in through `linters.exclusions.presets` |
| `govet.check-shadowing: true` | Removed. Enable the analyzer with `govet.enable: [shadow]` |
| `gosimple` as its own linter | Merged into `staticcheck`, which now reports its checks |
| `gofmt` and `goimports` under `linters` | Moved to the top-level `formatters` section |

`default: standard` enables `errcheck`, `govet`, `ineffassign`, `staticcheck`, and `unused`, so those need no entry
under `enable`. Listing them again is harmless but says nothing.

Convert an existing file rather than rewriting it by hand:

```bash
golangci-lint migrate
```
