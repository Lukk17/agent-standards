---
name: pytorch-patterns
description: 'PyTorch 2 patterns: devices, seeding, training loops, data loading, checkpoints, AMP and DDP. Use when the user says "write a training loop" or "my GPU is starved". Not for plain Python, use `python-patterns`.'
metadata:
  version: "1.1.0"
---

# PyTorch Development Patterns

Rules for PyTorch code that runs the same way twice, survives a restart, and uses the hardware it was given. The long-form training, data, performance, and distributed material lives in the reference files listed below.

Written for PyTorch 2 on Python 3.14. The examples use `torch.amp`, `torch.compile`, and `weights_only=True` without a compatibility note.

---

### When not to activate

- Writing general-purpose Python, or pytest tests around the training code, use `python-patterns`.
- Structuring the logs and metrics a training run emits, use `observability-and-logging`.
- Packaging the training image or pinning CUDA in a container, use `docker-patterns`.

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
| [core-rules.md](references/core-rules.md) | A rule above needs its Pass and Fail example, its full reasoning or the trap table. |
| [training-loop.md](references/training-loop.md) | Full train and validate loops, schedulers, checkpoint and resume. |
| [data-pipeline.md](references/data-pipeline.md) | Dataset design, collate functions, sampling, worker seeding. |
| [performance.md](references/performance.md) | AMP, gradient checkpointing, `torch.compile`, profiling, memory. |
| [distributed.md](references/distributed.md) | DDP, `torchrun`, samplers, rank-aware logging, FSDP. |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job. |
| [checklist.md](references/checklist.md) | Before calling a model, a training loop or a data pipeline done. |
