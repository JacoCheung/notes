#!/usr/bin/env python3
"""Launch two independent CUDA processes and relay only their IPC handle."""
import argparse
from pathlib import Path
import subprocess
import sys


def read_exact(stream, size):
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            raise RuntimeError("Owner exited before publishing a complete IPC handle")
        data.extend(chunk)
    return bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default="./ipc_process")
    parser.add_argument("--reader", type=int, default=0)
    parser.add_argument("--owner", type=int, default=1)
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    devices = [str(args.reader), str(args.owner)]
    # A fresh executable initializes CUDA in each child. No initialized CUDA
    # context is inherited by a forked child.
    owner = subprocess.Popen([binary, "owner", *devices], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE)
    try:
        header = read_exact(owner.stdout, 4)
        size = int.from_bytes(header, sys.byteorder)
        if not 0 < size <= 4096:
            raise RuntimeError("Invalid IPC handle size")
        handle = read_exact(owner.stdout, size)
        result = subprocess.run([binary, "reader", *devices], input=header + handle)
        if result.returncode:
            raise RuntimeError("Reader failed with exit code %d" % result.returncode)
        owner.stdin.write(b"K")
        owner.stdin.flush()
        if owner.wait() != 0:
            raise RuntimeError("Owner failed during cleanup")
    finally:
        owner.stdin.close()
        owner.stdout.close()
        # EOF releases the owner's acknowledgement wait on failure. Only this
        # owned child is terminated if it cannot exit after the pipe closes.
        try:
            owner.wait(timeout=5)
        except subprocess.TimeoutExpired:
            owner.terminate()
            owner.wait(timeout=5)


if __name__ == "__main__":
    main()
