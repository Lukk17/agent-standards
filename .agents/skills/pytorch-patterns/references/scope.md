# Scope

Companion reference for the [pytorch-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing a model, a training loop, or a data pipeline.
- The user says "write a training loop", "build this nn.Module", "my GPU is starved", "add mixed precision", or "scale this to several GPUs".
- Debugging a training run that will not reproduce, will not converge, or runs out of memory.
- Speeding up training that is starved on data loading or is not using the GPU well.
- Adding checkpointing, resumption, or evaluation to an existing script.
- Scaling a single-GPU script to several GPUs or several nodes.

---

### When not to activate

- Writing general-purpose Python. Use `python-patterns`.
- Writing pytest tests around the training code. Use `python-patterns`.
- Profiling a web service or a database query. Use `performance-optimization`.
- Structuring the logs and metrics a training run emits. Use `observability-and-logging`.
- Packaging the training image or pinning CUDA in a container. Use `docker-patterns`.

---

### Related skills

- `python-patterns` for the Python the training script is written in, and for the pytest suite around data pipelines, shapes, and training steps.
- `performance-optimization` for the measure-first discipline this skill applies to GPUs.
- `observability-and-logging` for metrics and structured logs from a run.
- `docker-patterns` for packaging the training environment and its CUDA stack.
