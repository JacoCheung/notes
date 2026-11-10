#!/usr/bin/env bash
set -euo pipefail

# Keep trace output outside a source worktree. Override NVCC and CUDA_SM for
# your installed toolkit and GPU, for example CUDA_SM=sm_80 for an A100.
trace_dir=${1:?Usage: bash trace.sh /path/to/output-directory}
nvcc_bin=${NVCC:-nvcc}
cuda_sm=${CUDA_SM:-sm_90}
for tool in "$nvcc_bin" strace ltrace; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 1; }
done
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
nvcc_path=$(readlink -f -- "$(command -v "$nvcc_bin")")
cuda_lib=$(dirname -- "$nvcc_path")/../lib64
mkdir -p -- "$trace_dir"
trace_dir=$(cd -- "$trace_dir" && pwd)
"$nvcc_bin" -std=c++17 -O0 -lineinfo -arch="$cuda_sm" --cudart shared \
    -Xlinker -rpath -Xlinker "$cuda_lib" "$source_dir/hello.cu" -o "$trace_dir/hello"
(
    cd -- "$trace_dir"
    # Full syscall capture; keep BEGIN/END marker writes in the log.
    strace -f -ttt -T -yy -s 160 -o syscalls.txt ./hello \
        >hello.stdout.txt 2>hello.stderr.txt
    # A separate execution: library calls and syscalls have different clocks.
    ltrace -F "$source_dir/cuda.ltrace.conf" -f -tt -e 'cuda*' \
        -o api.txt ./hello >api.stdout.txt 2>api.stderr.txt
    cat hello.stdout.txt
    cat api.stdout.txt
)
echo "Trace output: $trace_dir"
