"""Runnable examples for the map-style DataLoader article (PyTorch 2.8).

python dataloader-demo.py --workers 0
python dataloader-demo.py --workers 1
python dataloader-demo.py --workers 2 --slow
python dataloader-demo.py --workers 2 --ragged
python dataloader-demo.py --workers 2 --bulk
torchrun --standalone --nproc-per-node=2 dataloader-demo.py --ddp --workers 1
"""

import argparse
import os
import time

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import (
    BatchSampler, DataLoader, Dataset, DistributedSampler, Sampler,
    default_collate, get_worker_info,
)

ORDER = [3, 0, 4, 1, 2]


class FiveSamples(Dataset):
    def __len__(self):
        return 5

    def __getitem__(self, index):
        worker = get_worker_info()
        return {
            "index": index,
            "x": torch.tensor([index, 10 * index], dtype=torch.float32),
            "y": index % 2,
            "worker": -1 if worker is None else worker.id,
        }


class FixedOrder(Sampler):
    def __iter__(self):
        return iter(ORDER)

    def __len__(self):
        return len(ORDER)


class SlowSamples(FiveSamples):
    def __getitem__(self, index):
        if index == 3:
            time.sleep(0.3)
        return super().__getitem__(index)


class RaggedSamples(FiveSamples):
    def __getitem__(self, index):
        sample = super().__getitem__(index)
        sample["x"] = torch.arange(1, index + 2, dtype=torch.float32)
        return sample


def pad_collate(samples):
    sequences = [sample["x"] for sample in samples]
    batch = default_collate([
        {key: value for key, value in sample.items() if key != "x"}
        for sample in samples
    ])
    batch["lengths"] = torch.tensor([len(sequence) for sequence in sequences])
    batch["x"] = pad_sequence(sequences, batch_first=True, padding_value=0)
    batch["mask"] = torch.arange(batch["x"].shape[1])[None, :] < batch["lengths"][:, None]
    return batch


class BulkSamples(FiveSamples):
    def __getitems__(self, indices):
        # Demonstrates the interface, not faster I/O. A real backend could
        # issue one batch query, then restore this requested index order.
        return [self[index] for index in indices]


def trace_collate(samples):
    batch = default_collate(samples)
    worker = get_worker_info()
    batch["collate_worker"] = -1 if worker is None else worker.id
    return batch


def worker_options(workers):
    if workers == 0:
        return {}
    return {"multiprocessing_context": "spawn", "prefetch_factor": 2}


def run_local(args):
    dataset_type = (RaggedSamples if args.ragged else BulkSamples if args.bulk
                    else SlowSamples if args.slow else FiveSamples)
    loader = DataLoader(
        dataset_type(),
        batch_sampler=BatchSampler(FixedOrder(), batch_size=2, drop_last=args.drop_batch),
        num_workers=args.workers,
        collate_fn=pad_collate if args.ragged else trace_collate,
        in_order=not args.unordered,
        **worker_options(args.workers),
    )
    for batch in loader:
        fields = {
            "indices": batch["index"].tolist(),
            "sample_workers": batch["worker"].tolist(),
            "x": batch["x"].tolist(),
        }
        if "collate_worker" in batch:
            fields["collate_worker"] = batch["collate_worker"]
        if "lengths" in batch:
            fields["lengths"] = batch["lengths"].tolist()
            fields["mask"] = batch["mask"].tolist()
        print(fields, flush=True)


def run_ddp(args):
    local_rank = int(os.environ["LOCAL_RANK"])
    device = torch.device("cuda", local_rank) if args.device == "cuda" else torch.device("cpu")
    if device.type == "cuda":
        torch.cuda.set_device(device)
    dist.init_process_group("nccl" if device.type == "cuda" else "gloo")
    try:
        rank = dist.get_rank()
        dataset = FiveSamples()
        sampler = DistributedSampler(
            dataset, shuffle=True, seed=193, drop_last=args.drop_sampler,
        )
        loader = DataLoader(
            dataset, sampler=sampler, batch_size=2, drop_last=args.drop_batch,
            num_workers=args.workers, collate_fn=trace_collate,
            pin_memory=device.type == "cuda",
            generator=torch.Generator().manual_seed(1000 + rank),
            **worker_options(args.workers),
        )
        torch.manual_seed(0)
        model = DistributedDataParallel(
            torch.nn.Linear(2, 2).to(device),
            device_ids=[local_rank] if device.type == "cuda" else None,
        )
        optimizer = torch.optim.SGD(model.parameters(), lr=0.001)
        for epoch in range(args.epochs):
            sampler.set_epoch(epoch)
            for step, batch in enumerate(loader):
                x = batch["x"].to(device, non_blocking=device.type == "cuda")
                y = batch["y"].to(device, non_blocking=device.type == "cuda")
                optimizer.zero_grad()
                loss = torch.nn.functional.cross_entropy(model(x), y)
                loss.backward()
                optimizer.step()
                print({"rank": rank, "epoch": epoch, "step": step,
                       "indices": batch["index"].tolist(),
                       "sample_workers": batch["worker"].tolist(),
                       "collate_worker": batch["collate_worker"]}, flush=True)
    finally:
        dist.destroy_process_group()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--ddp", action="store_true")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--slow", action="store_true")
    parser.add_argument("--unordered", action="store_true")
    parser.add_argument("--ragged", action="store_true")
    parser.add_argument("--bulk", action="store_true")
    parser.add_argument("--drop-sampler", action="store_true")
    parser.add_argument("--drop-batch", action="store_true")
    args = parser.parse_args()
    if args.workers < 0:
        parser.error("--workers must be nonnegative")
    if args.epochs < 1:
        parser.error("--epochs must be positive")
    if args.ddp and (args.ragged or args.bulk or args.slow or args.unordered):
        parser.error("--ddp uses the fixed-size dataset and ordered delivery")
    torch.set_num_threads(1)
    run_ddp(args) if args.ddp else run_local(args)


if __name__ == "__main__":
    main()
