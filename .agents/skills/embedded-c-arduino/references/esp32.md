# ESP32

What changes on a dual-core ESP32. The rules that hold on every target are in [SKILL.md](../SKILL.md), and the ISR pattern this file builds on is in [core-rules-and-examples.md](core-rules-and-examples.md#isrs-set-a-flag-and-return). The FreeRTOS rules are in [freertos.md](freertos.md), and the ESP-IDF call that confirms an OTA image is in [protocols-and-ota.md](protocols-and-ota.md#ota-update-safety).

---

### ISR shared state on two cores

`ISR(INT0_vect)` and `noInterrupts()` are the AVR form. On a dual-core ESP32, disabling interrupts masks only the calling core, so the other core can still touch the shared state. Attach the handler with `attachInterrupt`, place it in IRAM with `IRAM_ATTR`, and guard the shared state with a `portMUX_TYPE` spinlock, taking it with `taskENTER_CRITICAL_ISR` inside the handler and `taskENTER_CRITICAL` in the main loop.

```c
static portMUX_TYPE pulse_mux = portMUX_INITIALIZER_UNLOCKED;

void IRAM_ATTR on_pulse(void) {
  taskENTER_CRITICAL_ISR(&pulse_mux);
  pulse_count++;
  pulse_pending = true;
  taskEXIT_CRITICAL_ISR(&pulse_mux);
}
```

The main loop makes the same copy as the AVR main loop, of `pulse_pending` and `pulse_count` into locals, between `taskENTER_CRITICAL(&pulse_mux)` and `taskEXIT_CRITICAL(&pulse_mux)`.
