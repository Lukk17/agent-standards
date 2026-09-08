# Compose stacks, networking, and debugging

A reference local development stack, the override-file pattern, network isolation, and the commands that answer
"why can this container not reach that one". The rules live in [SKILL.md](../SKILL.md).

---

### A standard web application stack

```yaml
services:
  app:
    build:
      context: .
      target: dev
    ports:
      - "3000:3000"
    volumes:
      - .:/app
      - node_modules:/app/node_modules
    environment:
      - DATABASE_URL=postgres://postgres:postgres@db:5432/app_dev
      - REDIS_URL=redis://redis:6379/0
      - NODE_ENV=development
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    command: npm run dev

  db:
    image: postgres:18-alpine
    ports:
      - "127.0.0.1:5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app_dev
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:8-alpine
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redisdata:/data

  mailpit:
    image: axllent/mailpit:v1
    ports:
      - "8025:8025"
      - "1025:1025"

volumes:
  pgdata:
  redisdata:
  node_modules:
```

`.:/app` is the bind mount that gives hot reload. `node_modules:/app/node_modules` is a named volume layered on top
of it so the container's own dependencies, built for the container's platform, are not shadowed by whatever the host
installed. `condition: service_healthy` on `db` is what makes `depends_on` mean "ready" rather than "started".

---

### Override files

`docker-compose.override.yml` is loaded automatically and holds development-only settings:

```yaml
services:
  app:
    environment:
      - DEBUG=app:*
      - LOG_LEVEL=debug
    ports:
      - "9229:9229"
```

`docker-compose.prod.yml` is explicit and never auto-loads:

```yaml
services:
  app:
    build:
      target: production
    restart: always
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
```

Development starts with the override applied automatically:

```bash
docker compose up
```

Production composes the two files by name:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

### Networking

Services on the same Compose network resolve each other by service name, so `db` and `redis` are hostnames inside
`app`. There is never a reason to put an IP address in a connection string.

Split networks when a tier should be unreachable rather than merely unused:

```yaml
services:
  frontend:
    networks: [frontend-net]
  api:
    networks: [frontend-net, backend-net]
  db:
    networks: [backend-net]

networks:
  frontend-net:
  backend-net:
```

`db` sits only on `backend-net`, so `frontend` cannot reach it at all. That is enforcement, not convention.

Bind a published port to the loopback address (`"127.0.0.1:5432:5432"`) so it is reachable from the host but not
from the network the host is on, and omit `ports` entirely in production, where the service should only be reachable
inside the Docker network.

---

### Volume strategies

```yaml
services:
  app:
    volumes:
      - .:/app
      - node_modules:/app/node_modules
      - next_cache:/app/.next

  db:
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  node_modules:
  next_cache:
  pgdata:
```

A bind mount maps a host directory in, for source during development and for init scripts. A named volume holds
anything the container generates and the host should not shadow: dependencies, build caches, database data.

---

### Debugging

Follow one service's logs:

```bash
docker compose logs -f app
```

Open a shell inside a running service:

```bash
docker compose exec app sh
```

Check what is running and what it is consuming:

```bash
docker compose ps
```

```bash
docker stats
```

Rebuild after a Dockerfile change:

```bash
docker compose up --build
```

Force a full rebuild when a cached layer is stale:

```bash
docker compose build --no-cache app
```

Stop and remove containers, leaving volumes intact:

```bash
docker compose down
```

Remove volumes as well, which destroys the database:

```bash
docker compose down -v
```

---

### Debugging a network problem

Check name resolution from inside the container that is failing, not from the host:

```bash
docker compose exec app nslookup db
```

Then check that the port actually answers:

```bash
docker compose exec app wget -qO- http://api:3000/health
```

Inspect which containers are attached to a network:

```bash
docker network inspect <project>_default
```

Resolution failing means the service is on a different network or is not running. Resolution working with a refused
connection means the process inside is not listening on that port, or is bound to `127.0.0.1` inside the container
instead of `0.0.0.0`.
