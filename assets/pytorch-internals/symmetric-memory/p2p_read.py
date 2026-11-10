"""Two-rank peer load + compute, following PyTorch v2.9.0 CUDA SymmMem APIs.

Run on one Linux host with two mutually P2P-accessible NVIDIA GPUs:
    torchrun --standalone --nproc-per-node=2 p2p_read.py
Requires a CUDA PyTorch build with symmetric memory and matching Triton.
Source-reviewed example; no multi-GPU execution was performed for this article.
"""
import os
from datetime import timedelta

# Keep the dedicated-allocation model when running newer PyTorch builds.
# PyTorch 2.9.0 does not use the later implicit symmetric-memory pool.
os.environ["TORCH_SYMMMEM_IMPLICIT_POOL"] = "0"

import torch
import torch.distributed as dist
import torch.distributed._symmetric_memory as symm_mem
import triton
import triton.language as tl


# BEGIN kernel
@triton.jit
def peer_read_add_one(src, dst, N: tl.constexpr, BLOCK: tl.constexpr):
    i = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    value = tl.load(src + i, mask=i < N, other=0.0)
    tl.store(dst + i, value + 1.0, mask=i < N)
# END kernel


def main():
    local_rank = int(os.environ["LOCAL_RANK"])
    if not torch.cuda.is_available() or torch.cuda.device_count() != 2:
        raise RuntimeError("Expose exactly two CUDA GPUs, e.g. CUDA_VISIBLE_DEVICES=0,1")
    torch.cuda.set_device(local_rank)
    if not torch.cuda.can_device_access_peer(local_rank, 1 - local_rank):
        raise RuntimeError("This example needs mutually accessible peer GPUs")
    dist.init_process_group("nccl", timeout=timedelta(seconds=120))
    if dist.get_world_size() != 2:
        raise RuntimeError("Launch exactly two ranks on one host")

    # BEGIN access
    symm_mem.set_backend("CUDA")  # Before the first symmetric allocation.
    rank = dist.get_rank()
    device = torch.device("cuda", local_rank)
    n = 1025  # Includes a partial Triton block.
    x = symm_mem.empty(n, dtype=torch.float32, device=device)
    hdl = symm_mem.rendezvous(x, group=dist.group.WORLD)
    peer = hdl.get_buffer(1 - rank, x.shape, x.dtype)
    y = torch.empty(n, dtype=x.dtype, device=device)

    for step in range(3):
        x.fill_(10 * rank + step)
        hdl.barrier(channel=0)  # Publish this iteration's input.
        peer_read_add_one[(triton.cdiv(n, 256),)](peer, y, n, BLOCK=256)
        hdl.barrier(channel=0)  # All peer reads complete before input reuse.
        torch.cuda.synchronize()
        expected = torch.full_like(y, 10 * (1 - rank) + step + 1)
        torch.testing.assert_close(y, expected, rtol=0, atol=0)
    # END access

    print(f"rank {rank}: PASS; final y[0]={y[0].item():.0f}", flush=True)
    # No rank tears down its allocation while another rank still uses it.
    dist.barrier()
    torch.cuda.synchronize()
    del peer, hdl, x
    dist.destroy_process_group()


if __name__ == "__main__":
    main()
