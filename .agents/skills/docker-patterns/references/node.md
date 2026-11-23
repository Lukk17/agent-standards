# Node.js Dockerfile

The reference multi-stage Dockerfile for a Node.js service, development and production from one file. Like every image in this skill, it pins a specific tag plus its digest, with `<digest>` standing in for the value `docker buildx imagetools inspect <image>:<tag>` prints, builds in stages, drops to a non-root user before the runtime stage ends, and declares a `HEALTHCHECK`. The container rules live in [SKILL.md](../SKILL.md), and the layer rules every Dockerfile shares, apt-get layering, OCI labels and build-time secrets, are in [dockerfiles.md](dockerfiles.md).

---

### Development and production from one file

```dockerfile
FROM node:26-alpine@sha256:<digest> AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:26-alpine@sha256:<digest> AS dev
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM node:26-alpine@sha256:<digest> AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build && npm prune --production

FROM node:26-alpine@sha256:<digest> AS production
WORKDIR /app
RUN addgroup -g 1001 -S appgroup && adduser -S appuser -u 1001
USER appuser
COPY --from=build --chown=appuser:appgroup /app/dist ./dist
COPY --from=build --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=build --chown=appuser:appgroup /app/package.json ./
ENV NODE_ENV=production
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["node", "dist/server.js"]
```

The `dev` stage exists so Compose can target it with `build.target: dev` and get hot reload, while production builds
target `production` from the same file. Two Dockerfiles drift, one file with two stages cannot.
