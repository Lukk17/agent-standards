# React

The token rule as it shows up in a React component. Open it when a component written in JSX sets a visual value, or when generate mode runs on a React codebase.

---

### Reference the token from the component

A value typed into a `style` prop is a hex code in a component file, the same as one typed into a stylesheet. The component names the token and the token file owns the value.

```tsx
// PASS: the component references the token
<Button style={{ background: 'var(--color-primary-500)' }} />

// FAIL: the value is welded into the component
<Button style={{ background: '#2563eb' }} />
```

---

### Generate mode in a React project

Generate mode scans the styled-components templates for the values already in use, beside the CSS.
