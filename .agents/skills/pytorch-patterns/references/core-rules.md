# PyTorch Core Rules in Depth

The Pass and Fail examples, the reasoning, and the trap table behind each rule the SKILL.md hub states in one or two lines. Open it when a hub rule needs its worked form or its full explanation. Written for PyTorch 2 on Python 3.14.

---

### Contents

- Write device-agnostic code
- Seed everything, and say so
- Track the shape at every step
- Build layers in `__init__`, never in `forward`
- Set the mode, and turn gradients off for evaluation
- Zero with `set_to_none`, clip before you step
- Checkpoint the whole training state
- Keep the GPU fed
- Reach for mixed precision and compilation before more hardware
- Scale out with DDP under torchrun
- Avoid the classic traps

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
[references/training-loop.md](training-loop.md).

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

A file holding only the weights cannot resume a run: the optimizer momentum, the scheduler position, the AMP scaler, and the epoch are all gone. Load with `weights_only=True` spelled out. It has been the `torch.load` default since PyTorch 2.6, and writing it explicitly keeps the script safe on an older 2.x install and stops a later edit from opting back into full unpickling, which runs arbitrary code from the file.

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
batching are in [references/data-pipeline.md](data-pipeline.md).

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
[references/performance.md](performance.md).

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
            state = {
                "model_state_dict": model.module.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "scaler_state_dict": scaler.state_dict(),
                "epoch": epoch,
            }
            save_checkpoint(state, path)
        dist.barrier()

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
[references/distributed.md](distributed.md) has the rest.

---

### Avoid the classic traps

| Trap | Do instead |
| --- | --- |
| `x += residual` or `relu(x, inplace=True)` on a tensor autograd needs | `x = x + residual`, `x = F.relu(x)` |
| `.item()` before `backward` | Keep the tensor, call `.item()` only to log |
| `model.to(device)` inside the training loop | Move once before the loop |
| Accumulating `total_loss += loss` | Accumulate `loss.detach()`, or the graph is retained, and call `.item()` once per epoch |
| `torch.load(path)` with no `weights_only` | `torch.load(path, map_location="cpu", weights_only=True)` |
| Validating without `model.eval()` | Set the mode, and wrap in `@torch.no_grad()` |
