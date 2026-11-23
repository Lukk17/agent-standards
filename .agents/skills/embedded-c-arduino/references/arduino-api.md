# Arduino Library API

The conventions for the public API of an Arduino library. The memory, timing, and interrupt rules live in [SKILL.md](../SKILL.md).

---

### Arduino API design

Shape a public API around what the user of the library wants to do, not around the registers underneath. Follow the established naming: `begin()` to initialise, `read()` for input, `write()` for output. Do not make the caller pass a raw buffer pointer and a separate length, take a bounded array or wrap the data in a struct. A pointer to a handle or to a single output value is fine. Validate everything arriving from UART, I2C, or SPI, and put a timeout on every synchronous read so a disconnected peripheral cannot hang the device.

Pass:

```c
sensor_status_t sensor_read_timeout(sensor_handle_t *handle, float *out_celsius, uint16_t timeout_ms);
```

Fail:

```c
float readSensor(void) { while (!(TWCR & _BV(TWINT))) { } return decode(TWDR); }
```
