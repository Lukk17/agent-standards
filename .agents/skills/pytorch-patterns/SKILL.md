---
name: pytorch-patterns
description: PyTorch patterns for reproducible deep learning, covering device-agnostic code, seeding, nn.Module structure, training and validation loops, DataLoader throughput, checkpointing, mixed precision, torch.compile, and distributed training with DDP. Use when writing a training loop, building an nn.Module, speeding up a starved DataLoader, adding mixed precision, or scaling training across several GPUs. Not for general Python idioms and typing, use `python-patterns`.
---

# PyTorch Development Patterns

Rules for PyTorch code that runs the same way twice, survives a restart, and uses the hardware it was given. The
long-form training, data, performance, and distributed material lives in the reference files listed near the bottom.

Baseline: the current stable PyTorch release, the 2.x line, on Python 3.13 or newer. The examples use `torch.amp`,
`torch.compile`, and `weights_only=True` without a compatibility note.

---

### When to activate

- Writing or reviewing a model, a training loop, or a data pipeline.
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

### Write device-agnostic code

Resolve the device once and move everything to it. A hardcoded `.cuda()` crashes on a laptop and on a CPU-only CI
runner, which is where the tests run.

Pass:

```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = MyModel().to(device)
```

Fail:

```python
model = MyModel().cuda()
```

---

### Seed everything, and say so

Without a seed a failed run cannot be reproduced and a successful one cannot be trusted. Deterministic cudnn costs
throughput, so turn it on while you are chasing a bug and record in the run's config whether it was on.

Pass:

```python
def set_seed(seed: int = 42, deterministic: bool = False) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = deterministic
    torch.backends.cudnn.benchmark = not deterministic
```

Fail:

```python
model = MyModel()
```

Seed the DataLoader workers too, through `worker_init_fn` and a `generator`, or shuffling and augmentation stay
random regardless of the global seed.

---

### Track the shape at every step

Shapes are the type system PyTorch does not have. Annotate the transitions in `forward` so a mismatch is caught by
reading rather than by a stack trace four layers down.

Pass:

```python
def forward(self, x: torch.Tensor) -> torch.Tensor:
    x = self.features(x)            # (B, 64, H//2, W//2)
    x = x.flatten(start_dim=1)      # (B, 64 * H//2 * W//2)
    return self.classifier(x)       # (B, num_classes)
```

Fail:

```python
def forward(self, x):
    x = self.features(x)
    x = x.view(x.size(0), -1)
    return self.classifier(x)
```

Prefer `flatten(start_dim=1)` to `view(x.size(0), -1)`: it does the same thing and does not fail on a non-contiguous
tensor.

---

### Build layers in `__init__`, never in `forward`

A layer created inside `forward` gets fresh weights on every call, is invisible to the optimizer, and is not saved in
the state dict. The model appears to train and learns nothing.

Pass:

```python
class ImageClassifier(nn.Module):
    def __init__(self, num_classes: int, dropout: float = 0.5) -> None:
        super().__init__()
        self.features = nn.Sequential(nn.Conv2d(3, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2))
        self.classifier = nn.Sequential(nn.Dropout(dropout), nn.Linear(64 * 16 * 16, num_classes))
```

Fail:

```python
def forward(self, x):
    return F.conv2d(x, weight=self.make_weight())
```

Initialise weights explicitly with `model.apply(...)` rather than trusting the defaults, which differ between layer
types and change between releases.

---

### Set the mode, and turn gradients off for evaluation

`model.train()` and `model.eval()` change what dropout and batch norm do. Forgetting `eval()` gives validation
numbers that are quietly wrong rather than an error.

Pass:

```python
@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = sum((model(x.to(device)).argmax(1) == y.to(device)).sum().item() for x, y in loader)
    return correct / len(loader.dataset)
```

Fail:

```python
def evaluate(model, loader, device):
    with torch.no_grad():
        return sum((model(x.to(device)).argmax(1) == y.to(device)).sum().item() for x, y in loader)
```

Set `model.train()` back at the top of the next training epoch. The full loop is in
[references/training-loop.md](references/training-loop.md).

---

### Zero with `set_to_none`, clip before you step

`zero_grad(set_to_none=True)` frees the gradient buffers instead of filling them with zeros. Gradient clipping goes
after `backward` and before `step`, and after `scaler.unscale_` when mixed precision is on.

Pass:

```python
optimizer.zero_grad(set_to_none=True)
loss.backward()
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
optimizer.step()
```

Fail:

```python
loss.backward()
optimizer.step()
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
optimizer.zero_grad()
```

---

### Checkpoint the whole training state

A file holding only the weights cannot resume a run: the optimizer momentum, the scheduler position, the AMP scaler,
and the epoch are all gone. Load with `weights_only=True`, because `torch.load` otherwise unpickles arbitrary code.

