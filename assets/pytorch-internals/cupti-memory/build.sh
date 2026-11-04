#!/usr/bin/env bash
set -euo pipefail

# Override CUDA_INCLUDE, CUPTI_INCLUDE, and CUPTI_LIB for nonstandard installs.
CUDA_ROOT=${CUDA_ROOT:-/usr/local/cuda-12.8}
CUDA_INCLUDE=${CUDA_INCLUDE:-$CUDA_ROOT/include}
CUPTI_INCLUDE=${CUPTI_INCLUDE:-$CUDA_ROOT/extras/CUPTI/include}
CUPTI_LIB=${CUPTI_LIB:-$CUDA_ROOT/extras/CUPTI/lib64}
TRACE_BUILD=${TRACE_BUILD:-./build}
SOURCE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
test -f "$CUDA_INCLUDE/cuda.h"
test -f "$CUPTI_INCLUDE/cupti.h"
if [[ -f "$CUPTI_LIB/libcupti.so" ]]; then
    CUPTI_LINK=-lcupti
else
    test -f "$CUPTI_LIB/libcupti.so.12"
    CUPTI_LINK=-l:libcupti.so.12
fi
mkdir -p "$TRACE_BUILD"
"${CXX:-g++}" -std=c++17 -O2 -Wall -Wextra -Werror -fPIC -shared -pthread \
    -I"$CUDA_INCLUDE" -I"$CUPTI_INCLUDE" "$SOURCE_DIR/memory_trace.cpp" \
    -L"$CUPTI_LIB" "$CUPTI_LINK" -Wl,-rpath,"$CUPTI_LIB" \
    -o "$TRACE_BUILD/libmemory_trace.so"
printf 'Built %s/libmemory_trace.so\n' "$TRACE_BUILD"
