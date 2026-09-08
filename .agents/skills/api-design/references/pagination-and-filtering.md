# Pagination, filtering, sorting, and search

Read this when designing the query-parameter surface of a collection endpoint, or when a list endpoint slows down as
the table grows.

---

### Offset pagination

```text
GET /api/v1/users?page=2&per_page=20

SELECT * FROM users ORDER BY created_at DESC LIMIT 20 OFFSET 20;
```

It supports jumping to page N and is trivial to implement. It also degrades on large offsets, because the database
scans and discards every skipped row, and it skips or repeats rows when the underlying data changes between requests.

---

### Cursor pagination, the default for unbounded data

```text
GET /api/v1/users?cursor=eyJpZCI6MTIzfQ&limit=20

SELECT * FROM users WHERE id > :cursor_id ORDER BY id ASC LIMIT 21;
```

Fetch one row more than the page size to answer `has_next` without a second count query.

```json
{
  "data": [],
  "meta": { "has_next": true, "next_cursor": "eyJpZCI6MTQzfQ" }
}
```

Cost stays constant regardless of position and the page is stable under concurrent inserts. The trade is that a caller
cannot jump to an arbitrary page.

Sort on an indexed, immutable key, and tie-break on the primary key so the ordering is total. Keep the cursor opaque
(base64 of an internal structure) so its encoding stays yours to change, and reject a cursor that does not decode
rather than falling back to page one.

---

### Choosing between them

| Use case | Pagination |
| --- | --- |
| Admin dashboards, small fixed sets under 10k rows | Offset |
| Infinite scroll, feeds, unbounded collections | Cursor |
| Public APIs | Cursor, with offset only if a partner needs page numbers |
| Search results | Offset, because users expect numbered pages |

Cap `limit` server-side whichever you choose. An uncapped page size is an unauthenticated way to read the whole table.

---

### Filtering

```text
GET /api/v1/orders?status=active&customer_id=abc-123          # equality, flat notation
GET /api/v1/products?price[gte]=10&price[lte]=100             # bracket notation for ranges
GET /api/v1/orders?created_at[after]=2025-01-01
GET /api/v1/products?category=electronics,clothing            # comma for multiple values
GET /api/v1/orders?customer.country=US                        # dot notation for nested fields
```

Validate the field name against an allow-list before it reaches the query builder. A filter parameter that maps
straight onto a column name lets a caller filter, and therefore infer, columns you never meant to expose.

---

### Sorting

```text
GET /api/v1/products?sort=-created_at                         # leading minus for descending
GET /api/v1/products?sort=-featured,price,-created_at         # comma-separated, applied in order
```

Allow-list the sortable fields too, and require an index behind each one.

---

### Full-text search

```text
GET /api/v1/products?q=wireless+headphones                    # free-text across the searchable fields
GET /api/v1/users?email=alice                                 # field-specific match
```

Keep `q` distinct from field filters, because they combine: `?q=headphones&status=active` is one search inside one
filtered set.

---

### Sparse fieldsets

```text
GET /api/v1/users?fields=id,name,email
GET /api/v1/orders?fields=id,total,status&include=customer.name
```

Honour the field list all the way down to the query, not just in the serializer. Trimming the response after loading
every column saves bandwidth and nothing else.

---

### Related skills

- `api-design` for the response envelope these parameters produce.
- `postgres-patterns` for the indexes a sort or filter parameter needs.
- `backend-patterns` for the language-neutral cursor rules.
