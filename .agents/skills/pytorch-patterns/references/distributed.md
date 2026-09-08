# Distributed Training

Running one job across several GPUs or several machines with DDP, and knowing when to move to FSDP. Open this when a
single-GPU script has to scale.

---

### One process per GPU, launched by torchrun

DDP replicates the model on every rank, runs the same step on different data, and all-reduces the gradients. Every
rank runs the same script, and `torchrun` supplies the environment that tells each one who it is.

```python
def main() -> None:
    dist.init_process_group(backend="nccl")
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)
    device = torch.device("cuda", local_rank)

    model = DistributedDataParallel(MyModel().to(device), device_ids=[local_rank])
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    sampler = DistributedSampler(dataset, shuffle=True)
    loader = DataLoader(dataset, batch_size=32, sampler=sampler, num_workers=8, pin_memory=True)

    for epoch in range(epochs):
        sampler.set_epoch(epoch)
        train_one_epoch(model, loader, optimizer, criterion, device)

        if dist.get_rank() == 0:
            save_checkpoint({"model_state_dict": model.module.state_dict()}, checkpoint_path)

    dist.destroy_process_group()


if __name__ == "__main__":
    main()
```

Single machine, four GPUs:

```bash
torchrun --standalone --nproc_per_node=4 train.py
```

Multiple machines, run on every node with a different `--node_rank`:

```bash
torchrun --nnodes=2 --node_rank=0 --nproc_per_node=8 --rdzv_backend=c10d --rdzv_endpoint=head:29500 train.py
```

Use `nccl` on NVIDIA GPUs and `gloo` on CPU. `torchrun` sets `RANK`, `LOCAL_RANK`, `WORLD_SIZE`, and the rendezvous
variables, so the script reads them rather than parsing arguments of its own.

---

### Call set_epoch on the sampler every epoch

`DistributedSampler` derives its shuffle from an internal epoch counter. Without `set_epoch`, every rank replays the
same order for the whole run, which quietly removes shuffling from the training.

Pass:

```python
for epoch in range(epochs):
    sampler.set_epoch(epoch)
    train_one_epoch(...)
```

Fail:

```python
for epoch in range(epochs):
    train_one_epoch(...)
```

The validation sampler needs `shuffle=False`, and `drop_last=False` so no rank silently discards samples and skews
the metric.

---

### Save from rank zero, unwrap the module

`model.state_dict()` on a DDP-wrapped model prefixes every key with `module.`, so the checkpoint only loads back into
another DDP wrapper. Save `model.module.state_dict()` instead.

Pass:

```python
if dist.get_rank() == 0:
    torch.save({"model_state_dict": model.module.state_dict()}, path)
dist.barrier()
```

Fail:

```python
torch.save({"model_state_dict": model.state_dict()}, path)
```

The failing version has every rank write the same file at the same time, which is a corrupted checkpoint waiting to
happen. The `barrier` after the write stops the other ranks racing ahead to a resume that reads a half-written file.

---

### Log and evaluate from rank zero

Every rank runs the same code, so an unguarded log line appears once per GPU and a progress bar becomes unreadable.
Metrics that must reflect the whole batch are reduced first, then logged once.

```python
def is_main() -> bool:
    return not dist.is_initialized() or dist.get_rank() == 0


def all_reduce_mean(value: torch.Tensor) -> torch.Tensor:
    dist.all_reduce(value, op=dist.ReduceOp.SUM)
    return value / dist.get_world_size()
```

Reduce a tensor on the device, not a Python float. Reducing after `.item()` means each rank reports only its own
shard and the numbers do not add up.

---

### Scale the learning rate with the effective batch

`batch_size` in the loader is per rank, so eight GPUs at 32 is an effective batch of 256. Keeping the single-GPU
learning rate on that batch usually underfits, and jumping straight to a large one diverges. Scale linearly with the
world size and add a warmup over the first few epochs.

```python
lr = base_lr * dist.get_world_size()
```

---

### Skip the gradient sync on accumulation steps

Under gradient accumulation, DDP all-reduces on every `backward` by default, which is network traffic for gradients
that are not being applied yet. `no_sync` suppresses it until the step that matters.

```python
should_step = (step + 1) % accumulation_steps == 0
context = contextlib.nullcontext() if should_step else model.no_sync()

with context:
    loss.backward()

if should_step:
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
```

---

### Move to FSDP when the model no longer fits

DDP replicates parameters, gradients, and optimizer state on every rank, so the largest model it can train is the
one that fits on a single GPU. Fully Sharded Data Parallel shards all three across ranks and gathers each layer's
parameters only while it is being used, which is what makes a model larger than one device trainable.

Reach for it when memory rather than throughput is the limit, and expect to pay for it: FSDP adds communication on
every layer, its checkpointing needs a state-dict configuration of its own, and mixed precision is configured on the
wrapper rather than with a bare autocast. Start with DDP plus gradient checkpointing, and switch only when that is
not enough.

---

### Clean up, and make failure loud

An orphaned process group holds the GPU and the port, so the next launch fails with an unrelated error. Destroy the
group on the way out, including on the error path.

```python
try:
    main()
finally:
    if dist.is_initialized():
        dist.destroy_process_group()
```

Set a timeout on `init_process_group` so a rank that never joins fails the job instead of hanging the cluster all
night, and let a crashed rank crash: `torchrun` restarts the whole group, which is the recovery you want.
