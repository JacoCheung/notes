// Linux teaching tracer: CUDA Toolkit / CUPTI 12.8, one controlled process.
// Callback logging is synchronous; do not use these timings as a benchmark.
#include <cupti.h>
#include <cupti_driver_cbid.h>
#include <cupti_runtime_cbid.h>
// cupti.h already includes generated_cuda{,_runtime_api}_meta.h in 12.8.
// These generated parameter headers do not have independent include guards.

#include <cinttypes>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <sys/syscall.h>
#include <unistd.h>

namespace {
CUpti_SubscriberHandle subscriber{};
FILE* output = nullptr;
std::mutex output_mutex;
char phase[64] = "INIT";
bool active = false;
bool io_failed = false;

struct Fields {
    uint64_t bytes = 0, address = 0, handle = 0, offset = 0;
    bool has_bytes = false, has_address = false, has_handle = false;
    bool has_offset = false;
};

// Decode inputs at EXIT. Read output pointers ONLY after successful return.
Fields decode(CUpti_CallbackDomain domain, CUpti_CallbackId id,
              const void* params, bool success) {
    Fields f;
    if (domain == CUPTI_CB_DOMAIN_RUNTIME_API) {
        if (id == CUPTI_RUNTIME_TRACE_CBID_cudaMalloc_v3020) {
            const auto* p = static_cast<const cudaMalloc_v3020_params*>(params);
            f.bytes = p->size; f.has_bytes = true;
            if (success && p->devPtr) {
                f.address = reinterpret_cast<uintptr_t>(*p->devPtr);
                f.has_address = true;
            }
        } else if (id == CUPTI_RUNTIME_TRACE_CBID_cudaFree_v3020) {
            const auto* p = static_cast<const cudaFree_v3020_params*>(params);
            f.address = reinterpret_cast<uintptr_t>(p->devPtr);
            f.has_address = true;
        }
        return f;
    }
    switch (id) {
    case CUPTI_DRIVER_TRACE_CBID_cuMemAddressReserve: {
        const auto* p = static_cast<const cuMemAddressReserve_params*>(params);
        f.bytes = p->size; f.has_bytes = true;
        if (success && p->ptr) { f.address = *p->ptr; f.has_address = true; }
        break;
    }
    case CUPTI_DRIVER_TRACE_CBID_cuMemAddressFree: {
        const auto* p = static_cast<const cuMemAddressFree_params*>(params);
        f.bytes = p->size; f.address = p->ptr;
        f.has_bytes = f.has_address = true;
        break;
    }
    case CUPTI_DRIVER_TRACE_CBID_cuMemCreate: {
        const auto* p = static_cast<const cuMemCreate_params*>(params);
        f.bytes = p->size; f.has_bytes = true;
        if (success && p->handle) { f.handle = *p->handle; f.has_handle = true; }
        break;
    }
    case CUPTI_DRIVER_TRACE_CBID_cuMemRelease: {
        const auto* p = static_cast<const cuMemRelease_params*>(params);
        f.handle = p->handle; f.has_handle = true;
        break;
    }
    case CUPTI_DRIVER_TRACE_CBID_cuMemMap: {
        const auto* p = static_cast<const cuMemMap_params*>(params);
        f.address = p->ptr; f.bytes = p->size; f.handle = p->handle;
        f.offset = p->offset;
        f.has_address = f.has_bytes = f.has_handle = f.has_offset = true;
        break;
    }
    case CUPTI_DRIVER_TRACE_CBID_cuMemUnmap: {
        const auto* p = static_cast<const cuMemUnmap_params*>(params);
        f.address = p->ptr; f.bytes = p->size;
        f.has_address = f.has_bytes = true;
        break;
    }
    case CUPTI_DRIVER_TRACE_CBID_cuMemSetAccess: {
        const auto* p = static_cast<const cuMemSetAccess_params*>(params);
        f.address = p->ptr; f.bytes = p->size;
        f.has_address = f.has_bytes = true;
        break;
    }
    default: break;
    }
    return f;
}

uint64_t timestamp() {
    uint64_t value = 0;
    // A zero timestamp is retained as missing data, never a valid duration.
    if (cuptiGetTimestamp(&value) != CUPTI_SUCCESS) return 0;
    return value;
}

void CUPTIAPI callback(void*, CUpti_CallbackDomain domain,
                       CUpti_CallbackId id, const void* data) {
    if (domain != CUPTI_CB_DOMAIN_RUNTIME_API &&
        domain != CUPTI_CB_DOMAIN_DRIVER_API) return;
    const auto* info = static_cast<const CUpti_CallbackData*>(data);
    if (info->callbackSite == CUPTI_API_ENTER) {
        *info->correlationData = timestamp();
        return;
    }
    if (info->callbackSite != CUPTI_API_EXIT) return;
    const uint64_t end = timestamp();
    const uint64_t start = *info->correlationData;
    const int result = domain == CUPTI_CB_DOMAIN_RUNTIME_API
        ? static_cast<int>(*static_cast<const cudaError_t*>(info->functionReturnValue))
        : static_cast<int>(*static_cast<const CUresult*>(info->functionReturnValue));
    const Fields f = decode(domain, id, info->functionParams, result == 0);
    char bytes[32] = "", address[32] = "", handle[32] = "", offset[32] = "";
    if (f.has_bytes) std::snprintf(bytes, sizeof(bytes), "%" PRIu64, f.bytes);
    if (f.has_address) std::snprintf(address, sizeof(address), "0x%" PRIx64, f.address);
    if (f.has_handle) std::snprintf(handle, sizeof(handle), "0x%" PRIx64, f.handle);
    if (f.has_offset) std::snprintf(offset, sizeof(offset), "%" PRIu64, f.offset);
    std::lock_guard<std::mutex> lock(output_mutex);
    if (!output) return;
    const int written = std::fprintf(output,
        "api,%s,%ld,%ld,%s,%u,%u,%u,%s,%" PRIu64 ",%" PRIu64 ",%d,%s,%s,%s,%s\n",
        phase, static_cast<long>(getpid()), static_cast<long>(syscall(SYS_gettid)),
        domain == CUPTI_CB_DOMAIN_RUNTIME_API ? "runtime" : "driver",
        static_cast<unsigned>(id), info->correlationId, info->contextUid,
        info->functionName, start, end, result, bytes, address, handle, offset);
    if (written < 0) io_failed = true;
}

bool check(CUptiResult result, const char* operation) {
    if (result == CUPTI_SUCCESS) return true;
    const char* message = "unknown CUPTI error";
    cuptiGetResultString(result, &message);
    std::fprintf(stderr, "%s: %s (%d)\n", operation, message, static_cast<int>(result));
    return false;
}
}  // namespace

