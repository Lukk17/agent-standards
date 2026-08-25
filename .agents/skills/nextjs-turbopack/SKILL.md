---
name: nextjs-turbopack
description: "Next.js 16+ and Turbopack: incremental bundling, FS caching, dev speed, and when to use Turbopack vs webpack."
origin: ECC
---

# Next.js and Turbopack

Next.js 16+ uses Turbopack by default for local development: an incremental bundler written in Rust that significantly
speeds up dev startup and hot updates.

---

### When to use

- Turbopack (default dev): Use for day-to-day development. Faster cold starts and HMR, especially in large applications.
- Webpack (legacy dev): Use only if you hit a Turbopack bug or rely on a webpack-specific plugin in dev. Disable it with
  `--webpack` (or `--no-turbopack` depending on your Next.js version; check the docs for your version).
- Production: Production build behavior (`next build`) may use Turbopack or webpack depending on the Next.js version;
  check the official Next.js documentation for your version.

Use this when developing or debugging Next.js 16+ applications, diagnosing slow dev startup or HMR, or optimizing
production bundles.

---

### How it works

- Turbopack: The incremental bundler for Next.js dev. It uses a file system cache, so restarts are much faster (for
  example, 5-14x in large projects).
- Default in dev: From Next.js 16 onward, `next dev` runs with Turbopack unless it is disabled.
- File system cache: Restarts reuse previous work; the cache is usually under `.next`, and no extra configuration is
  needed for basic use.
- Bundle Analyzer (Next.js 16.1+): An experimental Bundle Analyzer for inspecting the output and finding heavy
  dependencies; enable it via config or an experimental flag (see the Next.js documentation for your version).

---

### Examples

#### Commands

To run local development with Turbopack:

```bash
next dev
```

To create a production build:

```bash
next build
```

To start the production server after building:

```bash
next start
```

#### Usage

Run `next dev` for local development with Turbopack. Use the Bundle Analyzer to optimize code-splitting and trim large
dependencies (see the Next.js documentation). Prefer the App Router and server components where possible.

---

### Best practices

- Stay on a current Next.js 16.x version for stable Turbopack and caching behavior.
- If dev is slow, make sure you are on Turbopack (the default) and that the cache is not being cleared unnecessarily.
- For production bundle size issues, use the official Next.js bundle analysis tools for your version.