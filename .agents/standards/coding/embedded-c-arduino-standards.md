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