// Call start/mark/stop serially from the controlling Python thread.
// Before stop, all application threads must have left traced CUDA API calls.
extern "C" int trace_start(const char* path) {
    if (active || output || !path) return -1;
    output = std::fopen(path, "w");
    if (!output) { std::perror("open trace"); return -1; }
    io_failed = false;
    std::snprintf(phase, sizeof(phase), "INIT");
    std::fprintf(output, "kind,phase,pid,tid,domain,cbid,correlation_id,context_uid,api,start_ns,end_ns,result,bytes,address,handle,offset\n");
    if (!check(cuptiSubscribe(&subscriber, callback, nullptr), "cuptiSubscribe")) {
        std::fclose(output); output = nullptr; return -1;
    }
    active = true;
    struct Selection { CUpti_CallbackDomain domain; CUpti_CallbackId id; };
    const Selection selection[] = {
        {CUPTI_CB_DOMAIN_RUNTIME_API, CUPTI_RUNTIME_TRACE_CBID_cudaMalloc_v3020},
        {CUPTI_CB_DOMAIN_RUNTIME_API, CUPTI_RUNTIME_TRACE_CBID_cudaFree_v3020},
        {CUPTI_CB_DOMAIN_DRIVER_API, CUPTI_DRIVER_TRACE_CBID_cuMemAddressReserve},
        {CUPTI_CB_DOMAIN_DRIVER_API, CUPTI_DRIVER_TRACE_CBID_cuMemAddressFree},
        {CUPTI_CB_DOMAIN_DRIVER_API, CUPTI_DRIVER_TRACE_CBID_cuMemCreate},
        {CUPTI_CB_DOMAIN_DRIVER_API, CUPTI_DRIVER_TRACE_CBID_cuMemRelease},
        {CUPTI_CB_DOMAIN_DRIVER_API, CUPTI_DRIVER_TRACE_CBID_cuMemMap},
        {CUPTI_CB_DOMAIN_DRIVER_API, CUPTI_DRIVER_TRACE_CBID_cuMemUnmap},
        {CUPTI_CB_DOMAIN_DRIVER_API, CUPTI_DRIVER_TRACE_CBID_cuMemSetAccess},
    };
    for (const auto& item : selection) {
        if (!check(cuptiEnableCallback(1, subscriber, item.domain, item.id), "cuptiEnableCallback")) {
            if (check(cuptiUnsubscribe(subscriber), "cuptiUnsubscribe")) {
                active = false; std::fclose(output); output = nullptr;
            }
            return -1;
        }
    }
    return 0;
}

extern "C" int trace_mark(const char* name) {
    if (!active || !name || std::strlen(name) >= sizeof(phase)) return -1;
    // Keep CSV fields unquoted by restricting phase labels to safe characters.
    for (const char* p = name; *p; ++p) {
        if (!((*p >= 'A' && *p <= 'Z') || (*p >= '0' && *p <= '9') || *p == '_')) return -1;
    }
    const uint64_t now = timestamp();
    std::lock_guard<std::mutex> lock(output_mutex);
    std::snprintf(phase, sizeof(phase), "%s", name);
    if (std::fprintf(output, "phase,%s,%ld,%ld,host,,,,mark,%" PRIu64 ",%" PRIu64 ",0,,,,\n",
        phase, static_cast<long>(getpid()), static_cast<long>(syscall(SYS_gettid)), now, now) < 0) io_failed = true;
    return io_failed ? -1 : 0;
}

extern "C" int trace_stop() {
    if (!active) return -1;
    if (!check(cuptiUnsubscribe(subscriber), "cuptiUnsubscribe")) return -1;
    active = false;
    std::lock_guard<std::mutex> lock(output_mutex);
    const bool failed = io_failed || std::ferror(output);
    const int closed = std::fclose(output); output = nullptr;
    return failed || closed != 0 ? -1 : 0;
}
