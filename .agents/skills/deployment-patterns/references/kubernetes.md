# Kubernetes and Helm standards

Cluster-side defaults every production workload carries, and the Helm conventions that package them. The pipeline
and strategy rules live in [SKILL.md](../SKILL.md).

Baseline: Kubernetes 1.34 and Helm 4 (both verified locally).

---

### Probes

Three probes, three different questions. `startupProbe` answers "has it finished booting", and while it is failing
the other two are suspended, which is what stops a slow start from being killed as a liveness failure.
`livenessProbe` answers "is the process wedged", and a failure restarts the pod. `readinessProbe` answers "can it
serve right now", and a failure removes it from the Service endpoints without restarting it.

```yaml
startupProbe:
  httpGet:
    path: /health/liveness
    port: 3000
  periodSeconds: 5
  failureThreshold: 30

livenessProbe:
  httpGet:
    path: /health/liveness
    port: 3000
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/readiness
    port: 3000
  periodSeconds: 10
  failureThreshold: 2
```

Point liveness at a check that touches no dependency. Pointing it at a readiness endpoint that checks the database
turns a database blip into a cluster-wide restart storm.

---

### Pod security context, required on every deployment

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
```

---

### PodDisruptionBudget, required for every production deployment

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: my-app
```

`minAvailable` or `maxUnavailable`, either way the budget must make it impossible for a voluntary disruption, a node
drain during an upgrade, to take every replica down at once.

---

### NetworkPolicy, default deny

Every namespace starts with a default-deny policy. Allowances are then explicit and reviewable.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

Then open exactly what is needed, by label, by port:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-app-ingress
spec:
  podSelector:
    matchLabels:
      app: my-app
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: ingress-controller
      ports:
        - protocol: TCP
          port: 8080
```

---

### Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
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

`minReplicas: 2` is the floor that makes the PodDisruptionBudget satisfiable. Use KEDA for event-driven workloads
scaling on queue depth or Kafka lag, and VPA for right-sizing requests in non-production.

---

### Resource governance

Every namespace carries a `ResourceQuota` and a `LimitRange`, so one team's runaway workload cannot starve the
cluster and a pod with no explicit request still gets a sane one.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
```

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
spec:
  limits:
    - type: Container
      default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 100m
        memory: 128Mi
```

---

### Metrics scraping

Every service exposes Prometheus metrics through a `ServiceMonitor`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-app
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
    - port: metrics
      path: /actuator/prometheus
      interval: 15s
```

---

### Policy enforcement

Use Kyverno, preferred, or OPA Gatekeeper to enforce the rules above at admission rather than at review time:

- Require `securityContext.runAsNonRoot: true`.
- Require resource requests and limits on every container.
- Block images without a digest, or from a registry not on the approved list.
- Require a `PodDisruptionBudget` for any Deployment with `replicas > 1`.

A rule enforced by a policy engine cannot be forgotten in a hurry. A rule written in a document can.

---

### Stateful workload protection

Snapshot before any stateful upgrade:

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: pre-upgrade-snapshot
spec:
  volumeSnapshotClassName: csi-hostpath-snapclass
  source:
    persistentVolumeClaimName: my-data-pvc
```

Set `reclaimPolicy: Retain` on every production PersistentVolume, so deleting a claim does not delete the data.

---

### Helm charts

Every chart contains `Chart.yaml` with name, version, appVersion, description and maintainers, a `values.yaml` where
every configurable value carries an inline comment, `templates/_helpers.tpl` for shared named templates, and
`NOTES.txt` with post-install instructions.

Validate critical values at render time rather than letting a broken deployment reach the cluster:

```yaml
image:
  repository: {{ required "image.repository is required" .Values.image.repository }}
  tag: {{ required "image.tag is required" .Values.image.tag }}
```

Distribute charts through an OCI registry with `helm push` and `helm pull oci://`, commit `Chart.lock`, and deploy
with `--atomic` so a failed release rolls itself back rather than leaving a half-applied state. Never put a
plaintext secret in chart YAML, use External Secrets Operator or Sealed Secrets. Scan charts with Trivy and Checkov
before publishing.
