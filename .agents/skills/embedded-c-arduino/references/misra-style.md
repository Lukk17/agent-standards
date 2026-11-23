# MISRA C:2012 Style

How MISRA C:2012 is applied, and the formatting and naming rules beside it. The memory, timing, and interrupt rules live in [SKILL.md](../SKILL.md), and the MISRA rules on `goto`, `setjmp` and recursion are in [core-rules-and-examples.md](core-rules-and-examples.md#every-loop-has-an-upper-bound).

---

### Style, MISRA C:2012

Treat every Required rule as mandatory and every Advisory rule as a default that needs a documented justification to deviate from. K&R braces, two-space indentation, `UPPER_SNAKE_CASE` for `#define`, `lower_snake_case` for functions. Cap a function at 50 executable lines and extract beyond that. Every `.c` and `.h` starts with one `SPDX-License-Identifier` line, the one comment every file carries because licence scanners read it. No other file header: git already records the author and the date, and the no-comments default in `coding-standards` and the Doc Comments rule in [SKILL.md](../SKILL.md) cover the rest.

Pass:

```c
static uint8_t crc8_update(uint8_t crc, uint8_t byte) {
  crc ^= byte;
  return crc;
}
```

Fail:

```c
static uint8_t CRC8Update(uint8_t crc, uint8_t byte)
{
    crc ^= byte; return crc;
}
```
