# React Patterns Checklist

Run it before calling a React change or a React review done.

- Every top-level component is a named function declaration, except an error boundary, which React supports only as a class component.
- Component families are composed, not configured through a growing flag surface.
- Every async operation exposes one `AsyncState` union, not separate data, loading, and error flags.
- No component or hook calls `fetch` directly, and every endpoint lives in the typed API client.
- With React Compiler on, a hand-written `useMemo`, `useCallback`, or `React.memo` is an escape hatch with a stated reason. Without it, each traces back to a measurement.
- No sort, splice, or reverse mutates a prop or a state value in place.
- Heavy client-only modules are lazy loaded, and lists past a few hundred rows are virtualised.
- Every user-facing string goes through the i18n layer, keys and identifiers are English, and no component hard-codes a locale.
- Every animation respects `prefers-reduced-motion`.
- Doc comments follow `coding-standards`, and a prop is documented on its props type, never as a `@param` on the component.
