#include "peer_load.cuh"

int main(int argc, char** argv) {
    if (argc != 3) {
        std::fprintf(stderr, "Usage: %s READER_GPU OWNER_GPU\n", argv[0]);
        return 2;
    }
    const int reader = device_arg(argv[1]), owner = device_arg(argv[2]);
    require_peer(reader, owner);

    // BEGIN same_process
    CUDA_CHECK(cudaSetDevice(owner));
    float* remote = nullptr;
    CUDA_CHECK(cudaMalloc(&remote, kBytes));
    initialize(remote); // Fills remote[i] = i, then waits for GPU owner.

    CUDA_CHECK(cudaSetDevice(reader));
    cudaError_t status = cudaDeviceEnablePeerAccess(owner, 0);
    bool enabled_here = status == cudaSuccess;
    if (status == cudaErrorPeerAccessAlreadyEnabled) {
        (void)cudaGetLastError(); // Clear the already-enabled status.
    } else {
        CUDA_CHECK(status);
    }

    float* local = nullptr;
    CUDA_CHECK(cudaMalloc(&local, kBytes));
    peer_load<<<(kCount + 255) / 256, 256>>>(remote, local, kCount);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize()); // Consumer finished using remote.
    verify(local);

    CUDA_CHECK(cudaFree(local));
    if (enabled_here) CUDA_CHECK(cudaDeviceDisablePeerAccess(owner));
    CUDA_CHECK(cudaSetDevice(owner));
    CUDA_CHECK(cudaFree(remote));
    // END same_process
}
