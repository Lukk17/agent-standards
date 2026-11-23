# Scope

Companion reference for the [embedded-c-arduino](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing `.c`, `.h`, or `.ino` firmware.
- Replacing `delay()` with non-blocking timing, or diagnosing a loop that misses events.
- Writing or reviewing an interrupt service routine.
- Chasing an SRAM exhaustion, a stack overflow, or a corrupted buffer.
- Introducing a hardware abstraction layer so logic can be tested off-target.
- Setting up Ceedling, Unity, or CMock for host-side unit tests.
- Adding a hardware watchdog to a sketch that can hang.
- The user says "replace this delay with a state machine", "write the ISR for this encoder" or "my sketch runs out of SRAM".

The skill covers heap-free memory, bounded loops and watchdogs, non-blocking millis state machines, flag-and-return ISRs, MISRA C:2012 rules, a hardware abstraction layer and host-side unit tests.

---

### When not to activate

- Designing the board the firmware runs on, use `kicad`.
- Slicing or printing an enclosure for it, use `g-code-3d-printing`.
- Writing the host-side tool that flashes or talks to the device, use `bash` or `powershell`.
- Building a service that ingests the device's telemetry, use `backend-patterns`.
- Automating the device from Home Assistant, use `home-assistant`.

---

### Related skills

- `kicad` for the board, its decoupling, and its connector pinout.
- `g-code-3d-printing` for the printed enclosure.
- `bash` and `powershell` for flashing, log capture, and CI scripts.
- `home-assistant` for integrating the finished device into a home system.
- `coding-standards` for the naming and control-flow floor this skill sits on top of.
