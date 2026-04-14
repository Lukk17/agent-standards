# Kubernetes Standards

Applies to all Kubernetes manifests and configurations. Universal rules in `universal-coding-standards.md` apply in addition to these.

---

## Image Versioning

- Never use `latest` image tags in any manifest. Pin to a specific immutable tag or digest.
- For production deployments, prefer pinning by digest (`image: myapp@sha256:...`) for full reproducibility.

---

## Resource Management

Every container spec must declare both `requests` and `limits`:

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

- Never omit `requests`; this causes the scheduler to make uninformed decisions.
- Set `limits.memory` conservatively to prevent OOM kills from cascading.
- Only set `limits.cpu` if the workload is known to be CPU-bound; unbounded CPU limits can cause throttling.

---

## Health Probes

Every Deployment and StatefulSet must declare all three probes:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 15

readinessProbe:
  httpGet:
    path: /readyz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10

startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 30
  periodSeconds: 5
```

- `livenessProbe`: restarts the container if the app is deadlocked.
- `readinessProbe`: removes the pod from load balancer endpoints until it is ready.
- `startupProbe`: prevents premature liveness kills during slow startup.

---

## Security

### RBAC
- Apply the principle of least privilege. Create dedicated `ServiceAccount` per application.
- Never use `cluster-admin` for application workloads.
- Never bind `ClusterRole` when a namespaced `Role` is sufficient.

### Secrets
- Never store secrets as plaintext in YAML files committed to version control.
- Use external secret management: Kubernetes `ExternalSecret` with a secrets manager (Vault, AWS Secrets Manager, etc.), or `SealedSecrets`.
- Do not use `kubectl create secret` in CI/CD pipelines without an auditable secret source.

### Pod Security
- Set `securityContext` on containers:
  ```yaml
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop: ["ALL"]
  ```
- Mount temporary directories as `emptyDir` when `readOnlyRootFilesystem: true` is set and the app writes to disk.

---

## Availability

- Set `replicas: 2` minimum for any production Deployment.
- Define a `PodDisruptionBudget` for every production workload:
  ```yaml
  spec:
    minAvailable: 1
    selector:
      matchLabels:
        app: my-app
  ```
- Use `RollingUpdate` deployment strategy with appropriate `maxUnavailable` and `maxSurge`.

---

## Configuration

- Use `ConfigMap` for non-sensitive configuration; reference it via `envFrom` or volume mounts.
- Never inline environment variables directly in the Deployment spec if they are shared across pods; use `ConfigMap`.
- Use `Namespace` to isolate workloads by team or environment.

---

## Labels and Annotations

Every resource must include standard labels:

```yaml
labels:
  app.kubernetes.io/name: my-app
  app.kubernetes.io/version: "1.2.3"
  app.kubernetes.io/component: backend
  app.kubernetes.io/part-of: my-platform
  app.kubernetes.io/managed-by: helm
```

---

## Networking

- Define `NetworkPolicy` to restrict ingress and egress to only what is necessary.
- Default-deny all traffic and whitelist explicitly.
- Use `Service` type `ClusterIP` internally; expose externally only via `Ingress` or `LoadBalancer` with justification.
