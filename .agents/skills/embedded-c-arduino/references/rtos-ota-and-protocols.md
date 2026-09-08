# RTOS, power management, protocols, and OTA

The subsystems that only apply to some targets. The rules that apply to every firmware build live in
[SKILL.md](../SKILL.md).

---

### Power management and sleep modes

On a battery-powered target, sleeping is the design, not an optimisation added later.

- `SLEEP_MODE_PWR_DOWN` for the deepest sleep, woken only by an external interrupt.
- `SLEEP_MODE_IDLE` for light sleep, woken by any interrupt including a timer.

Enter sleep from the main loop's idle state and wake on an interrupt: a hardware timer, an external pin, or UART RX.
Power-gate every unused peripheral (ADC, UART, SPI, TWI) through the Power Reduction Register (`PRR`, `PRR0`,
`PRR1`) before sleeping, because a clocked-but-unused peripheral costs current for nothing.

Document the expected current in each sleep mode in the project's hardware notes, so a later regression in battery
life has a number to be measured against.

---

### FreeRTOS rules

When using FreeRTOS on Arduino-compatible hardware (the AVR FreeRTOS library, ESP-IDF, or similar):

- Assign explicit task priorities and record the rationale. A higher value is more time-critical.
- Size every task stack from `uxTaskGetStackHighWaterMark()` profiling. An arbitrary large value hides an overflow
  until the day the call depth changes.
- Use a mutex (`xSemaphoreCreateMutex`) to protect a shared resource from task context. Never disable interrupts
  from a task to do it.
- Use a binary semaphore (`xSemaphoreCreateBinary`) for ISR-to-task synchronisation. Never call a blocking FreeRTOS
  API such as `xSemaphoreTake` or `vTaskDelay` from inside an ISR.
- Use the `FromISR` variants for all ISR-to-task communication, `xSemaphoreGiveFromISR` and `xQueueSendFromISR`, and
  always pass and then act on `pxHigherPriorityTaskWoken`. Dropping it means the woken high-priority task waits for
  the next tick instead of running immediately, which silently destroys the latency the priority was chosen for.

---

### Communication protocol versioning

Every serial frame starts with a magic byte sequence and a one-byte protocol version.

```c
#define FRAME_MAGIC_0    0xAAU
#define FRAME_MAGIC_1    0x55U
#define FRAME_VERSION    0x03U
```

Reject an unknown version gracefully: record the received value and return a NACK byte. Never process a frame whose
version you do not recognise, because the field layout behind it is unknown by definition.

Document the complete frame format, every field, its size, the byte order, and the CRC algorithm, in
`docs/PROTOCOL.md`, and increment the version field on any breaking change to that structure.

---

### OTA update safety

On a platform that supports it (ESP32, ESP8266, Arduino Nano 33 IoT), use a dual-bank flash scheme: one bank active,
one receiving the incoming image.

- Verify the downloaded image's checksum, CRC32 or SHA-256, before committing the update and rebooting.
- Implement automatic rollback: if the new firmware does not produce a healthy watchdog reset within N seconds of
  its first boot, revert to the previous bank without human involvement.
- Log every attempt, checksum result, and rollback to non-volatile storage (EEPROM or NVS). A device that bricked in
  the field is only diagnosable from what it wrote down before it did.
