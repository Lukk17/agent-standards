# PyTorch Checklist

Run it before calling a model, a training loop or a data pipeline done. The rules behind each item are in [SKILL.md](../SKILL.md).

- [ ] The device is resolved once and every tensor and module moves to it.
- [ ] Every run seeds Python, NumPy, and torch, and records whether cudnn was deterministic.
- [ ] Shapes are annotated through `forward`, and flattening uses `flatten(start_dim=1)`.
- [ ] All layers are constructed in `__init__` and weights are initialised explicitly.
- [ ] `model.train()` and `model.eval()` are set, and evaluation runs under `@torch.no_grad()`.
- [ ] Gradients are zeroed with `set_to_none=True` and clipped between `backward` and `step`.
- [ ] Checkpoints hold model, optimizer, scheduler, scaler, and epoch, and load with `weights_only=True`.
- [ ] The DataLoader sets `num_workers`, `pin_memory`, and `persistent_workers`, and the GPU is not starved.
- [ ] Mixed precision uses `torch.amp.autocast` with a `GradScaler`, never a manual `.half()`.
- [ ] Gradient checkpointing passes `use_reentrant=False`.
- [ ] Multi-GPU runs use DDP under `torchrun`, call `sampler.set_epoch`, and write only from rank 0.
- [ ] No in-place operation sits on a tensor autograd still needs.
