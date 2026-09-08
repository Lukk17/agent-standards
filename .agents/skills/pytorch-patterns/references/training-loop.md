# Training and Validation Loops

The full shape of a training step, an evaluation pass, scheduling, and checkpoint and resume. Open this when the hub
rule shows a fragment and you need the loop it belongs to.

---

### One epoch of training

The loop below is the assembled form of the hub rules: mode set, gradients zeroed before the forward pass, autocast
around the forward, clipping between `backward` and `step`, and the loss detached before it is accumulated.

```python
def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    scaler: torch.amp.GradScaler | None = None,
) -> float:
    model.train()
    total_loss = 0.0

    for data, target in loader:
        data = data.to(device, non_blocking=True)
        target = target.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        with torch.amp.autocast("cuda", enabled=scaler is not None):
            loss = criterion(model(data), target)

        if scaler is not None:
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        total_loss += loss.item()

    return total_loss / len(loader)
```

`scaler.unscale_(optimizer)` before clipping is what makes the clip threshold mean the same thing with and without
mixed precision. Clipping scaled gradients clips at the wrong magnitude.

---

### Evaluation

Evaluation sets `eval` mode, disables gradients, and never touches the optimizer. Returning both the loss and the
metric keeps early stopping and reporting on the same numbers.

```python
@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0

    for data, target in loader:
        data = data.to(device, non_blocking=True)
        target = target.to(device, non_blocking=True)

        output = model(data)
        total_loss += criterion(output, target).item()
        correct += (output.argmax(1) == target).sum().item()
        total += target.size(0)

    return total_loss / len(loader), correct / total
```

Divide the metric by the number of samples and the loss by the number of batches. Mixing the two is the most common
reason a reported accuracy does not match a hand check.

---

### Step the scheduler at the right time

Most schedulers step once per epoch. `OneCycleLR` and other batch-wise schedules step once per batch, inside the
training loop, after `optimizer.step()`. Stepping the wrong one at the wrong rate silently changes the schedule.

Pass:

```python
for epoch in range(epochs):
    train_loss = train_one_epoch(model, train_loader, optimizer, criterion, device, scaler)
    val_loss, val_acc = evaluate(model, val_loader, criterion, device)
    scheduler.step(val_loss)
```

Fail:

```python
for epoch in range(epochs):
    train_one_epoch(...)
    scheduler.step()
    optimizer.step()
```

`ReduceLROnPlateau` takes the metric as an argument. Every other scheduler takes none, and passing one to those is a
silent no-op in some versions.

---

### Accumulate gradients when the batch will not fit

Gradient accumulation gives the optimizer the statistics of a large batch on hardware that cannot hold one. Divide
the loss by the accumulation count, or the effective learning rate scales with it.

```python
accumulation_steps = 4

for step, (data, target) in enumerate(loader):
    with torch.amp.autocast("cuda"):
        loss = criterion(model(data.to(device)), target.to(device)) / accumulation_steps

    scaler.scale(loss).backward()

    if (step + 1) % accumulation_steps == 0:
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)
```

Under DDP, wrap the non-stepping iterations in `model.no_sync()` so gradients are only all-reduced on the step that
actually applies them.

---

### Save and resume the whole state

```python
def save_checkpoint(state: dict[str, object], path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    torch.save(state, tmp)
    tmp.replace(path)


def load_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    scheduler: torch.optim.lr_scheduler.LRScheduler | None = None,
) -> int:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer is not None:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    if scheduler is not None:
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    return checkpoint["epoch"]
```

Writing to a temporary file and renaming makes the save atomic, so a job killed mid-write leaves the previous
checkpoint intact instead of a truncated one.

Load to CPU and move afterwards. Loading straight to `cuda:0` fails on a machine with a different GPU count and
pins the checkpoint to the topology it was written on.

---

### Track the best model, not the last

The last epoch is rarely the best one. Keep the best by validation metric, and keep the last separately so a crashed
run can resume.

```python
if val_loss < best_val_loss:
    best_val_loss = val_loss
    save_checkpoint(state, checkpoint_dir / "best.pt")
save_checkpoint(state, checkpoint_dir / "last.pt")
```

Early stopping counts epochs since the best value, not since the last improvement in training loss. Training loss
still falling while validation loss rises is the signal to stop, not a reason to wait.

---

### Log once per epoch, from one place

A print inside the batch loop produces thousands of lines nobody reads and slows the loop down. Aggregate over the
epoch, log once, and send the numbers to whatever the project uses for metrics.

Pass:

```python
logger.info(
    "epoch %d train_loss=%.4f val_loss=%.4f val_acc=%.4f lr=%.2e",
    epoch, train_loss, val_loss, val_acc, optimizer.param_groups[0]["lr"],
)
```

Fail:

```python
for batch_idx, (data, target) in enumerate(loader):
    print(f"batch {batch_idx} loss {loss.item()}")
```

Log discipline in general, meaning levels, structure, and correlation, belongs to `observability-and-logging`.
