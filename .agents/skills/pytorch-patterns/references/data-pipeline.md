# Data Pipelines

Dataset design, collate functions, sampling, and the worker settings that decide whether the GPU waits. Open this
when the model is fast and the run is not.

---

### Keep the Dataset dumb and cheap

`__getitem__` returns one example. It opens a file, decodes it, applies the transform, and returns tensors. It does
not hold a database connection, a CUDA tensor, or anything else that cannot be pickled to a worker process.

Pass:

```python
class ImageDataset(Dataset):
    def __init__(self, image_dir: Path, labels: dict[str, int], transform: Callable | None = None) -> None:
        self.image_paths = sorted(image_dir.glob("*.jpg"))
        self.labels = labels
        self.transform = transform

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        path = self.image_paths[idx]
        image = Image.open(path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, self.labels[path.stem]
```

Fail:

```python
class ImageDataset(Dataset):
    def __init__(self, image_dir: Path) -> None:
        self.images = [Image.open(p).convert("RGB") for p in image_dir.glob("*.jpg")]
```

The failing version loads the whole dataset into memory at construction and then copies it into every worker process.

`sorted(...)` rather than raw `glob` matters: filesystem order is not stable across machines, so an unsorted index
makes the run unreproducible even with a fixed seed.

---

### Open handles lazily, per worker

A file handle, a database connection, or an LMDB environment opened in `__init__` is forked into every worker and
shared, which corrupts reads. Open it on first use inside the worker instead.

```python
def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
    if self._env is None:
        self._env = lmdb.open(str(self.path), readonly=True, lock=False)
    ...
```

---

### Set the loader up for throughput

```python
loader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    num_workers=8,
    pin_memory=True,
    persistent_workers=True,
    prefetch_factor=4,
    drop_last=True,
)
```

| Setting | Why |
| --- | --- |
| `num_workers` | Decoding and augmentation move off the training process. Start near the physical core count |
| `pin_memory` | Page-locked staging buffers, which is what makes `non_blocking=True` transfers overlap |
| `persistent_workers` | Workers survive between epochs instead of being respawned each time |
| `prefetch_factor` | Batches queued per worker, so a slow example does not stall the step |
| `drop_last` | Constant batch size, which batch norm and compiled graphs both prefer |

More workers is not always better. Each one costs memory and a copy of the dataset object, and past the point where
the GPU is saturated they only add contention. Raise it until GPU utilisation stops improving, then stop.

---

### Seed the workers

Each worker inherits the same base seed, so without a `worker_init_fn` several workers can produce identical
augmentations. Seed from the worker id, and give the loader its own generator so shuffling is reproducible.

```python
def seed_worker(worker_id: int) -> None:
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)

generator = torch.Generator()
generator.manual_seed(42)

loader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=8,
                    worker_init_fn=seed_worker, generator=generator)
```

---

### Collate variable-length data in one place

Padding belongs in `collate_fn`, where the batch is known, not in `__getitem__`, where padding to a global maximum
wastes memory on every short example. Return the lengths too, so the model can build a mask.

```python
def collate_sequences(batch: list[tuple[torch.Tensor, int]]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    sequences, labels = zip(*batch, strict=True)
    lengths = torch.tensor([len(s) for s in sequences])
    padded = nn.utils.rnn.pad_sequence(sequences, batch_first=True, padding_value=0)
    return padded, lengths, torch.tensor(labels)
```

Pass the function to the loader:

```python
loader = DataLoader(dataset, batch_size=32, collate_fn=collate_sequences)
```

Sort or bucket by length before batching when sequence lengths vary a lot. Padding a 10-token example to 512 wastes
most of the batch.

---

### Choose the sampler deliberately

`shuffle=True` is a `RandomSampler` in disguise, and it is mutually exclusive with a custom sampler. Reach for an
explicit sampler when the default distribution is wrong.

| Situation | Sampler |
| --- | --- |
| Balanced classes, single process | `shuffle=True` |
| Imbalanced classes | `WeightedRandomSampler` with per-example weights |
| Multi-GPU training | `DistributedSampler`, with `set_epoch` called every epoch |
| Deterministic evaluation | `shuffle=False`, and `drop_last=False` so nothing is skipped |

Never set `shuffle=True` on a validation loader. It changes nothing about the metric and makes per-batch debugging
irreproducible.

---

### Transform on the GPU when the CPU is the bottleneck

If workers are pinned at full and the GPU is idle, move augmentation onto the device. Batched tensor operations on
the GPU are often faster than per-example PIL work on the CPU, and they free the workers for decoding.

Measure first. A GPU already at high utilisation gains nothing and loses the overlap the workers were providing.
