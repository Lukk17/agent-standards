# Animation

Motion in React with the `motion` library, plus the reduced-motion rule that applies to every animation regardless of
how it is implemented.

The package is imported as `motion/react`. The old `framer-motion` package name is the previous name for the same
library, so a codebase still importing it should be migrated rather than mixed.

---

### List and presence animation

`AnimatePresence` is what makes an exit animation possible, because React would otherwise unmount the node
immediately. Every animated child needs a stable `key`.

```typescript
import { motion, AnimatePresence } from 'motion/react'

export function AnimatedMarketList({ markets }: { markets: Market[] }) {
  return (
    <AnimatePresence>
      {markets.map((market) => (
        <motion.div
          key={market.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          <MarketCard market={market} />
        </motion.div>
      ))}
    </AnimatePresence>
  )
}
```

---

### Modal animation

Animate the overlay and the panel separately so the backdrop can fade while the panel scales, and keep the whole
thing inside one `AnimatePresence` so both exit together.

```typescript
import { motion, AnimatePresence } from 'motion/react'

export function Modal({ isOpen, onClose, children }: ModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="modal-content"
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
```

An animated modal still needs focus moved into it, trapped while open, and restored to the trigger on close. See
[accessibility.md](accessibility.md) for the React mechanics and `web-accessibility` for the requirement.

---

### Reduced motion is not optional

Every animation and transition, CSS or JavaScript or library, respects the user's motion preference. For some people
large motion causes nausea and vertigo, so this is an accessibility requirement rather than a nicety.

```css
/* PASS: the animation has an off switch */
.slide-in {
  animation: slideIn 300ms ease-out;
}

@media (prefers-reduced-motion: reduce) {
  .slide-in {
    animation: none;
  }
}
```

```typescript
// PASS: the hook reads the same preference and flattens the movement
import { motion, useReducedMotion } from 'motion/react'

export function AnimatedCard({ children }: { children: React.ReactNode }) {
  const shouldReduceMotion = useReducedMotion()

  return (
    <motion.div
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.3 }}
    >
      {children}
    </motion.div>
  )
}

// FAIL: moves regardless of the preference
export function AnimatedCard({ children }: { children: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      {children}
    </motion.div>
  )
}
```

Opacity-only transitions are usually acceptable under a reduced-motion preference. Movement, parallax, and scale are
the parts to drop.

---

### Timing budgets

| Kind of transition | Duration |
| --- | --- |
| Micro-interaction, hover or focus | 100 to 150ms |
| Component transition, modal or drawer | 200 to 300ms |
| Page or route transition | 300 to 500ms |
| Anything at all | never above 500ms |

Above 500ms an interface stops feeling responsive and starts feeling broken.

---

### Token-driven CSS transitions

Durations and easings come from the design system, not from a number typed into a component stylesheet.

```css
/* PASS: token-driven and motion-safe */
.btn {
  transition: background-color var(--duration-fast, 150ms) var(--ease-out, ease);
}

@media (prefers-reduced-motion: reduce) {
  .btn {
    transition: none;
  }
}
```

```css
/* FAIL: hardcoded timing, no preference check */
.btn {
  transition: background-color 420ms ease-in-out;
}
```
