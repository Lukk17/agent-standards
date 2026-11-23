# AVR

Detail for an AVR target. The rules that hold on every target are in [SKILL.md](../SKILL.md), and the ISR example in [core-rules-and-examples.md](core-rules-and-examples.md#isrs-set-a-flag-and-return) is already written in the AVR form.

---

### Power management and sleep modes

On a battery-powered target, sleeping is the design, not an optimisation added later.

- `SLEEP_MODE_PWR_DOWN` for the deepest sleep, woken only by an external interrupt.
- `SLEEP_MODE_IDLE` for light sleep, woken by any interrupt including a timer.

Enter sleep from the main loop's idle state and wake on an interrupt: a hardware timer, an external pin, or UART RX. Power-gate every unused peripheral (ADC, UART, SPI, TWI) through the Power Reduction Register (`PRR`, `PRR0`, `PRR1`) before sleeping, because a clocked-but-unused peripheral costs current for nothing.

Document the expected current in each sleep mode in the project's hardware notes, so a later regression in battery life has a number to be measured against.
