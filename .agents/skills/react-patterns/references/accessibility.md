# Accessibility Mechanics in React

`web-accessibility` owns the requirements: what conformance means, which roles apply, how a screen reader announces
things, and what WCAG 2.2 AA demands. Read that skill first. This file only holds the React-side mechanics for the two
patterns that come up constantly, keyboard navigation and focus management.

---

### Keyboard navigation

A composite widget handles its own arrow keys. Arrow keys move the active option, Enter commits it, Escape closes,
and each handled key calls `preventDefault` so the page does not scroll underneath.

```typescript
export function Dropdown({ options, onSelect }: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setActiveIndex((i) => Math.min(i + 1, options.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setActiveIndex((i) => Math.max(i - 1, 0))
        break
      case 'Enter':
        e.preventDefault()
        onSelect(options[activeIndex])
        setIsOpen(false)
        break
      case 'Escape':
        setIsOpen(false)
        break
    }
  }

  return (
    <div
      role="combobox"
      aria-expanded={isOpen}
      aria-haspopup="listbox"
      aria-activedescendant={isOpen ? `option-${activeIndex}` : undefined}
      onKeyDown={handleKeyDown}
    >
      {/* listbox and options */}
    </div>
  )
}
```

Before building one of these, check whether a native `select`, `details`, or `dialog` does the job. The platform
element already has the keyboard behaviour, the role, and the screen-reader announcements, and it will not drift.

---

### Focus management

Opening a dialog moves focus into it, keeps focus inside while it is open, and returns focus to the element that
opened it on close. Skipping the last step drops the user at the top of the document.

```typescript
export function Modal({ isOpen, onClose, children }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!isOpen) return

    previousFocusRef.current = document.activeElement as HTMLElement
    modalRef.current?.focus()

    return () => {
      previousFocusRef.current?.focus()
    }
  }, [isOpen])

  return isOpen ? (
    <div
      ref={modalRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      tabIndex={-1}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      {children}
    </div>
  ) : null
}
```

Restoring focus in the effect cleanup rather than in an `else` branch means it also runs when the modal unmounts
while open, which is the case a route change hits.

This example moves and restores focus but does not trap it. `web-accessibility` has the trap implementation and the
rest of the dialog requirements.

---

### What this file does not decide

- Whether a pattern needs ARIA at all, and which role is correct.
- Contrast ratios, focus indicator visibility, and target sizes.
- Form label, `aria-invalid`, and `aria-describedby` wiring.
- Live region behaviour and announcement timing.
- How to test with a screen reader.

All of it lives in `web-accessibility`.
