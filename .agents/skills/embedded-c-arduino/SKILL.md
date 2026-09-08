---
name: embedded-c-arduino
description: Embedded C and Arduino standards for heap-free memory discipline, bounded loops and watchdogs, non-blocking millis state machines, ISR flag-and-return, fixed-width integer types, MISRA C 2012 style, a hardware abstraction layer, and host-side unit tests. Use when you say "replace this delay with a state machine", "write the ISR for this encoder", "my sketch runs out of SRAM", "unit test this firmware on the host", or "add a watchdog". Not for the PCB the firmware runs on, use `kicad`.
---

# Embedded C and Arduino Standards

How firmware stays predictable on a part with a few kilobytes of RAM and no operating system underneath: nothing
allocates, nothing blocks, and nothing that runs in an interrupt does real work. The rules read as restrictive
because every one of them removes a failure that is untraceable once the device is in the field.

Baseline: C11 with MISRA C:2012 as the rule set, Arduino AVR and ESP32 cores at current stable, and Ceedling with
Unity and CMock for host-side tests.

---

### When to activate

- Writing or reviewing `.c`, `.h`, or `.ino` firmware.
- Replacing `delay()` with non-blocking timing, or diagnosing a loop that misses events.
- Writing or reviewing an interrupt service routine.
- Chasing an SRAM exhaustion, a stack overflow, or a corrupted buffer.
- Introducing a hardware abstraction layer so logic can be tested off-target.
- Setting up Ceedling, Unity, or CMock for host-side unit tests.

---

### When not to activate

- Designing the board the firmware runs on, use `kicad`.
- Slicing or printing an enclosure for it, use `g-code-3d-printing`.
- Writing the host-side tool that flashes or talks to the device, use `bash` or `powershell`.
- Building a service that ingests the device's telemetry, use `backend-patterns`.
- Automating the device from Home Assistant, use `home-assistant`.

---

### No heap, ever

`malloc`, `calloc`, `realloc`, and `free` are prohibited. Heap fragmentation on a constrained MCU produces failures
that appear after hours of uptime and cannot be reproduced on a bench. The C++ `String` class is prohibited on AVR
for the same reason: it allocates on every concatenation.

Pass:

```c
static char message_buffer[64];
```

Fail:

```c
String message = "temp: " + String(celsius);
```

Put every read-only lookup table, string, and large constant in Flash with `PROGMEM`, give every array and buffer a
declared bound, and profile SRAM usage before each release.

---

### Every loop has an upper bound

No `while` or `for` may run indefinitely, including under a hardware fault or a disconnected peripheral. Add a
hardware watchdog on anything safety-critical and reset it from the main loop, so a hung path recovers.

Pass:

```c
for (uint8_t attempt = 0U; attempt < MAX_ATTEMPTS; attempt++) {
  if (sensor_ready()) { break; }
  wdt_reset();
}
```

Fail:

```c
while (!sensor_ready()) { }
```

No `goto`, no `setjmp` or `longjmp`, and no direct or indirect recursion (MISRA C:2012 Required rules 15.2 and
17.2). Recursion has no bounded stack cost you can compute at review time.

---

### Non-blocking timing, not delay()

`delay()` stops the whole program. Every periodic or timed behaviour is a state machine driven by `millis()` or a
hardware timer, so the main loop keeps servicing everything else.

Pass:

```c
typedef enum {
  LAMP_IDLE,
  LAMP_ON,
  LAMP_COOLDOWN
} lamp_state_t;

#define LAMP_ON_MS        5000U
#define LAMP_COOLDOWN_MS  1000U

static lamp_state_t lamp_state    = LAMP_IDLE;
static uint32_t     lamp_since_ms = 0U;

void lamp_task(uint32_t now_ms, bool motion) {
  switch (lamp_state) {
    case LAMP_IDLE:
      if (motion) {
        hal_gpio_write(PIN_LAMP, 1U);
        lamp_since_ms = now_ms;
        lamp_state = LAMP_ON;
      }
      break;

    case LAMP_ON:
      if ((uint32_t)(now_ms - lamp_since_ms) >= LAMP_ON_MS) {
        hal_gpio_write(PIN_LAMP, 0U);
        lamp_since_ms = now_ms;
        lamp_state = LAMP_COOLDOWN;
      }
      break;

    case LAMP_COOLDOWN:
      if ((uint32_t)(now_ms - lamp_since_ms) >= LAMP_COOLDOWN_MS) {
        lamp_state = LAMP_IDLE;
      }
      break;

    default:
      lamp_state = LAMP_IDLE;
      break;
  }
}
```

Fail:

```c
void lamp_task(bool motion) {
  if (motion) {
    digitalWrite(PIN_LAMP, HIGH);
    delay(5000);
    digitalWrite(PIN_LAMP, LOW);
  }
}
```

Compare elapsed time as `now - since >= interval`, never `now >= since + interval`. The subtraction form is correct
across the `millis()` rollover at about 49.7 days, the addition form overflows and stalls the state machine there.
`lamp_task` takes `now_ms` as a parameter rather than calling `millis()` itself, which is what makes it testable on
the host with a synthetic clock.

---

### ISRs set a flag and return

