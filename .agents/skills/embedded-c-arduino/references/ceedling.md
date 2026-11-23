# Ceedling, Unity and CMock

The Ceedling setup that runs firmware logic on a development machine, with Unity for the tests and CMock for the mocks. The hardware abstraction layer that makes it possible is in [core-rules-and-examples.md](core-rules-and-examples.md#hardware-abstraction-layer).

---

### Host-side unit tests

Write tests with Unity, generate mocks with CMock, orchestrate with Ceedling, and run all of it on the host for a fast loop with no flashing. Mock every HAL function so logic is tested independently of hardware. Target at least 80 percent branch coverage on business-logic modules, and mirror `src/` under `test/`, one test file per module.

Pass:

```bash
ceedling test:all
```

Fail:

```bash
arduino-cli upload --fqbn arduino:avr:uno --port COM3
```

- Reference: http://www.throwtheswitch.org/ceedling
