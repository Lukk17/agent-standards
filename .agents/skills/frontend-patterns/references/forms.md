# Forms, Errors, and Internationalisation

Controlled forms with validation, the error boundary that catches what escapes them, and the i18n layer every string
passes through.

---

### Controlled form with validation

Validation returns a map of field errors rather than a boolean, so each message can render next to its own field.
Every visible string is looked up through the i18n layer.

```typescript
interface FormValues {
  name: string
  description: string
  endDate: string
}

type FormErrors = Partial<Record<keyof FormValues, string>>

export function CreateMarketForm() {
  const { t } = useTranslation()
  const [values, setValues] = useState<FormValues>({ name: '', description: '', endDate: '' })
  const [errors, setErrors] = useState<FormErrors>({})

  const validate = (): boolean => {
    const next: FormErrors = {}

    if (!values.name.trim()) {
      next.name = t('markets.form.errors.nameRequired')
    } else if (values.name.length > 200) {
      next.name = t('markets.form.errors.nameTooLong')
    }

    if (!values.description.trim()) {
      next.description = t('markets.form.errors.descriptionRequired')
    }

    if (!values.endDate) {
      next.endDate = t('markets.form.errors.endDateRequired')
    }

    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    await api.markets.create(values)
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <label htmlFor="market-name">{t('markets.form.name')}</label>
      <input
        id="market-name"
        value={values.name}
        onChange={(e) => setValues((prev) => ({ ...prev, name: e.target.value }))}
        aria-invalid={Boolean(errors.name)}
        aria-describedby={errors.name ? 'market-name-error' : undefined}
      />
      {errors.name && (
        <p id="market-name-error" className="error">
          {errors.name}
        </p>
      )}

      <button type="submit">{t('markets.form.submit')}</button>
    </form>
  )
}
```

For anything past a handful of fields, define the shape once as a schema and derive both the types and the validation
from it rather than writing the checks by hand. The wiring that makes an error reach a screen reader, and the rules
for labels, `aria-invalid`, and `aria-describedby`, belong to `web-accessibility`.

---

### Error boundary

An error boundary catches render-time errors below it and shows a fallback instead of an empty page. It does not
catch errors inside event handlers or async callbacks, so those still need their own handling.

```typescript
interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    reportError(error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} onRetry={() => this.setState({ hasError: false })} />
    }

    return this.props.children
  }
}
```

```typescript
<ErrorBoundary>
  <App />
</ErrorBoundary>
```

Place boundaries around regions that can fail independently, such as a dashboard widget, rather than only at the
root. One boundary at the root turns any failure into a blank application.

---

### Internationalisation

User-facing text never lives as a literal in JSX. Every label, placeholder, button, and message goes through one i18n
layer, looked up by key, so copy lives in translation catalogues and the UI stays translatable.

```typescript
import { useTranslation } from 'react-i18next'

export function SaveButton() {
  const { t } = useTranslation()
  return <button type="submit">{t('common.save')}</button>
}
```

Format numbers, dates, and currency through `Intl` rather than string concatenation, so the output follows the active
locale.

```typescript
const formatted = new Intl.NumberFormat(locale, { style: 'currency', currency: 'EUR' }).format(price)
```

Leave room for translated strings to grow, and use CSS logical properties so a right-to-left locale does not need a
separate stylesheet.
