# Web Accessibility Checklist

Run it before calling a component, a page or an audit accessible.

- Every interactive element is a native control, or has a justified reason not to be.
- One `h1` per page, and no skipped heading levels.
- The whole flow is operable by keyboard, in a sensible order, with a visible focus indicator throughout.
- Every dialog moves focus in, traps it, closes on Escape, and restores focus to its trigger.
- Client-side route changes move focus to the new content or a status region.
- Text meets 4.5:1, and large text, UI boundaries, and the focus ring meet 3:1.
- No state or meaning is carried by colour alone.
- Every image has a purposeful alt, or an empty alt when decorative.
- Non-essential motion is gated behind `prefers-reduced-motion`.
- Targets are at least 24 by 24 CSS pixels, with padding rather than a bigger icon.
- Every field has a real label, and every error is linked with `aria-describedby` and `aria-invalid`.
- The document language is set and layout uses logical properties.
- The keyboard path and a screen-reader pass have both been run by hand, not only a scanner.
