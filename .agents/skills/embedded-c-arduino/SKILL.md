---
name: embedded-c-arduino
description: Embedded C and Arduino standards for memory safety, non-blocking code, ISR discipline, hardware abstraction, and testing with Unity/CMock/Ceedling.
origin: project-standards
---

# Embedded C / Arduino Development Standards

## Memory Management and Safety

- Prohibit `malloc`, `calloc`, `realloc`, and `free`. Heap fragmentation on constrained MCUs causes unpredictable failures.
- Prohibit the C++ `String` class on AVR microcontrollers. Use statically allocated `char` arrays (C-strings) exclusively.
- Declare all read-only lookup tables, arrays, and large constants with the `PROGMEM` keyword to store them in Flash instead of SRAM.
- Define strict memory bounds for all arrays and buffers to prevent buffer overflows.
- Prefer fixed-size stack allocations; profile SRAM usage before each release.

## Control Flow and Infinite Loop Prevention

- Give every loop a fixed upper bound. No `while` or `for` loop may execute indefinitely, even under hardware failure or disconnected peripheral conditions.
- Implement hardware **watchdog timers (WDT)** on all safety-critical projects. The main loop must call `wdt_reset()` periodically to recover from hard faults.
- Do not use `goto`, `setjmp`/`longjmp`, or any form of direct or indirect recursion (MISRA C:2012 Required Rule 15.2, 17.2).
- Replace all blocking `delay()` calls with **non-blocking state machines** driven by `millis()` or hardware timers.

## Hardware Interfacing and Interrupts (ISR Discipline)

- Restrict ISR bodies to the **absolute minimum** logic: set a `volatile` flag and return. Defer all processing to the main loop.
- Declare every variable shared between an ISR and the main loop with the `volatile` keyword to prevent compiler over-optimisation.
- Disable interrupts (`noInterrupts()` / `cli()`) only for the shortest possible critical section when reading or writing multi-byte `volatile` variables, then re-enable immediately.
- Never call blocking functions, `Serial.print`, or dynamic allocations from inside an ISR.

## Hardware-Specific Integer Types

- Enforce the use of types from `<stdint.h>` (`uint8_t`, `int8_t`, `uint16_t`, `int16_t`, `uint32_t`, `int32_t`) for all register-level and protocol code.
- Never use bare `int`, `long`, or `short` for hardware-mapped values; their sizes are architecture-dependent.
- Use `size_t` for buffer lengths and loop indices over arrays.

## Coding Style — MISRA C:2012

- Follow **MISRA C:2012** as the target rule set. Treat all "Required" rules as mandatory; treat "Advisory" rules as defaults requiring documented justification to deviate.
- Use K&R brace style with **2-space indentation** for all `.c` and `.h` files.
- Limit function length to a maximum of **50 executable lines**; extract longer functions into named sub-functions.
- Add a file header block to every `.c` and `.h` file containing: description, author, date, target hardware, and licence.
- Name `#define` constants in `UPPER_SNAKE_CASE`; name functions in `lower_snake_case`.

## Arduino API Design

- Structure public API functions around the data and functionality the end user expects, abstracting low-level register manipulation.
- Follow established Arduino naming conventions: `read()` for inputs, `write()` for outputs, `begin()` for initialisation.
- Do not require the user to pass variables by pointer notation; use array notation or wrap complex structures securely.
- Validate all inputs from external interfaces (UART, I2C, SPI). Implement timeouts for all synchronous serial reads to prevent hanging when a peripheral disconnects.

## Hardware Abstraction Layer (HAL)

- Separate hardware register access from business logic using a HAL layer.
- Define the HAL interface as a set of function pointers or abstract C functions: `hal_gpio_write`, `hal_gpio_read`, `hal_uart_send`, `hal_uart_recv`, `hal_spi_transfer`, etc.
- Implement hardware-specific HAL functions in a separate translation unit per peripheral (e.g., `hal_gpio_avr.c`, `hal_uart_avr.c`).
- This separation allows business logic to be compiled and unit-tested on a host machine (x86/x64) without physical hardware.

## Unit Testing — Unity / CMock / Ceedling

- Write all unit tests using the **Unity** test framework, **CMock** for mock generation, and **Ceedling** as the build orchestrator.
  - Reference: http://www.throwtheswitch.org/ceedling
- Compile and run all tests on the host machine (x86/x64) for fast iteration without flashing hardware.
- Mock all HAL functions in unit tests; test business logic independently of hardware.
- Target a minimum of **80% branch coverage** for all business-logic modules.
- Organise tests under `test/` mirroring the `src/` directory structure; one test file per source module.

## Power Management — Sleep Modes

- Use the MCU's sleep modes in battery-powered applications:
  - `SLEEP_MODE_PWR_DOWN` for deepest sleep (wake via external interrupt only).
  - `SLEEP_MODE_IDLE` for light sleep (wake via any interrupt including timers).
- Enter sleep mode in the main loop's idle state; wake via interrupt (hardware timer, external pin, UART RX).
- Power-gate unused peripherals (ADC, UART, SPI, TWI) via the Power Reduction Register (`PRR` / `PRR0` / `PRR1`) before entering sleep.
- Document the expected current consumption in each sleep mode in the project's hardware notes.

## RTOS — FreeRTOS Rules

When using FreeRTOS on Arduino-compatible hardware (AVR FreeRTOS library, ESP-IDF, or similar):

- Assign **explicit task priorities** and document the priority rationale (higher value = more time-critical).
- Calculate and explicitly specify task stack sizes using `uxTaskGetStackHighWaterMark()` profiling; never use arbitrary large values.
- Use **mutexes** (`xSemaphoreCreateMutex`) for shared resource protection from task context; do not disable interrupts from tasks.
- Use **binary semaphores** (`xSemaphoreCreateBinary`) for ISR-to-task synchronisation; never call FreeRTOS blocking APIs (`xSemaphoreTake`, `vTaskDelay`, etc.) from within an ISR.
- Use `xSemaphoreGiveFromISR` / `xQueueSendFromISR` for all ISR-to-task communication; always pass and check `pxHigherPriorityTaskWoken`.

## Communication Protocol Versioning

- Begin every serial protocol frame with a **magic byte sequence** (e.g., `0xAA 0x55`) and a 1-byte **protocol version** field.
- Reject frames with unknown version numbers gracefully: log the received version and return a NACK byte; do not silently process corrupt data.
- Document the complete frame format (fields, sizes, byte order, CRC algorithm) in `docs/PROTOCOL.md`.
- Increment the version field on any breaking change to the frame structure.

## OTA (Over-The-Air) Update Safety

- For platforms supporting OTA (ESP32, ESP8266, Arduino Nano 33 IoT), use a **dual-bank flash** scheme: one bank active, one receiving the incoming image.
- Verify the downloaded firmware image checksum (**CRC32** or **SHA-256**) before committing the update and issuing a reboot.
- Implement **automatic rollback**: if the new firmware fails to produce a healthy watchdog reset within N seconds after first boot, revert to the previous bank automatically.
- Log OTA update attempts, checksum results, and rollback events to non-volatile storage (EEPROM / NVS) for post-mortem analysis.
