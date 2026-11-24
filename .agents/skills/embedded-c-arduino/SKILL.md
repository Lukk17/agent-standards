---
name: embedded-c-arduino
description: 'Embedded C and Arduino firmware rules: no heap, bounded loops, millis timing, flag-and-return ISRs, a HAL, host tests. Use when the user says "replace this delay" or "write this ISR". Not for the PCB, use `kicad`.'
metadata:
  version: "1.1.0"
---

# Embedded C and Arduino Standards

How firmware stays predictable on a part with a few kilobytes of RAM and no operating system underneath: nothing allocates, nothing blocks, and nothing that runs in an interrupt does real work. Every rule removes a failure that is untraceable once the device is in the field.

Written for C11 with MISRA C:2012 as the rule set, the Arduino AVR and ESP32 cores, and Ceedling with Unity and CMock for host-side tests.

| Task | Open |
|---|---|
| The Pass and Fail code behind any rule below: the `millis()` state machine, the ISR pattern, the Doxygen example | [core-rules-and-examples.md](references/core-rules-and-examples.md) |
| A dual-core ESP32: the ISR spinlock pattern | [esp32.md](references/esp32.md) |
| A battery-powered AVR target: sleep modes, power gating | [avr.md](references/avr.md) |
| FreeRTOS: priorities, stack sizing, mutexes, `FromISR` calls | [freertos.md](references/freertos.md) |
| A versioned serial frame, or a dual-bank OTA update with rollback | [protocols-and-ota.md](references/protocols-and-ota.md) |
| MISRA C:2012 treatment, formatting, naming, the file header | [misra-style.md](references/misra-style.md) |
| The public API of an Arduino library | [arduino-api.md](references/arduino-api.md) |
| Host tests with Ceedling, Unity and CMock | [ceedling.md](references/ceedling.md) |
| Before calling a firmware change done | [checklist.md](references/checklist.md) |

---

### When not to activate

- Designing the board the firmware runs on, use `kicad`.
- Slicing or printing an enclosure for it, use `g-code-3d-printing`.
- Writing the host-side tool that flashes or talks to the device, use `bash` or `powershell`.

---

### Rules

1. No heap, ever: `malloc`, `calloc`, `realloc` and `free` are prohibited, and so is the C++ `String` class on AVR. Use a bounded `static` buffer.
2. Put every read-only lookup table, string and large constant in Flash with `PROGMEM`, give every array and buffer a declared bound, and profile SRAM usage before each release.
3. Every `while` and `for` has an upper bound, including under a hardware fault or a disconnected peripheral. On anything safety-critical add a hardware watchdog and reset it from the main loop.
4. No `goto`, no `setjmp` or `longjmp`, and no direct or indirect recursion, which has no stack cost you can compute at review time.
5. No `delay()`, which stops the whole program. Every periodic or timed behaviour is a state machine driven by `millis()` or a hardware timer.
6. Compare elapsed time as `now - since >= interval`, never `now >= since + interval`, because only the subtraction is correct across the `millis()` rollover.
7. A timed task takes `now_ms` as a parameter rather than calling `millis()` itself, which makes it testable on the host with a synthetic clock.
8. An ISR records what happened, sets a `volatile` flag and returns. No blocking call, no `Serial.print` and no allocation inside an ISR.
9. Every variable shared between an ISR and the main loop is `volatile`. Copy a multi-byte shared value inside a critical section containing nothing but the copy. On a multi-core part, disabling interrupts masks only the calling core, so guard the shared state with a spinlock.
10. Use `<stdint.h>` types for every register-level and protocol value, and `size_t` for buffer lengths and array indices.
11. Keep register access behind a HAL, each peripheral in its own translation unit, so the logic compiles and runs on a host with no hardware attached.
12. Test on the host, never by flashing a board. Mock every HAL function, mirror `src/` under `test/`, and reach at least 80 percent branch coverage on business-logic modules.
13. Doxygen blocks follow "Doc Comments" in `coding-standards`, plus the C delta: one `@brief` line, `@param[in]` or `@param[out]` on every pointer, whether it may be null and who owns the buffer, and every status code or errno a caller can branch on.