An interrupt handler does the minimum: record what happened, set a `volatile` flag, return. Everything else is the
main loop's job. Blocking calls, `Serial.print`, and allocation inside an ISR either deadlock or corrupt state,
because the code they call is not reentrant.

Pass, the ISR:

```c
static volatile bool     pulse_pending = false;
static volatile uint32_t pulse_count   = 0U;

ISR(INT0_vect) {
  pulse_count++;
  pulse_pending = true;
}
```

And the main loop, reading the shared state inside the shortest possible critical section:

```c
void loop(void) {
  bool     pending;
  uint32_t count;

  noInterrupts();
  pending       = pulse_pending;
  count         = pulse_count;
  pulse_pending = false;
  interrupts();

  if (pending) {
    report_pulses(count);
  }
}
```

Fail:

```c
ISR(INT0_vect) {
  pulse_count++;
  Serial.print("pulse ");
  Serial.println(pulse_count);
  delay(10);
}
```

Every variable shared between an ISR and the main loop is `volatile`, or the compiler caches it in a register and
the main loop never sees the change. `pulse_count` is 32-bit, so an 8-bit core reads it in four instructions and an
interrupt landing between them yields a torn value: that is why the copy sits inside `noInterrupts()` /
`interrupts()`, and why that section contains nothing but the copy.

---

### Fixed-width integer types

Use `<stdint.h>` types for every register-level and protocol value. Bare `int`, `long`, and `short` change size
between an AVR build and an ESP32 build, so the same struct describes two different frame layouts.

Pass:

```c
uint16_t adc_raw = hal_adc_read(ADC_CHANNEL_2);
```

Fail:

```c
int adc_raw = analogRead(A2);
```

Use `size_t` for buffer lengths and for indices into arrays.

---

### Doc Comments

Default to none. A Doxygen block is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named function, rename the parameters so they carry their own meaning, and tighten the
types. Do that first and most Doxygen blocks have nothing left to say, which is the outcome you want. Code that
explains itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@brief` and `@param` and `@return` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in. On a constrained target the
header is often the only contract a caller reads, which raises the bar for the prose, not the line count.

1. Prose. One `@brief` line saying what it does, then only what a caller cannot infer from the signature. Nothing
   more.
2. `@param` only when the name and the type do not already convey it, meaning units, a valid range, whether a pointer
   may be null, and who owns the buffer afterwards. Always mark the direction, `@param[in]` or `@param[out]`, because
   a bare pointer type does not say it.
3. `@return` only when it is non-obvious. Naming the status codes a caller can branch on counts as non-obvious.
4. Document every error path always, every status code or errno a caller can act on. C has no exceptions and the
   return type alone rarely names them, so this one is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

Pass, one line of brief, then only what the signature cannot say:

```c
/**
 * @brief Reads one temperature sample from the sensor.
 * @param[out] out_celsius Written only when the call returns SENSOR_OK.
 * @return SENSOR_TIMEOUT when the bus does not answer within 50 ms.
 */
sensor_status_t sensor_read(sensor_handle_t *handle, float *out_celsius);
```

Fail, every tag restates the signature:

```c
/**
 * @brief Reads the sensor.
 * @param handle The handle.
 * @param out_celsius The output.
 * @return The status.
 */
sensor_status_t sensor_read(sensor_handle_t *handle, float *out_celsius);
```

---

### Hardware abstraction layer

Separate register access from logic behind a HAL: `hal_gpio_write`, `hal_gpio_read`, `hal_uart_send`,
`hal_uart_recv`, `hal_spi_transfer`. Implement each peripheral in its own translation unit, `hal_gpio_avr.c`,
`hal_uart_avr.c`. That boundary is what lets the business logic compile and run on a host machine with no hardware
attached, which is the entire basis of the testing rule below.

Pass:

```c
hal_gpio_write(PIN_LAMP, 1U);
```

Fail:

```c
PORTB |= _BV(PB5);
```

---

### Host-side unit tests

Write tests with Unity, generate mocks with CMock, orchestrate with Ceedling, and run all of it on the host for a
fast loop with no flashing. Mock every HAL function, mirror `src/` under `test/`, and target at least 80 percent
branch coverage on business-logic modules. Setup and coverage detail is in
[references/style-and-testing.md](references/style-and-testing.md).

Pass:

```bash
ceedling test:all
```

Fail:

```bash
arduino-cli upload --fqbn arduino:avr:uno --port COM3
```

---

### Reference files

| Open this | For |
|---|---|
| [references/rtos-ota-and-protocols.md](references/rtos-ota-and-protocols.md) | Sleep modes and power gating, FreeRTOS task and ISR rules, serial protocol versioning, and dual-bank OTA with rollback |
| [references/style-and-testing.md](references/style-and-testing.md) | MISRA and formatting rules, Arduino library API conventions, and the Ceedling, Unity and CMock host test setup |

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
- [ ] Multi-byte shared variables read inside the shortest possible `noInterrupts()` section.
- [ ] Every register and protocol value uses a `<stdint.h>` type.
- [ ] MISRA C:2012 Required rules met, deviations documented.
- [ ] All register access sits behind the HAL.
- [ ] Ceedling suite passes on the host, at least 80 percent branch coverage on logic modules.
