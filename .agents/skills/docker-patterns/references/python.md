# Python Dockerfile

The reference multi-stage Dockerfile for a Python service. Like every image in this skill, it pins a specific tag plus its digest, with `<digest>` standing in for the value `docker buildx imagetools inspect <image>:<tag>` prints, builds in stages, drops to a non-root user before the runtime stage ends, and declares a `HEALTHCHECK`. The container rules live in [SKILL.md](../SKILL.md), and the layer rules every Dockerfile shares, apt-get layering, OCI labels and build-time secrets, are in [dockerfiles.md](dockerfiles.md).

---

### Builder and runner

```dockerfile
FROM python:3.14-slim@sha256:<digest> AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

FROM python:3.14-slim@sha256:<digest> AS runner
WORKDIR /app
RUN useradd -r -u 1001 appuser
USER appuser
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

The `site-packages` path carries the minor version, so it changes when the base image's minor version does. Bump
both lines together or the copy silently produces an image with no dependencies installed.
