---
name: embedded-c-arduino
description: Embedded C and Arduino standards for heap-free memory, bounded loops and watchdogs, non-blocking millis state machines, flag-and-return ISRs, MISRA C:2012 rules, a hardware abstraction layer and host-side unit tests. Use when the user says "replace this delay with a state machine", "write the ISR for this encoder" or "my sketch runs out of SRAM". Not for the PCB the firmware runs on, use `kicad`.
---

# Embedded C and Arduino Standards

How firmware stays predictable on a part with a few kilobytes of RAM and no operating system underneath: nothing allocates, nothing blocks, and nothing that runs in an interrupt does real work. Every rule removes a failure that is untraceable once the device is in the field.

Written for C11 with MISRA C:2012 as the rule set, the Arduino AVR and ESP32 cores, and Ceedling with Unity and CMock for host-side tests.

| Task | Open |
|---|---|
| The Pass and Fail code behind any rule below, including the full `millis()` state machine and the AVR and ESP32 ISR patterns | [references/core-rules-and-examples.md](references/core-rules-and-examples.md) |
| Sleep modes and power gating, FreeRTOS task and ISR rules, serial protocol versioning, and dual-bank OTA with rollback | [references/rtos-ota-and-protocols.md](references/rtos-ota-and-protocols.md) |
| MISRA and formatting rules, Arduino library API conventions, and the Ceedling, Unity and CMock host test setup | [references/style-and-testing.md](references/style-and-testing.md) |

---

### When to activate

- Writing or reviewing `.c`, `.h`, or `.ino` firmware.
- Replacing `delay()` with non-blocking timing, or diagnosing a loop that misses events.
- Writing or reviewing an interrupt service routine.
- Chasing an SRAM exhaustion, a stack overflow, or a corrupted buffer.
- Introducing a hardware abstraction layer so logic can be tested off-target.
- Setting up Ceedling, Unity, or CMock for host-side unit tests.
- Adding a hardware watchdog to a sketch that can hang.

---

### When not to activate

- Designing the board the firmware runs on, use `kicad`.
- Slicing or printing an enclosure for it, use `g-code-3d-printing`.
- Writing the host-side tool that flashes or talks to the device, use `bash` or `powershell`.
- Building a service that ingests the device's telemetry, use `backend-patterns`.
- Automating the device from Home Assistant, use `home-assistant`.

---

### Rules

1. No heap, ever: `malloc`, `calloc`, `realloc` and `free` are prohibited, because fragmentation on a constrained MCU fails after hours of uptime and never on the bench. The C++ `String` class is prohibited on AVR for the same reason: it allocates on every concatenation. Use a bounded `static` buffer.
2. Put every read-only lookup table, string and large constant in Flash with `PROGMEM`, give every array and buffer a declared bound, and profile SRAM usage before each release.
3. Every `while` and `for` has an upper bound, including under a hardware fault or a disconnected peripheral. On anything safety-critical add a hardware watchdog and reset it from the main loop, so a hung path recovers.
4. No `goto` (MISRA C:2012 Rule 15.1, Advisory, adopted here as mandatory), no `setjmp` or `longjmp` (Rule 21.4, Required, which bans `<setjmp.h>`), and no direct or indirect recursion (Rule 17.2, Required), which has no stack cost you can compute at review time.
5. No `delay()`, which stops the whole program. Every periodic or timed behaviour is a state machine driven by `millis()` or a hardware timer, so the main loop keeps servicing everything else.
6. Compare elapsed time as `now - since >= interval`, never `now >= since + interval`: the subtraction is correct across the `millis()` rollover at about 49.7 days, the addition overflows and stalls the state machine there.
7. A timed task takes `now_ms` as a parameter rather than calling `millis()` itself, which makes it testable on the host with a synthetic clock.
8. An ISR records what happened, sets a `volatile` flag and returns. Blocking calls, `Serial.print` and allocation inside an ISR deadlock or corrupt state, because the code they call is not reentrant.
9. Every variable shared between an ISR and the main loop is `volatile`, or the compiler caches it in a register. Copy a multi-byte shared value inside `noInterrupts()` / `interrupts()` containing nothing but the copy, because an 8-bit core reads a 32-bit value in four instructions and an interrupt between them tears it.
10. On a dual-core ESP32, disabling interrupts masks only the calling core. Attach the handler with `attachInterrupt`, place it in IRAM with `IRAM_ATTR`, and guard shared state with a `portMUX_TYPE` spinlock: `taskENTER_CRITICAL_ISR` in the handler, `taskENTER_CRITICAL` in the main loop.
11. Use `<stdint.h>` types for every register-level and protocol value, because bare `int`, `long` and `short` change size between AVR and ESP32 builds. Use `size_t` for buffer lengths and array indices.
12. Keep register access behind a HAL (`hal_gpio_write`, `hal_gpio_read`, `hal_uart_send`, `hal_uart_recv`, `hal_spi_transfer`), each peripheral in its own translation unit such as `hal_gpio_avr.c`, so the logic compiles and runs on a host with no hardware attached.
13. Test on the host: Unity for tests, CMock for mocks, Ceedling to orchestrate (`ceedling test:all`), never by flashing a board. Mock every HAL function, mirror `src/` under `test/`, and reach at least 80 percent branch coverage on business-logic modules.

---

### Doc Comments

Doxygen blocks follow "Doc Comments" in `coding-standards`. The C delta: write the prose as one `@brief` line, mark every pointer `@param[in]` or `@param[out]` because a bare pointer type does not say which, say whether it may be null and who owns the buffer afterwards, and name every status code or errno a caller can branch on, since C has no exceptions and the return type rarely names them.

---

### Related skills

- `kicad` for the board, its decoupling, and its connector pinout.
- `g-code-3d-printing` for the printed enclosure.
- `bash` and `powershell` for flashing, log capture, and CI scripts.
- `home-assistant` for integrating the finished device into a home system.
- `coding-standards` for the naming and control-flow floor this skill sits on top of.

---

### Checklist

- [ ] No `malloc`, `free`, or C++ `String` anywhere in the build.
- [ ] Every lookup table and constant string in `PROGMEM`, every buffer bounded.
- [ ] SRAM usage profiled before the release.
- [ ] Every loop bounded, watchdog reset from the main loop on safety-critical builds.
- [ ] No `goto`, `setjmp`, `longjmp`, or recursion.
- [ ] No `delay()`, timing done by a `millis()` state machine using subtraction for elapsed time.
- [ ] Every ISR sets a `volatile` flag and returns, no printing, blocking, or allocation.
- [ ] Multi-byte shared variables read inside the shortest possible `noInterrupts()` section, or a spinlock critical section on ESP32.
- [ ] Every register and protocol value uses a `<stdint.h>` type.
- [ ] MISRA C:2012 Required rules met, deviations documented.
- [ ] All register access sits behind the HAL.
- [ ] Ceedling suite passes on the host, at least 80 percent branch coverage on logic modules.
