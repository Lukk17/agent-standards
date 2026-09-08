# Server Actions

Mutations that run on the server, work without client JavaScript, and invalidate their own caches.

---

### Shape of an action

Mark the module or the function with `'use server'`, validate the input, do the work, invalidate what the work
dirtied, and return a typed result the caller can branch on. Never return a raw exception to the client.

```typescript
// app/actions/cart.ts
'use server'

import { revalidateTag } from 'next/cache'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { z } from 'zod'

const addToCartSchema = z.object({ productId: z.string().uuid() })

export async function addToCart(productId: string) {
  const parsed = addToCartSchema.safeParse({ productId })
  if (!parsed.success) {
    return { error: 'Invalid product' }
  }

  const cookieStore = await cookies()
  const sessionId = cookieStore.get('session')?.value

  if (!sessionId) {
    redirect('/login')
  }

  try {
    await db.cart.upsert({
      where: { sessionId_productId: { sessionId, productId } },
      update: { quantity: { increment: 1 } },
      create: { sessionId, productId, quantity: 1 },
    })

    revalidateTag('cart')
    return { success: true }
  } catch {
    return { error: 'Failed to add item to cart' }
  }
}
```

---

### Actions as form handlers

Passing the action to a form's `action` prop makes the form work before hydration, which is the whole point of using
one instead of an `onSubmit` handler. `redirect` throws, so call it after the mutation succeeds and never inside a
`try` block that would swallow it.

```typescript
// app/actions/checkout.ts
'use server'

import { redirect } from 'next/navigation'
import { z } from 'zod'

const checkoutSchema = z.object({
  address: z.string().min(1, 'Address is required'),
  payment: z.string().min(1, 'Payment method is required'),
})

export async function checkout(formData: FormData) {
  const parsed = checkoutSchema.safeParse(Object.fromEntries(formData))
  if (!parsed.success) {
    return { errors: parsed.error.flatten().fieldErrors }
  }

  const order = await processOrder(parsed.data)

  redirect(`/orders/${order.id}/confirmation`)
}
```

```typescript
// app/checkout/page.tsx
import { checkout } from '@/app/actions/checkout'

export default function CheckoutPage() {
  return (
    <form action={checkout}>
      <label htmlFor="address">Delivery address</label>
      <input id="address" name="address" required />
      <label htmlFor="payment">Payment method</label>
      <input id="payment" name="payment" required />
      <button type="submit">Place order</button>
    </form>
  )
}
```

---

### Rules that keep actions safe

- Treat every argument as hostile. An action is a network endpoint, so validate the input even when the only caller
  you wrote is a trusted form.
- Authorise inside the action. A hidden button does not stop anyone from calling the action directly.
- Never accept an identifier that the server can derive itself. Read the session from `cookies()` rather than
  trusting a `userId` argument.
- Invalidate in the same function that mutates. `revalidateTag` for a data set, `revalidatePath` for a specific
  route, both when the change touches both.
- Return a discriminated result, never an exception message. Leaking a database error to the client is an
  information disclosure bug.

---

### Pairing with the client

`useTransition` gives a pending flag around an action call from a button. For form submissions, `useFormStatus` reads
the pending state of the enclosing form without threading it through props.

```typescript
'use client'

import { useFormStatus } from 'react-dom'

export function SubmitButton() {
  const { pending } = useFormStatus()
  return (
    <button type="submit" disabled={pending}>
      {pending ? 'Placing order...' : 'Place order'}
    </button>
  )
}
```
