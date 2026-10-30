# TypeScript walkthrough

Contents:

- [Port definitions](#port-definitions)
- [Use case](#use-case)
- [Outbound adapter](#outbound-adapter)
- [Composition root](#composition-root)
- [What to notice](#what-to-notice)
- [Related skills](#related-skills)

A complete vertical slice in TypeScript: ports, a use case, an outbound adapter, and the composition root that binds
them. Read this when you want the concrete shape rather than the rule.

---

### Port definitions

```typescript
export interface OrderRepositoryPort {
  save(order: Order): Promise<void>;
  findById(orderId: string): Promise<Order | null>;
}

export interface PaymentGatewayPort {
  authorize(input: {
    orderId: string;
    amountCents: number;
    idempotencyKey: string;
  }): Promise<{ authorizationId: string }>;
}
```

### Use case

```typescript
type CreateOrderInput = {
  orderId: string;
  amountCents: number;
};

type CreateOrderOutput = {
  orderId: string;
  authorizationId: string;
};

export class CreateOrderUseCase {
  constructor(
    private readonly orderRepository: OrderRepositoryPort,
    private readonly paymentGateway: PaymentGatewayPort
  ) {}

  async execute(input: CreateOrderInput): Promise<CreateOrderOutput> {
    const order = Order.create({ id: input.orderId, amountCents: input.amountCents });
    await this.orderRepository.save(order);

    const auth = await this.paymentGateway.authorize({
      orderId: order.id,
      amountCents: order.amountCents,
      idempotencyKey: order.id,
    });

    await this.orderRepository.save(order.markAuthorized(auth.authorizationId));

    return {
      orderId: order.id,
      authorizationId: auth.authorizationId,
    };
  }
}
```

### Outbound adapter

```typescript
export class PostgresOrderRepository implements OrderRepositoryPort {
  constructor(private readonly db: SqlClient) {}

  async save(order: Order): Promise<void> {
    await this.db.query(
      "insert into orders (id, amount_cents, status, authorization_id) values ($1, $2, $3, $4) " +
        "on conflict (id) do update set status = excluded.status, authorization_id = excluded.authorization_id",
      [order.id, order.amountCents, order.status, order.authorizationId]
    );
  }

  async findById(orderId: string): Promise<Order | null> {
    const row = await this.db.oneOrNone("select * from orders where id = $1", [orderId]);
    return row ? Order.rehydrate(row) : null;
  }
}
```

### Composition root

```typescript
export const buildCreateOrderUseCase = (deps: { db: SqlClient; stripe: StripeClient }) => {
  const orderRepository = new PostgresOrderRepository(deps.db);
  const paymentGateway = new StripePaymentGateway(deps.stripe);

  return new CreateOrderUseCase(orderRepository, paymentGateway);
};
```

---

### What to notice

- The use case names only port types. Nothing in it knows Postgres or Stripe exists.
- The order is saved before the payment is authorized, and the order id doubles as the provider's idempotency key. A
  crash between the two calls leaves a pending order rather than a charge with no order, and a client retry reuses
  the same key, so the provider authorizes once.
- `markAuthorized` returns a new `Order` rather than mutating one, so no caller holds a half-updated entity.
- `save` is an upsert, so the second save after authorization updates the row the first one wrote.
- The adapter is the only place a SQL string appears, and the only place a database row becomes a domain object.
- The composition root is a plain function. Swapping `PostgresOrderRepository` for an in-memory fake in a test needs no
  container and no framework.

---

### Related skills

- `hexagonal-architecture` for the boundary rules this slice follows.
- `node-backend-patterns` for the Express or Next.js inbound adapter around the use case.
- `react-patterns` when a similar boundary is wanted on the client.