Pass:

```python
state = {
    "epoch": epoch,
    "model_state_dict": model.state_dict(),
    "optimizer_state_dict": optimizer.state_dict(),
    "scheduler_state_dict": scheduler.state_dict(),
    "scaler_state_dict": scaler.state_dict(),
}
torch.save(state, path)
```

Fail:

```python
torch.save(model, "model.pt")
```

Saving the module object pickles the class definition, so the file stops loading the moment the code is refactored.

---

### Keep the GPU fed

A DataLoader on its defaults loads in the training process with no prefetch, so the GPU waits on the CPU. Set the
worker count from the machine, not from a copied number, and check GPU utilisation before blaming the model.

Pass:

```python
loader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=8,
                    pin_memory=True, persistent_workers=True, prefetch_factor=4)
```

Fail:

```python
loader = DataLoader(dataset, batch_size=32)
```

`pin_memory=True` pays off only with `non_blocking=True` on the transfer. Dataset, collate, and variable-length
batching are in [references/data-pipeline.md](references/data-pipeline.md).

---

### Reach for mixed precision and compilation before more hardware

Autocast with a `GradScaler` typically halves memory and raises throughput on a tensor-core GPU for a few lines of
change. `torch.compile` adds a one-off warmup and then removes Python overhead from the step.

Pass:

```python
scaler = torch.amp.GradScaler("cuda")
model = torch.compile(model)

with torch.amp.autocast("cuda"):
    loss = criterion(model(data), target)
scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

Fail:

```python
model = model.half()
loss = criterion(model(data), target)
loss.backward()
```

Casting the whole model to fp16 by hand underflows the gradients, which is exactly what the scaler exists to prevent.
Gradient checkpointing, which trades compute for memory and must be called with `use_reentrant=False`, is in
[references/performance.md](references/performance.md).

---

### Scale out with DDP under torchrun

`DistributedDataParallel` runs one process per GPU and is the default for multi-GPU training. `DataParallel` is
single-process, imbalanced, and deprecated in practice: do not start with it.

Pass:

```python
def main() -> None:
    dist.init_process_group(backend="nccl")
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)

    model = DistributedDataParallel(MyModel().to(local_rank), device_ids=[local_rank])
    sampler = DistributedSampler(dataset, shuffle=True)
    loader = DataLoader(dataset, batch_size=32, sampler=sampler, num_workers=8, pin_memory=True)

    for epoch in range(epochs):
        sampler.set_epoch(epoch)
        train_one_epoch(model, loader, optimizer, criterion, torch.device(local_rank))
        if dist.get_rank() == 0:
            save_checkpoint(model.module, optimizer, epoch, path)

    dist.destroy_process_group()
```

Launch it with `torchrun`, which sets `RANK`, `LOCAL_RANK`, and `WORLD_SIZE` for every process:

```bash
torchrun --standalone --nproc_per_node=4 train.py
```

Fail:

```python
model = nn.DataParallel(MyModel()).cuda()
```

Three details are not optional: `sampler.set_epoch(epoch)` every epoch or every rank sees the same order forever,
`model.module` when saving so the checkpoint loads without the DDP wrapper, and rank-0-only writes for checkpoints
and logs. Reach for FSDP instead of DDP when the parameters, gradients, and optimizer state no longer fit on one GPU,
because it shards all three across ranks rather than replicating them.
[references/distributed.md](references/distributed.md) has the rest.

---

### Avoid the classic traps

| Trap | Do instead |
| --- | --- |
| `x += residual` or `relu(x, inplace=True)` on a tensor autograd needs | `x = x + residual`, `x = F.relu(x)` |
| `.item()` before `backward` | Keep the tensor, call `.item()` only to log |
| `model.to(device)` inside the training loop | Move once before the loop |
| Accumulating `total_loss += loss` | Accumulate `loss.item()`, or the graph is retained |
| `torch.load(path)` with no `weights_only` | `torch.load(path, map_location="cpu", weights_only=True)` |
| Validating without `model.eval()` | Set the mode, and wrap in `@torch.no_grad()` |

---

### Reference files

| Open this | For |
| --- | --- |
| [references/training-loop.md](references/training-loop.md) | Full train and validate loops, schedulers, checkpoint and resume |
| [references/data-pipeline.md](references/data-pipeline.md) | Dataset design, collate functions, sampling, worker seeding |
| [references/performance.md](references/performance.md) | AMP, gradient checkpointing, `torch.compile`, profiling, memory |
| [references/distributed.md](references/distributed.md) | DDP, `torchrun`, samplers, rank-aware logging, FSDP |

---

### Related skills

- `python-patterns` for the Python the training script is written in, and for the pytest suite around data
  pipelines, shapes, and training steps.
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
