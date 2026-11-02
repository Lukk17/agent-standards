---
name: pytorch-patterns
description: "PyTorch 2 patterns for reproducible deep learning, covering device-agnostic code, seeding, nn.Module structure, training and validation loops, DataLoader throughput, checkpointing, mixed precision, torch.compile and DDP. Use when the user says \"write a training loop\", \"my GPU is starved\" or \"scale this to several GPUs\". Not for general Python idioms and typing, use `python-patterns`."
---

# PyTorch Development Patterns

Rules for PyTorch code that runs the same way twice, survives a restart, and uses the hardware it was given. The long-form training, data, performance, and distributed material lives in the reference files listed near the bottom.

Written for PyTorch 2 on Python 3.14. The examples use `torch.amp`, `torch.compile`, and `weights_only=True` without a compatibility note.

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

### Rules

1. Resolve the device once and move every module and tensor to it. Never hardcode `.cuda()`.
2. Seed Python, NumPy and torch, seed DataLoader workers through `worker_init_fn` and a `generator`, and record whether deterministic cudnn was on.
3. Annotate the shape at each step of `forward`, and flatten with `flatten(start_dim=1)` rather than `view(x.size(0), -1)`.
4. Build every layer in `__init__`, never in `forward`, and initialise weights explicitly with `model.apply(...)`.
5. Call `model.eval()` and run under `@torch.no_grad()` to evaluate, then `model.train()` at the top of the next epoch.
6. Zero with `zero_grad(set_to_none=True)`, and clip after `backward` and before `step`, after `scaler.unscale_` under mixed precision.
7. Checkpoint model, optimizer, scheduler, scaler and epoch as state dicts, never the module object, and load with `weights_only=True` spelled out.
8. Feed the GPU: set `num_workers` from the machine, `pin_memory` with `non_blocking=True` transfers, `persistent_workers` and `prefetch_factor`, and check utilisation before blaming the model.
9. Use `torch.amp.autocast` with a `GradScaler` and `torch.compile` before buying hardware, never a manual `.half()`, and gradient checkpointing with `use_reentrant=False`.
10. Scale out with DDP under `torchrun`, never `DataParallel`: call `sampler.set_epoch` every epoch, save `model.module`, and write only from rank 0. Use FSDP once the state no longer fits one GPU.
11. Keep in-place operations off tensors autograd needs, and accumulate `loss.detach()` rather than the loss.

---

### Reference files

| Open this | When |
| --- | --- |
| [references/core-rules.md](references/core-rules.md) | A hub rule needs its Pass and Fail example, its full reasoning, or the trap table |
| [references/training-loop.md](references/training-loop.md) | Full train and validate loops, schedulers, checkpoint and resume |
| [references/data-pipeline.md](references/data-pipeline.md) | Dataset design, collate functions, sampling, worker seeding |
| [references/performance.md](references/performance.md) | AMP, gradient checkpointing, `torch.compile`, profiling, memory |
| [references/distributed.md](references/distributed.md) | DDP, `torchrun`, samplers, rank-aware logging, FSDP |

---

### Related skills

- `python-patterns` for the Python the training script is written in, and for the pytest suite around data pipelines, shapes, and training steps.
- `performance-optimization` for the measure-first discipline this skill applies to GPUs.
- `observability-and-logging` for metrics and structured logs from a run.
- `docker-patterns` for packaging the training environment and its CUDA stack.

---

### Checklist

- The device is resolved once and every tensor and module moves to it.
- Every run seeds Python, NumPy, and torch, and records whether cudnn was deterministic.
- Shapes are annotated through `forward`, and flattening uses `flatten(start_dim=1)`.
- All layers are constructed in `__init__` and weights are initialised explicitly.
- `model.train()` and `model.eval()` are set, and evaluation runs under `@torch.no_grad()`.
- Gradients are zeroed with `set_to_none=True` and clipped between `backward` and `step`.
- Checkpoints hold model, optimizer, scheduler, scaler, and epoch, and load with `weights_only=True`.
- The DataLoader sets `num_workers`, `pin_memory`, and `persistent_workers`, and the GPU is not starved.
- Mixed precision uses `torch.amp.autocast` with a `GradScaler`, never a manual `.half()`.
- Gradient checkpointing passes `use_reentrant=False`.
- Multi-GPU runs use DDP under `torchrun`, call `sampler.set_epoch`, and write only from rank 0.
- No in-place operation sits on a tensor autograd still needs.
