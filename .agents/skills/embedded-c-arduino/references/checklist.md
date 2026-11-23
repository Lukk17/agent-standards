# Embedded C and Arduino Checklist

Run it before calling a firmware change or a firmware review done.

- [ ] No `malloc`, `free`, or C++ `String` anywhere in the build.
- [ ] Every lookup table and constant string in `PROGMEM`, every buffer bounded.
- [ ] SRAM usage profiled before the release.
- [ ] Every loop bounded, watchdog reset from the main loop on safety-critical builds.
- [ ] No `goto`, `setjmp`, `longjmp`, or recursion.
- [ ] No `delay()`, timing done by a `millis()` state machine using subtraction for elapsed time.
- [ ] Every ISR sets a `volatile` flag and returns, no printing, blocking, or allocation.
- [ ] Multi-byte shared variables read inside the shortest possible `noInterrupts()` section, or a spinlock critical section on ESP32.
- [ ] Every register and protocol value uses a `<stdint.h>` type.
- [ ] MISRA C:2012 Required rules met, deviations documented.
- [ ] All register access sits behind the HAL.
- [ ] Ceedling suite passes on the host, at least 80 percent branch coverage on logic modules.
