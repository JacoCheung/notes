"""Controlled PyTorch allocation phases. Run each allocator mode in a fresh process."""
import argparse
import ctypes
import gc
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--trace", required=True, type=Path)
    args = parser.parse_args()
    # Importing torch does not intentionally create CUDA tensors in this script.
    # Set PYTORCH_CUDA_ALLOC_CONF in the launch command, before this import.
    import torch

    if torch.version.cuda is None:
        raise SystemExit("Install a CUDA-enabled PyTorch build; this is a CPU-only build.")
    tracer = ctypes.CDLL(str(args.library.resolve()))
    tracer.trace_start.argtypes = [ctypes.c_char_p]
    tracer.trace_mark.argtypes = [ctypes.c_char_p]
    tracer.trace_stop.argtypes = []
    for name in ("trace_start", "trace_mark", "trace_stop"):
        getattr(tracer, name).restype = ctypes.c_int

    def mark(name):
        if tracer.trace_mark(name.encode()) != 0:
            raise RuntimeError("Could not write trace phase " + name)

    def snapshot(name, **pointers):
        print(json.dumps({"phase": name,
            "allocated": torch.cuda.memory_allocated(),
            "reserved": torch.cuda.memory_reserved(), **pointers}), flush=True)

    args.trace.parent.mkdir(parents=True, exist_ok=True)
    if tracer.trace_start(os.fsencode(args.trace)) != 0:
        raise SystemExit("CUPTI subscription failed; inspect the error above.")
    try:
        mark("INIT")
        torch.cuda.init()
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        print(json.dumps({"torch": torch.__version__, "cuda_build": torch.version.cuda,
            "allocator_config": os.environ.get("PYTORCH_CUDA_ALLOC_CONF", ""),
            "backend": torch.cuda.memory.get_allocator_backend()}), flush=True)
        snapshot("INIT")

        mark("ALLOC_A")
        a = torch.empty(16 * 1024 * 1024, dtype=torch.float32, device="cuda")  # 64 MiB
        original = a.data_ptr()
        snapshot("ALLOC_A", a=hex(original))

        mark("DROP_A")
        del a
        gc.collect()
        snapshot("DROP_A")

        mark("REUSE_B")
        b = torch.empty(16 * 1024 * 1024, dtype=torch.float32, device="cuda")
        snapshot("REUSE_B", b=hex(b.data_ptr()), reused=(b.data_ptr() == original))

        mark("GROW_C")
        c = torch.empty(24 * 1024 * 1024, dtype=torch.float32, device="cuda")  # 96 MiB
        snapshot("GROW_C", c=hex(c.data_ptr()))

        mark("DROP_ALL")
        del b, c
        gc.collect()
        torch.cuda.synchronize()
        snapshot("DROP_ALL")

        mark("EMPTY_CACHE")
        torch.cuda.empty_cache()
        snapshot("EMPTY_CACHE")
        torch.cuda.synchronize()
    finally:
        # No application worker threads issue CUDA calls in this example.
        # Unsubscribe before ctypes can unload the library at process exit.
        if tracer.trace_stop() != 0:
            raise RuntimeError("Trace shutdown or file write failed")


if __name__ == "__main__":
    main()
