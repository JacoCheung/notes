#include "peer_load.cuh"
#include <cstdint>
#include <cstring>

static void io_check(bool ok, const char* message) {
    if (!ok) {
        std::fprintf(stderr, "%s\n", message);
        std::exit(1);
    }
}

// Pipes carry the opaque handle and completion acknowledgement, not GPU data.
static void send_handle(const cudaIpcMemHandle_t& handle) {
    uint32_t size = sizeof(handle);
    io_check(std::fwrite(&size, sizeof(size), 1, stdout) == 1, "Handle header write failed");
    io_check(std::fwrite(&handle, sizeof(handle), 1, stdout) == 1, "Handle write failed");
    io_check(std::fflush(stdout) == 0, "Handle flush failed");
}

static cudaIpcMemHandle_t receive_handle() {
    uint32_t size = 0;
    cudaIpcMemHandle_t handle{};
    io_check(std::fread(&size, sizeof(size), 1, stdin) == 1 && size == sizeof(handle),
             "Invalid handle header");
    io_check(std::fread(&handle, sizeof(handle), 1, stdin) == 1, "Handle read failed");
    return handle;
}

static void export_memory(int owner) {
    // BEGIN ipc_owner
    CUDA_CHECK(cudaSetDevice(owner));
    float* allocation = nullptr;
    CUDA_CHECK(cudaMalloc(&allocation, kBytes));
    initialize(allocation); // GPU writes complete before the handle is sent.
    cudaIpcMemHandle_t handle{};
    CUDA_CHECK(cudaIpcGetMemHandle(&handle, allocation));
    send_handle(handle);

    // Launcher sends this only after the reader has synchronized and closed.
    io_check(std::fgetc(stdin) == 'K', "Reader did not acknowledge completion");
    CUDA_CHECK(cudaFree(allocation));
    // END ipc_owner
}

static void import_and_read(int reader, int owner) {
    require_peer(reader, owner);
    // BEGIN ipc_reader
    CUDA_CHECK(cudaSetDevice(reader));
    cudaIpcMemHandle_t handle = receive_handle();
    float* imported = nullptr;
    CUDA_CHECK(cudaIpcOpenMemHandle(reinterpret_cast<void**>(&imported), handle,
                                   cudaIpcMemLazyEnablePeerAccess));
    float* local = nullptr;
    CUDA_CHECK(cudaMalloc(&local, kBytes));
    peer_load<<<(kCount + 255) / 256, 256>>>(imported, local, kCount);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());
    verify(local);
    CUDA_CHECK(cudaFree(local));
    CUDA_CHECK(cudaIpcCloseMemHandle(imported));
    // END ipc_reader
}

int main(int argc, char** argv) {
    if (argc != 4 || (std::strcmp(argv[1], "owner") && std::strcmp(argv[1], "reader"))) {
        std::fprintf(stderr, "Usage: %s owner|reader READER_GPU OWNER_GPU\n", argv[0]);
        return 2;
    }
    const int reader = device_arg(argv[2]), owner = device_arg(argv[3]);
    if (!std::strcmp(argv[1], "owner")) export_memory(owner);
    else import_and_read(reader, owner);
}
