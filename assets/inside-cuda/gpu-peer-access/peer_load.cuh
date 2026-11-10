#pragma once
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <vector>

inline void cuda_check(cudaError_t status, const char* call, int line) {
    if (status != cudaSuccess) {
        std::fprintf(stderr, "line %d: %s: %s\n", line, call,
                     cudaGetErrorString(status));
        std::exit(1);
    }
}
#define CUDA_CHECK(call) cuda_check((call), #call, __LINE__)

// BEGIN kernel
extern "C" __global__ void peer_load(const float* src, float* dst, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        float value = src[i];  // src can refer to local or mapped peer memory.
        dst[i] = value + 1.0f;
    }
}
// END kernel

constexpr int kCount = 65536;
constexpr size_t kBytes = kCount * sizeof(float);

inline int device_arg(const char* text) {
    char* end = nullptr;
    long value = std::strtol(text, &end, 10);
    if (!*text || *end || value < 0 || value > 1024) {
        std::fprintf(stderr, "Invalid device ordinal: %s\n", text);
        std::exit(2);
    }
    return static_cast<int>(value);
}

inline void require_peer(int reader, int owner) {
    int count = 0, supported = 0, uva_reader = 0, uva_owner = 0;
    CUDA_CHECK(cudaGetDeviceCount(&count));
    if (reader == owner || reader >= count || owner >= count) {
        std::fprintf(stderr, "Need two different visible GPUs.\n");
        std::exit(77);
    }
    CUDA_CHECK(cudaDeviceGetAttribute(&uva_reader, cudaDevAttrUnifiedAddressing, reader));
    CUDA_CHECK(cudaDeviceGetAttribute(&uva_owner, cudaDevAttrUnifiedAddressing, owner));
    CUDA_CHECK(cudaDeviceCanAccessPeer(&supported, reader, owner));
    if (!supported || !uva_reader || !uva_owner) {
        std::fprintf(stderr, "P2P/UVA unavailable for reader %d -> owner %d.\n", reader, owner);
        std::exit(77);
    }
}

inline void initialize(float* ptr) {
    std::vector<float> host(kCount);
    for (int i = 0; i < kCount; ++i) host[i] = static_cast<float>(i);
    CUDA_CHECK(cudaMemcpy(ptr, host.data(), kBytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaDeviceSynchronize()); // Producer completion before publication.
}

inline void verify(const float* ptr) {
    std::vector<float> host(kCount);
    CUDA_CHECK(cudaMemcpy(host.data(), ptr, kBytes, cudaMemcpyDeviceToHost));
    for (int i = 0; i < kCount; ++i) {
        if (host[i] != static_cast<float>(i) + 1.0f) {
            std::fprintf(stderr, "Mismatch at %d: got %g\n", i, host[i]);
            std::exit(1);
        }
    }
    std::fprintf(stderr, "PASS: %d peer loads verified.\n", kCount);
}
