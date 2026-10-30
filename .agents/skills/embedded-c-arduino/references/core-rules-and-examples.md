# Core firmware rules with examples

Open this for the Pass and Fail code behind any rule in [SKILL.md](../SKILL.md): the full millis state machine, the AVR and ESP32 ISR patterns, and the reasoning behind each rule.

---

### Contents

- [No heap, ever](#no-heap-ever)
- [Every loop has an upper bound](#every-loop-has-an-upper-bound)
- [Non-blocking timing, not delay()](#non-blocking-timing-not-delay)
- [ISRs set a flag and return](#isrs-set-a-flag-and-return)
- [Fixed-width integer types](#fixed-width-integer-types)
- [Doc Comments](#doc-comments)
- [Hardware abstraction layer](#hardware-abstraction-layer)
- [Host-side unit tests](#host-side-unit-tests)

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

No `goto` (MISRA C:2012 Rule 15.1, Advisory, adopted here as mandatory), no `setjmp` or `longjmp` (Rule 21.4,
Required, which bans `<setjmp.h>`), and no direct or indirect recursion (Rule 17.2, Required). Recursion has no bounded
stack cost you can compute at review time.

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

`ISR(INT0_vect)` and `noInterrupts()` are the AVR form. On a dual-core ESP32, disabling interrupts masks only the
calling core, so the other core can still touch the shared state. Attach the handler with `attachInterrupt`, place it
in IRAM with `IRAM_ATTR`, and guard the shared state with a `portMUX_TYPE` spinlock, taking it with
`taskENTER_CRITICAL_ISR` inside the handler and `taskENTER_CRITICAL` in the main loop.

```c
static portMUX_TYPE pulse_mux = portMUX_INITIALIZER_UNLOCKED;

void IRAM_ATTR on_pulse(void) {
  taskENTER_CRITICAL_ISR(&pulse_mux);
  pulse_count++;
  pulse_pending = true;
  taskEXIT_CRITICAL_ISR(&pulse_mux);
}
```

The main loop makes the same copy as above between `taskENTER_CRITICAL(&pulse_mux)` and
`taskEXIT_CRITICAL(&pulse_mux)`.

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

Doxygen blocks follow "Doc Comments" in `coding-standards`. The C delta: write the prose as one `@brief` line, mark
every pointer `@param[in]` or `@param[out]` because a bare pointer type does not say which, say whether it may be null
and who owns the buffer afterwards, and name every status code or errno a caller can branch on, since C has no
exceptions and the return type rarely names them.

```c
/**
 * @brief Reads one temperature sample from the sensor.
 * @param[out] out_celsius Written only when the call returns SENSOR_OK.
 * @return SENSOR_TIMEOUT when the bus does not answer within 50 ms.
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
[references/style-and-testing.md](style-and-testing.md).

Pass:

```bash
ceedling test:all
```

Fail:

```bash
arduino-cli upload --fqbn arduino:avr:uno --port COM3
```
