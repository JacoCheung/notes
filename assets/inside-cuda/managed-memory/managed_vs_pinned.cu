// Build: nvcc -O2 -lineinfo managed_vs_pinned.cu -o managed_vs_pinned
// Run:   ./managed_vs_pinned managed
//        ./managed_vs_pinned pinned
// CUDA 12+, Linux. An executable example, not a captured benchmark.
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

static void check(cudaError_t status, const char* call, int line) {
    if (status != cudaSuccess) {
        std::fprintf(stderr, "line %d: %s: %s\n", line, call,
                     cudaGetErrorString(status));
        std::exit(EXIT_FAILURE);
    }
}
#define CUDA_CHECK(call) check((call), #call, __LINE__)

__global__ void read_input(const float* src, float* dst, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) dst[i] = src[i] + 1.0f;
}

int main(int argc, char** argv) {
    if (argc != 2 || (std::strcmp(argv[1], "managed") != 0 &&
                      std::strcmp(argv[1], "pinned") != 0)) {
        std::fprintf(stderr, "Usage: %s managed|pinned\n", argv[0]);
        return EXIT_FAILURE;
    }
    const bool managed = std::strcmp(argv[1], "managed") == 0;
    // Set host-mapping flags before initializing the default device context.
    CUDA_CHECK(cudaSetDeviceFlags(cudaDeviceMapHost));
    CUDA_CHECK(cudaSetDevice(0));
    cudaDeviceProp prop{};
    CUDA_CHECK(cudaGetDeviceProperties(&prop, 0));
    if (managed && (!prop.managedMemory || !prop.concurrentManagedAccess)) {
        std::fprintf(stderr, "This example needs managedMemory and concurrentManagedAccess.\n");
        return EXIT_FAILURE;
    }
    if (!managed && !prop.canMapHostMemory) {
        std::fprintf(stderr, "This device cannot map host memory.\n");
        return EXIT_FAILURE;
    }

    constexpr int n = 1 << 20;
    constexpr size_t bytes = size_t(n) * sizeof(float);
    float *cpu_input = nullptr, *gpu_input = nullptr, *output = nullptr;
    if (managed) {
        CUDA_CHECK(cudaMallocManaged(&cpu_input, bytes));
        gpu_input = cpu_input;
    } else {
        CUDA_CHECK(cudaHostAlloc(&cpu_input, bytes, cudaHostAllocMapped));
        CUDA_CHECK(cudaHostGetDevicePointer(&gpu_input, cpu_input, 0));
    }
    CUDA_CHECK(cudaMalloc(&output, bytes));
    for (int i = 0; i < n; ++i) cpu_input[i] = float(i);

    cudaPointerAttributes attr{};
    CUDA_CHECK(cudaPointerGetAttributes(&attr, gpu_input));
    std::printf("GPU: %s; input: %s; bytes: %zu\n", prop.name,
                attr.type == cudaMemoryTypeManaged ? "managed" :
                attr.type == cudaMemoryTypeHost ? "host" : "other", bytes);
    std::printf("CPU pointer: %p; GPU pointer: %p\n",
                static_cast<void*>(cpu_input), static_cast<void*>(gpu_input));

    // The CPU does not touch the input between the two launches.
    // No GPU prefetch: observe the policy chosen for a CPU-initialized input.
    for (int pass = 0; pass < 2; ++pass) {
        read_input<<<(n + 255) / 256, 256>>>(gpu_input, output, n);
        CUDA_CHECK(cudaGetLastError());
        CUDA_CHECK(cudaDeviceSynchronize());
        std::printf("GPU pass %d complete\n", pass + 1);
    }

    std::vector<float> result(n);
    CUDA_CHECK(cudaMemcpy(result.data(), output, bytes, cudaMemcpyDeviceToHost));
    bool correct = true;
    for (int i = 0; i < n; ++i) {
        if (result[i] != float(i) + 1.0f) {
            std::fprintf(stderr, "Mismatch at %d: got %g\n", i, result[i]);
            correct = false;
            break;
        }
    }
    CUDA_CHECK(cudaFree(output));
    if (managed) CUDA_CHECK(cudaFree(cpu_input));
    else CUDA_CHECK(cudaFreeHost(cpu_input));
    if (correct) std::puts("Output verified");
    return correct ? EXIT_SUCCESS : EXIT_FAILURE;
}
