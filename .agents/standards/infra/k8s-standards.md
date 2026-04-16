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

---

## Autoscaling

- Define a `HorizontalPodAutoscaler` (HPA) for every production Deployment that handles variable traffic:
  ```yaml
  spec:
    minReplicas: 2
    maxReplicas: 20
    metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70
  ```
- For event-driven workloads (queue consumers), use **KEDA** `ScaledObject` instead of CPU-based HPA.
- Never set `minReplicas: 0` for services that must always be available.

---

## Resource Governance

- Define a `ResourceQuota` per namespace to cap total CPU, memory, and object counts:
  ```yaml
  spec:
    hard:
      requests.cpu: "10"
      requests.memory: 20Gi
      limits.cpu: "20"
      limits.memory: 40Gi
      pods: "50"
  ```
- Define a `LimitRange` per namespace to enforce default requests/limits on containers that omit them.
- Use **VPA** (Vertical Pod Autoscaler) in `Recommendation` mode for workloads with unpredictable resource patterns; review VPA recommendations before applying.

---

## Observability

- Annotate all pods with Prometheus scrape annotations:
  ```yaml
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
  ```
- Define a `ServiceMonitor` (Prometheus Operator CRD) for every service that exposes metrics to enable automatic Prometheus discovery.
- Expose a dedicated metrics port separate from the application port; do not multiplex application traffic and metrics on the same port.

---

## Policy Enforcement

- Deploy **Kyverno** or **OPA Gatekeeper** to enforce cluster-wide policies as admission webhooks.
- Enforce at minimum the Kubernetes **Baseline Pod Security Standard** on all non-system namespaces, and **Restricted** on production namespaces.
- Policies must be in `Enforce` mode in production; `Audit` mode is acceptable only during initial rollout.

---

## Persistent Volumes

- Select `StorageClass` explicitly; never rely on the cluster default storage class.
- Use `ReadWriteOnce` for single-pod workloads and `ReadWriteMany` only when multiple pods must share the volume concurrently (requires a compatible CSI driver).
- Define `VolumeSnapshotClass` and schedule automated volume snapshots for stateful workloads.
- Set `reclaimPolicy: Retain` on `PersistentVolume` objects backing production data to prevent accidental data loss on PVC deletion.

---

## Init Containers

- Use init containers for pre-start tasks: database migration execution, config file rendering, dependency health checks.
- Init containers must be idempotent; the pod must be able to restart and re-run init containers without corruption.
- Keep init container images minimal; prefer the same base image as the main container where possible.

---

## Admission Control

- Require `ValidatingWebhookConfiguration` for critical resource types (Deployments, Services, Ingresses) to enforce schema and policy checks before resources are persisted.
- Webhook failures must not silently allow invalid resources; set `failurePolicy: Fail` for security-critical webhooks.
