# Style, API design, and host-side testing

MISRA and formatting rules, Arduino library API conventions, and the Ceedling setup that runs firmware logic on a
development machine. The memory, timing, and interrupt rules live in [SKILL.md](../SKILL.md).

---

### Style, MISRA C:2012

Treat every Required rule as mandatory and every Advisory rule as a default that needs a documented justification to
deviate from. K&R braces, two-space indentation, `UPPER_SNAKE_CASE` for `#define`, `lower_snake_case` for functions.
Cap a function at 50 executable lines and extract beyond that. Every `.c` and `.h` carries a file header block with
description, author, date, target hardware, and licence.

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

---

### Arduino API design

Shape a public API around what the user of the library wants to do, not around the registers underneath. Follow the
established naming: `begin()` to initialise, `read()` for input, `write()` for output. Do not make the caller pass
raw pointers, take an array or wrap the structure. Validate everything arriving from UART, I2C, or SPI, and put a
timeout on every synchronous read so a disconnected peripheral cannot hang the device.

Pass:

```c
sensor_status_t sensor_read_timeout(sensor_handle_t *handle, float *out_celsius, uint16_t timeout_ms);
```

Fail:

```c
float readSensor(void) { while (!(TWCR & _BV(TWINT))) { } return decode(TWDR); }
```

---

### Host-side unit tests

Write tests with Unity, generate mocks with CMock, orchestrate with Ceedling, and run all of it on the host for a
fast loop with no flashing. Mock every HAL function so logic is tested independently of hardware. Target at least 80
percent branch coverage on business-logic modules, and mirror `src/` under `test/`, one test file per module.

Pass:

```bash
ceedling test:all
```

Fail:

```bash
arduino-cli upload --fqbn arduino:avr:uno --port COM3
```

- Reference: http://www.throwtheswitch.org/ceedling

---
