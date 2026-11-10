#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>

static void check(cudaError_t status, const char* call) {
    if (status != cudaSuccess) {
        std::fprintf(stderr, "FAIL %s: %s\n", call, cudaGetErrorString(status));
        std::exit(1);
    }
}

// Markers are host writes, useful for locating each phase in strace output.
#define CALL(expr) do { \
    std::fprintf(stderr, "BEGIN %s\n", #expr); \
    check((expr), #expr); \
    std::fprintf(stderr, "END %s\n", #expr); \
} while (0)

__global__ void hello(int* result) {
    *result += 1;
}

int main() {
    std::setvbuf(stderr, nullptr, _IONBF, 0);
    CALL(cudaSetDevice(0));
    int* device = nullptr;
    int host = 40;
    CALL(cudaMalloc(&device, sizeof(int)));
    CALL(cudaMemcpy(device, &host, sizeof(int), cudaMemcpyHostToDevice));
    for (int launch = 1; launch <= 2; ++launch) {
        std::fprintf(stderr, "BEGIN kernel launch %d\n", launch);
        hello<<<1, 1>>>(device);
        check(cudaGetLastError(), "hello launch");
        std::fprintf(stderr, "END kernel launch %d\n", launch);
        CALL(cudaDeviceSynchronize());
    }
    CALL(cudaMemcpy(&host, device, sizeof(int), cudaMemcpyDeviceToHost));
    CALL(cudaFree(device));
    std::printf("Hello from CUDA: %d (expected 42)\n", host);
    return host == 42 ? 0 : 1;
}
