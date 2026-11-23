# FreeRTOS

The rules for firmware that runs FreeRTOS. The rules that apply to every firmware build live in [SKILL.md](../SKILL.md).

---

### FreeRTOS rules

When using FreeRTOS on Arduino-compatible hardware (the AVR FreeRTOS library, ESP-IDF, or similar):

- Assign explicit task priorities and record the rationale. A higher value is more time-critical.
- Size every task stack from `uxTaskGetStackHighWaterMark()` profiling. An arbitrary large value hides an overflow until the day the call depth changes.
- Use a mutex (`xSemaphoreCreateMutex`) to protect a shared resource from task context. Never disable interrupts from a task to do it.
- Use a binary semaphore (`xSemaphoreCreateBinary`) for ISR-to-task synchronisation. Never call a blocking FreeRTOS API such as `xSemaphoreTake` or `vTaskDelay` from inside an ISR.
- Use the `FromISR` variants for all ISR-to-task communication, `xSemaphoreGiveFromISR` and `xQueueSendFromISR`, and always pass and then act on `pxHigherPriorityTaskWoken`. Dropping it means the woken high-priority task waits for the next tick instead of running immediately, which silently destroys the latency the priority was chosen for.
