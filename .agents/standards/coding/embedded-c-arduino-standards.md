### AI Arduino and Embedded C Development Standards

---

### Core Execution Directives

- Treat all LLM generated C/C++ code, register manipulations, and memory operations as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every hardware-level task.
- Append a Zero-Trust directive demanding mandatory web searches for target MCU datasheets, register maps, and Arduino core library updates.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official MCU datasheets or Arduino documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every memory address, register configuration, and pin assignment provided.
- Mandate direct, working links to the official datasheets or Arduino documentation used to ground the code.

---

### Memory Management and Safety

- Prohibit the use of dynamic memory allocation functions like malloc, calloc, realloc, and free to prevent heap fragmentation. [Confidence: 100%]
- Prohibit the use of the C++ String class on AVR microcontrollers due to severe memory fragmentation risks. Mandate the use of statically allocated char arrays (C-strings) instead. [Confidence: 100%]
- Declare all read-only lookup tables, arrays, and large constants with the PROGMEM keyword to force storage in Flash memory instead of SRAM. [Confidence: 100%]
- Strictly define memory bounds for all arrays and buffers to prevent buffer overflow vulnerabilities. [Confidence: 100%]

---

### Control Flow and Infinite Loop Prevention

- Give all loops a fixed upper bound. The code must guarantee that no while or for loop can execute indefinitely, even under hardware failure conditions or disconnected peripherals. [Confidence: 100%]
- Implement hardware watchdog timers (WDT) on all safety-critical projects. The main loop must reset the watchdog timer periodically to recover from hard faults. [Confidence: 100%]
- Do not use goto statements, setjmp/longjmp constructs, or direct/indirect recursion, conforming to MISRA C and safety-critical rules. [Confidence: 100%]
  - Link: https://en.wikipedia.org/wiki/MISRA_C
  - Quote: "set"
- Avoid blocking functions like delay(). Implement non-blocking state machines using millis() or hardware timers for time-based operations. [Confidence: 100%]

---

### Hardware Interfacing and Interrupts

- Restrict Interrupt Service Routines (ISRs) to the absolute minimum required logic. Set volatile flags inside the ISR and defer complex processing to the main loop. [Confidence: 100%]
- Declare variables shared between ISRs and the main loop with the volatile keyword to prevent compiler over-optimization. [Confidence: 100%]
- Disable interrupts globally (noInterrupts() or cli()) only for the shortest possible duration when reading or writing multi-byte volatile variables, then immediately re-enable them. [Confidence: 100%]

---

### Arduino Style and API Design

- Structure public API functions around the data and functionality the end user expects, abstracting low-level register manipulation. [Confidence: 100%]
- Use the established core libraries and styles, such as read() for inputs and write() for outputs. [Confidence: 100%]
- Do not assume end-user knowledge of pointers. Avoid requiring the user to pass variables by reference using pointer notation; use array notation or wrap complex structures securely. [Confidence: 100%]
  - Link: https://docs.arduino.cc/learn/contributions/arduino-library-style-guide/
  - Quote: "guide"

---

### Security and Defensive Programming

- Validate all inputs, especially from external interfaces like UART, I2C, and SPI. [Confidence: 100%]
- Implement timeouts for all synchronous serial communication reads to prevent the microcontroller from hanging if a peripheral device disconnects or shorts. [Confidence: 100%]
- Enforce the use of hardware-specific types (e.g., uint8_t, uint32_t) from <stdint.h> instead of standard int or long to guarantee precise byte sizes across different MCU architectures. [Confidence: 100%]

---

### Coding Style

- Follow **MISRA C:2012** as the target rule set. Treat all "Required" rules as mandatory and "Advisory" rules as defaults unless explicitly deviated from with a documented justification. [Confidence: 100%]
  - Link: https://misra.org.uk/misra-c/
- Use K&R (Kernighan & Ritchie) brace style with 2-space indentation for all C/C++ source files.
- Limit function length to a maximum of 50 executable lines; extract longer functions into named sub-functions.
- Add a file header block to every `.c` and `.h` file: description, author, date, target hardware, and licence.

---

### Hardware Abstraction Layer (HAL)

- Separate hardware register access from business logic using a HAL layer. [Confidence: 100%]
- Define a HAL interface as a set of function pointers or abstract C functions (e.g., `hal_gpio_write`, `hal_uart_read`).
- Implement hardware-specific HAL functions in a separate translation unit per peripheral (e.g., `hal_gpio_avr.c`).
- This separation allows business logic to be unit-tested on a host machine (x86) without physical hardware.

---

### Unit Testing for Embedded

- Write unit tests using the **Unity** test framework + **CMock** for mock generation, orchestrated by **Ceedling**. [Confidence: 100%]
  - Link: http://www.throwtheswitch.org/ceedling
- Compile and run tests on the host machine (x86/x64) to enable fast iteration without flashing hardware.
- Mock all HAL functions in unit tests; test business logic independently of hardware.
- Target a minimum of 80% branch coverage for all business-logic modules.

---

### Power Management

- Use the MCU's sleep modes (SLEEP_MODE_PWR_DOWN, SLEEP_MODE_IDLE) in battery-powered applications to extend battery life. [Confidence: 100%]
- Enter sleep mode in the main loop idle state; wake via interrupt (timer, external pin, UART).
- Power-gate unused peripherals (ADC, UART, SPI) via the Power Reduction Register (PRR) before entering sleep.
- Document the expected current consumption in each sleep mode in the project's hardware notes.

---

### RTOS (FreeRTOS)

- When using FreeRTOS on Arduino-compatible hardware (e.g., via `FreeRTOS` AVR library or ESP-IDF), follow these rules:
  - Assign explicit task priorities; document the priority rationale (higher priority = more time-critical). [Confidence: 100%]
  - Calculate and explicitly specify task stack sizes using `uxTaskGetStackHighWaterMark` profiling; never use arbitrary large values. [Confidence: 100%]
  - Use **mutexes** for shared resource protection (not raw disabling of interrupts from task context). [Confidence: 100%]
  - Use **binary semaphores** for ISR-to-task synchronisation; never call FreeRTOS blocking APIs from within an ISR. [Confidence: 100%]

---

### Communication Protocol Versioning

- Begin every serial protocol frame with a magic byte sequence and a 1-byte protocol version field. [Confidence: 100%]
- Reject frames with unknown version numbers gracefully; log the received version and return a NACK.
- Document the protocol frame format (fields, sizes, byte order) in `docs/PROTOCOL.md`.

---

### OTA (Over-The-Air) Update Safety

- For platforms supporting OTA (ESP32, ESP8266, Arduino Nano 33 IoT), use a **dual-bank flash** scheme: one bank active, one receiving the update. [Confidence: 100%]
- Verify the downloaded firmware image checksum (CRC32 or SHA-256) before committing the update and rebooting.
- Implement an automatic rollback: if the new firmware fails to produce a healthy watchdog reset within N seconds, revert to the previous bank.