# Helm Standards

Applies to all Helm charts. Kubernetes standards in `k8s-standards.md` and universal rules in `universal-coding-standards.md` apply in addition to these.

---

## Chart Structure

Every Helm chart must follow the standard layout:

```
my-chart/
  Chart.yaml          # Required: name, version, appVersion, description
  values.yaml         # Default values with inline documentation
  values-dev.yaml     # (optional) Dev environment overrides
  values-prod.yaml    # (optional) Prod environment overrides
  templates/
    _helpers.tpl      # Named templates and helper partials
    deployment.yaml
    service.yaml
    ingress.yaml
    configmap.yaml
    hpa.yaml
    pdb.yaml
    NOTES.txt         # Post-install instructions
  .helmignore
```

---

## Chart.yaml

Required fields:

```yaml
apiVersion: v2
name: my-chart
description: One-sentence description of what this chart deploys.
type: application
version: 1.0.0          # Chart version (SemVer); bump on every change
appVersion: "2.3.1"     # Application version being deployed
```

- Use SemVer for both `version` and `appVersion`.
- Bump `version` on every chart change, even minor template edits.
- `appVersion` must match the container image tag being deployed.

---

## values.yaml

- Every value must have an inline comment explaining its purpose and accepted values.
- Organize values by component (e.g., `image:`, `service:`, `ingress:`, `resources:`).
- Never hardcode environment-specific values in `values.yaml`; use override files.
- Use `null` as the default for optional values that must be explicitly provided (triggers validation).

Example:

```yaml
image:
  # Container registry and image name
  repository: my-registry/my-app
  # Image tag — must never be "latest" in production
  tag: "1.2.3"
  pullPolicy: IfNotPresent

resources:
  # Minimum resources guaranteed to the container
  requests:
    cpu: "100m"
    memory: "128Mi"
  # Maximum resources the container may consume
  limits:
    cpu: "500m"
    memory: "512Mi"
```

---

## Required Value Validation

Use `required` for values that have no safe default and must be explicitly provided:

```yaml
{{- $host := required "ingress.host is required" .Values.ingress.host }}
```

Use `fail` for values that must match a specific format or constraint:

```yaml
{{- if not (regexMatch "^[a-z][a-z0-9-]*$" .Values.appName) }}
{{- fail "appName must be lowercase alphanumeric with hyphens" }}
{{- end }}
```

---

## Templates

- Use `_helpers.tpl` for all repeated template fragments and label definitions.
- Define the standard label set using a helper:
  ```
  {{- define "my-chart.labels" -}}
  app.kubernetes.io/name: {{ include "my-chart.name" . }}
  app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
  app.kubernetes.io/managed-by: {{ .Release.Service }}
  {{- end }}
  ```
- Use `{{ include "my-chart.labels" . | nindent 4 }}` consistently; never duplicate label blocks.
- Wrap all top-level resource templates with `{{- if .Values.feature.enabled }}` guards for optional components.

---

## Image Tags

- Never set `image.tag` to `latest` in any `values.yaml` or override file for production environments.
- The `appVersion` in `Chart.yaml` should be the source of truth for which image version the chart deploys.
- Use `{{ .Values.image.tag | default .Chart.AppVersion }}` in templates to allow override while defaulting to chart's declared version.

---

## Versioning and Release

- Use semantic versioning: MAJOR for breaking changes to the chart API (values structure), MINOR for new features, PATCH for bug fixes.
- Document breaking changes in `Chart.yaml` under `annotations` or a `CHANGELOG.md` co-located with the chart.
- Use Helm `--atomic` flag in CI/CD pipelines to automatically roll back on failed deployments.

---

## Testing

- Every chart must include at minimum a `helm lint` check in CI.
- Use `helm template` + `kubeconform` or `kubeval` to validate rendered manifests against the Kubernetes API schema.
- Write `helm test` hooks for post-deploy smoke tests where applicable.
