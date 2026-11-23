# Data types

Open this for the column type table and the reasoning behind the type rules in [SKILL.md](../SKILL.md).

---

### Choose the type that cannot be wrong

| Use case | Correct type | Avoid |
| --- | --- | --- |
| Identifiers | `bigint`, or `uuid` v7 when it must be client-generated | `int`, random `uuid` v4 as a primary key |
| Strings | `text` | `varchar(255)` |
| Timestamps | `timestamptz` | `timestamp` |
| Money | `numeric(12,2)`, or an integer count of minor units | `float`, `real` |
| Flags | `boolean` | `varchar`, `int` |

Pass: `amount_minor bigint NOT NULL` for money, so no rounding exists to get wrong.

Fail: `price float`, which cannot represent 0.1 exactly and silently drifts across arithmetic.

`varchar(n)` buys no performance over `text` in PostgreSQL, and the length limit becomes a migration the first time the
business changes its mind.
