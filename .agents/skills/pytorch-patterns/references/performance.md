# PyTorch Performance

Mixed precision, gradient checkpointing, compilation, profiling, and memory. Open this when a run is too slow or too
large, after the data pipeline has been ruled out.

---

### Measure before changing anything

There are three usual bottlenecks and they need different fixes: the data loader starving the GPU, the step itself
being slow, and memory forcing a batch size that wastes the device. Find out which one you have first.

```bash
nvidia-smi dmon -s um
```

Sustained low GPU utilisation with busy CPU means the loader, and nothing in this file will help. Go to
[data-pipeline.md](data-pipeline.md).

---

### Mixed precision with autocast and a scaler

Autocast runs the eligible operations in bf16 or fp16 while keeping the master weights in fp32. The `GradScaler`
scales the loss so small fp16 gradients do not flush to zero, then unscales before the optimizer sees them.

Pass:

```python
scaler = torch.amp.GradScaler("cuda")

with torch.amp.autocast("cuda"):
    loss = criterion(model(data), target)

scaler.scale(loss).backward()
scaler.unscale_(optimizer)
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
scaler.step(optimizer)
scaler.update()
optimizer.zero_grad(set_to_none=True)
```

Fail:

```python
model = model.half()
loss = criterion(model(data), target)
loss.backward()
```

Only the forward pass and the loss go inside `autocast`. Putting `backward` inside it is a common mistake that does
nothing useful, and the optimizer step must stay outside.

bf16 has fp32's exponent range, so on hardware that supports it the scaler is unnecessary. Keep the scaler in the
code path anyway and disable it by construction, so switching precision is a config change rather than an edit.

---

### Trade compute for memory with gradient checkpointing

Checkpointing discards intermediate activations and recomputes them during the backward pass. It typically buys a
large memory saving for roughly 20 to 30 percent more compute, which is what lets a model fit at all.

```python
class LargeModel(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = checkpoint(self.block1, x, use_reentrant=False)
        x = checkpoint(self.block2, x, use_reentrant=False)
        return self.head(x)
```

`use_reentrant=False` is not optional. The reentrant implementation breaks with keyword arguments, with `no_grad`
regions, and with anything that does not have every input requiring gradients, and it is the legacy path.

---

### Compile the model

`torch.compile` traces the model into fused kernels, removing Python overhead per step. Compilation happens on the
first call, so the first iteration is slow and the rest are not.

```python
model = torch.compile(model, mode="reduce-overhead")
```

| Mode | Use for |
| --- | --- |
| `default` | The safe first try |
| `reduce-overhead` | Small models where Python overhead dominates the step |
| `max-autotune` | Long runs where a slow warmup pays for itself |

Changing input shapes triggers recompilation, so a ragged batch size defeats it. Use `drop_last=True` and bucket by
length, or accept the recompiles and measure whether it is still a win.

Compile the model before wrapping it in `DistributedDataParallel`, not after.

---

### Profile the step

The PyTorch profiler attributes time to operators and shows the CPU and GPU timelines together, which is how you find
a synchronisation point you did not know was there.

```python
with torch.profiler.profile(
    activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
    schedule=torch.profiler.schedule(wait=1, warmup=1, active=3),
    on_trace_ready=torch.profiler.tensorboard_trace_handler("./logs"),
) as prof:
    for step, batch in enumerate(loader):
        train_step(batch)
        prof.step()
        if step >= 5:
            break
```

Profile a handful of steps after a warmup, never the first step, which measures compilation and allocator warmup
rather than the model.

---

### Remove the hidden synchronisation points

CUDA is asynchronous. Anything that reads a value back to Python blocks until the queue drains, so a `.item()` inside
the loop turns an overlapped pipeline into a serial one.

Pass:

```python
running_loss += loss.detach()
...
epoch_loss = (running_loss / len(loader)).item()
```

Fail:

```python
running_loss += loss.item()
print(f"loss {loss.item():.4f}")
```

`.item()`, `.cpu()`, `.numpy()`, `print` of a tensor, and `torch.cuda.synchronize` are all synchronisation points.
One per epoch is fine, one per batch is a measurable cost.

---

### Diagnose out-of-memory before lowering the batch size

Read what is actually allocated rather than halving the batch and hoping.

```python
print(torch.cuda.memory_summary())
```

The usual causes, in the order they show up:

- A tensor with its graph attached accumulated across batches, from `total += loss` instead of `loss.detach()`.
- Validation running without `@torch.no_grad()`, which keeps activations for a backward pass that never comes.
- Fragmentation from varying shapes, which `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` often relieves.
- A cached, genuinely too-large model, at which point gradient checkpointing or FSDP is the answer, not a smaller
  batch.

`torch.cuda.empty_cache()` returns cached blocks to the driver. It does not fix a leak, it only makes the number in
`nvidia-smi` smaller, so reach for it when handing the GPU to another process and not as a fix.

---

### Set the matmul precision

On Ampere and later, allowing TF32 for matmuls is a large speedup at a precision loss that does not matter for most
training. It is a one-line decision that should be explicit rather than inherited from a default that has changed
between releases.

```python
torch.set_float32_matmul_precision("high")
```
