# Performance Examples in Python

The pass and fail code in Python for the N+1 query rule and the bounded memory rule. Open this when the slow path is Python. The reasoning behind each rule is in [worked-examples.md](worked-examples.md).

---

### Avoid the N+1 query

Fail: one query for the list, then one more per row.

```python
orders = order_repository.list_recent(limit=100)
for order in orders:
    order.customer = customer_repository.get(order.customer_id)
```

Pass: one query for the list, one for every customer it references.

```python
orders = order_repository.list_recent(limit=100)
customers = customer_repository.get_many({order.customer_id for order in orders})
for order in orders:
    order.customer = customers[order.customer_id]
```

---

### Keep memory bounded

Fail: the whole export is materialised in memory before the first byte is sent.

```python
rows = [format_row(row) for row in repository.fetch_all_orders()]
return Response("".join(rows), media_type="text/csv")
```

Pass: the rows are produced and released one at a time.

```python
def row_stream():
    for row in repository.iter_orders(chunk_size=1000):
        yield format_row(row)

return StreamingResponse(row_stream(), media_type="text/csv")
```
