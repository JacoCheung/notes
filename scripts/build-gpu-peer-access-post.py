#!/usr/bin/env python3
"""Build the bilingual GPU P2P article from its downloadable CUDA examples."""
from html import escape
from pathlib import Path
from post_series import render_series_nav
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/inside-cuda/gpu-peer-access'
NCCL = 'https://github.com/NVIDIA/nccl/blob/12df1a11afad322be5a204a2db890161cbf8131d/'
DRIVER = 'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/e6a2e01579fbbd1ca2ed43fef2ee2589e9bd8bd9/'
DOC = 'https://docs.nvidia.com/cuda/archive/12.4.1/'
LINKS = {
    'peer': DOC + 'cuda-runtime-api/group__CUDART__PEER.html',
    'ipc': DOC + 'cuda-runtime-api/group__CUDART__DEVICE.html',
    'guide': DOC + 'cuda-c-programming-guide/index.html#peer-to-peer-memory-access',
    'uva': DOC + 'cuda-c-programming-guide/index.html#unified-virtual-address-space',
    'events': DOC + 'cuda-c-programming-guide/index.html#stream-and-event-behavior',
    'ptx': DOC + 'parallel-thread-execution/index.html#data-movement-and-conversion-instructions-ld',
    'vmm': DOC + 'cuda-driver-api/group__CUDA__VA.html',
    'fabric_memory': 'https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/virtual-memory-management.html#unicast-memory-sharing',
    'imex': 'https://docs.nvidia.com/multi-node-nvlink-systems/imex-guide/overview.html#the-nvidia-import-export-service-for-internode-memory-sharing',
    'imex_channels': 'https://docs.nvidia.com/multi-node-nvlink-systems/imex-guide/imexchannels.html',
    'pdf': 'https://nvidia.github.io/open-gpu-doc/pascal/gp100-mmu-format.pdf',
    'pte': DRIVER + 'src/common/inc/swref/published/pascal/gp100/dev_mmu.h#L120-L156',
    'peer_id': DRIVER + 'src/nvidia/src/kernel/gpu/bus/arch/pascal/kern_bus_gp100.c#L812-L890',
    'route': DRIVER + 'src/nvidia/src/kernel/gpu/bus/arch/pascal/kern_bus_gp100.c#L336-L405',
    'lsa_usage': 'https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/deviceapi.html',
    'lsa_setup': 'https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/api/device_setup.html',
    'lsa_memory': 'https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/api/device_memory.html',
    'lsa_window': 'https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/bufferreg.html#window-registration',
    'lsa_comms': 'https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/api/comms.html#ncclcommwindowregister',
    'lsa_example': NCCL + 'docs/examples/06_device_api/01_allreduce_lsa/c/main.cu',
    'lsa_example_host': NCCL + 'docs/examples/06_device_api/01_allreduce_lsa/c/main.cu#L131-L215',
    'lsa_example_kernel': NCCL + 'docs/examples/06_device_api/01_allreduce_lsa/c/main.cu#L62-L98',
    'lsa_pointer_source': NCCL + 'src/include/nccl_device/impl/core__funcs.h#L145-L152',
    'lsa_barrier_source': NCCL + 'src/include/nccl_device/impl/lsa_barrier__funcs.h#L49-L177',
    'pascal': 'https://docs.nvidia.com/cuda/pascal-tuning-guide/index.html#nvlink-interconnect',
    'fabric': 'https://docs.nvidia.com/datacenter/tesla/fabric-manager-user-guide/index.html#nvswitch-core-software-stack',
    'smi': 'https://docs.nvidia.com/deploy/nvidia-smi/',
    'multi_gpu': 'https://docs.nvidia.com/cuda/cuda-programming-guide/03-advanced/multi-gpu-systems.html',
}


HOST_SNIPPETS = {
    'same_process': '''
        cudaSetDevice(1);  // Owner
        float* remote;
        cudaMalloc(&remote, bytes);

        cudaSetDevice(0);  // Reader
        cudaDeviceEnablePeerAccess(1, 0);
        float* local;
        cudaMalloc(&local, bytes);

        peer_load<<<(n + 255) / 256, 256>>>(remote, local, n);
    ''',
    'ipc_owner': '''
        cudaSetDevice(1);
        float* allocation;
        cudaMalloc(&allocation, bytes);

        cudaIpcMemHandle_t handle;
        cudaIpcGetMemHandle(
            &handle, allocation);
        send_handle(handle);
    ''',
    'ipc_reader': '''
        cudaSetDevice(0);
        auto handle = receive_handle();
        void* mapping;
        cudaIpcOpenMemHandle(
            &mapping, handle,
            cudaIpcMemLazyEnablePeerAccess);

        float* local;
        cudaMalloc(&local, bytes);
        peer_load<<<(n + 255) / 256, 256>>>(
            static_cast<float*>(mapping),
            local, n);
    ''',
    'fabric_owner': '''
        CUmemAllocationProp prop{};
        prop.type = CU_MEM_ALLOCATION_TYPE_PINNED;
        prop.location = {
            CU_MEM_LOCATION_TYPE_DEVICE,
            ownerDevice};
        prop.requestedHandleTypes =
            CU_MEM_HANDLE_TYPE_FABRIC;

        CUmemGenericAllocationHandle alloc;
        cuMemCreate(&alloc, bytes, &prop, 0);

        CUmemFabricHandle fabric;
        cuMemExportToShareableHandle(
            &fabric, alloc,
            CU_MEM_HANDLE_TYPE_FABRIC, 0);
        send_fabric(fabric, bytes);
    ''',
    'fabric_reader': '''
        CUmemFabricHandle fabric;
        size_t bytes;
        receive_fabric(fabric, bytes);

        CUmemGenericAllocationHandle imported;
        cuMemImportFromShareableHandle(
            &imported, &fabric,
            CU_MEM_HANDLE_TYPE_FABRIC);

        CUdeviceptr peerVA;
        cuMemAddressReserve(
            &peerVA, bytes, 0, 0, 0);
        cuMemMap(peerVA, bytes, 0, imported, 0);
        CUmemAccessDesc access{};
        access.location = {
            CU_MEM_LOCATION_TYPE_DEVICE,
            readerDevice};
        access.flags =
            CU_MEM_ACCESS_FLAGS_PROT_READ;
        cuMemSetAccess(peerVA, bytes, &access, 1);

        auto src =
            reinterpret_cast<const float*>(
                peerVA);
        peer_load<<<(n + 255) / 256, 256>>>(
            src, local, n);
    ''',
}


LSA_SNIPPETS = {
    'lsa_query': '''
        #include <nccl.h>
        #include <nccl_device.h>

        cudaSetDevice(localDevice);
        ncclComm_t comm;
        ncclCommInitRank(&comm, 2, id, rank);

        ncclCommProperties_t props = NCCL_COMM_PROPERTIES_INITIALIZER;
        ncclCommQueryProperties(comm, &props);
        // Required: props.deviceApiSupport && props.nLsaTeams == 1
    ''',
    'lsa_window_code': '''
        size_t bytes = count * sizeof(float);
        void* input;
        ncclMemAlloc(&input, bytes);

        ncclWindow_t win;
        ncclCommWindowRegister(
            comm, input, bytes, &win, NCCL_WIN_COLL_SYMMETRIC);

        float* output;
        cudaMalloc(&output, bytes);  // Used only by this GPU
    ''',
    'lsa_comm_code': '''
        constexpr int nCTAs = 4;
        constexpr int nThreads = 256;
        ncclDevCommRequirements reqs = NCCL_DEV_COMM_REQUIREMENTS_INITIALIZER;
        reqs.lsaBarrierCount = nCTAs;

        ncclDevComm devComm;
        ncclDevCommCreate(comm, &reqs, &devComm);
    ''',
    'lsa_kernel': '''
        __global__ void lsa_peer_load(
            ncclDevComm devComm, ncclWindow_t win,
            float* output, size_t count) {
            ncclLsaBarrierSession<ncclCoopCta> bar{
                ncclCoopCta(), devComm, ncclTeamTagLsa(), blockIdx.x};
            bar.sync(ncclCoopCta(), cuda::memory_order_acquire);

            int peer = (devComm.lsaRank + 1) % devComm.lsaSize;
            const float* src = static_cast<const float*>(
                ncclGetLsaPointer(win, 0, peer));

            for (size_t i = blockIdx.x * blockDim.x + threadIdx.x;
                 i < count; i += blockDim.x * gridDim.x) {
                output[i] = src[i] + 1.0f;
            }

            bar.sync(ncclCoopCta(), cuda::memory_order_release);
        }
    ''',
    'lsa_launch': '''
        lsa_peer_load<<<nCTAs, nThreads, 0, stream>>>(
            devComm, win, output, count);
    ''',
    'lsa_cleanup': '''
        // After all kernels using these resources have completed:
        ncclDevCommDestroy(comm, &devComm);
        ncclCommWindowDeregister(comm, win);
        ncclMemFree(input);
        cudaFree(output);
        ncclCommDestroy(comm);
    ''',
}


def snippet(source):
    return '<pre class="code" data-language="cpp"><code>' + escape(textwrap.dedent(source).strip()) + '</code></pre>'


def code(filename, marker):
    source = (ASSETS / filename).read_text()
    match = re.search(r'^[ \t]*// BEGIN ' + marker + r'\n(.*?)^[ \t]*// END ' + marker,
                      source, re.M | re.S)
    if not match:
        raise ValueError((filename, marker))
    return snippet(match[1])


def ipc_columns(lang, fabric=False):
    zh = lang == 'zh'
    panels = []
    entries = [
        ('Owner · Node A', 'fabric_owner', '分配并导出' if zh else 'Allocate and export'),
        ('Reader · Node B', 'fabric_reader', '导入并读取' if zh else 'Import and read'),
    ] if fabric else [
        ('Owner · GPU 1', 'ipc_owner', '分配并导出' if zh else 'Allocate and export'),
        ('Reader · GPU 0', 'ipc_reader', '导入并读取' if zh else 'Import and read'),
    ]
    for role, marker, description in entries:
        title_id = f'{lang}-{marker}-title'
        panels.append(f'<section class="p2p-code-panel" aria-labelledby="{title_id}">'
                      f'<div class="p2p-code-heading" id="{title_id}"><span>{role}</span>'
                      f'<small>{description}</small></div>{snippet(HOST_SNIPPETS[marker])}</section>')
    return '<div class="p2p-code-scroll" tabindex="0" role="region" aria-label="' + (
        'Owner 与 Reader 关键代码，可横向滚动' if zh else 'Owner and reader essentials; scroll horizontally'
    ) + '"><div class="p2p-code-columns">' + ''.join(panels) + '</div></div>'


def svg_start(name, height, title):
    return [f'<svg viewBox="0 0 920 {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{name}"><title id="{name}">{escape(title)}</title>',
            f'<defs><marker id="{name}-tip" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 Z" fill="var(--p2p-line)"/></marker></defs>']


def label(x, y, text, size=16, anchor='middle'):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}">{escape(text)}</text>'


def box(x, y, width, title, subtitle='', remote=False):
    parts = [f'<rect x="{x}" y="{y}" width="{width}" height="66" rx="3" fill="var(--p2p-remote)" stroke="var(--p2p-peer)" stroke-width="2"/>' if remote else
             f'<rect x="{x}" y="{y}" width="{width}" height="66" rx="3" fill="var(--p2p-fill)" stroke="var(--p2p-line)" stroke-width="2"/>',
             label(x+width/2, y+27, title, 18)]
    if subtitle: parts.append(label(x+width/2, y+50, subtitle, 14))
    return ''.join(parts)


def arrow(name, x1, x2, y, text, dashed=False, href=None, label_x=None):
    content = f'<path d="M{x1} {y} H{x2}" fill="none" stroke="var(--p2p-line)" stroke-width="2"' + (' stroke-dasharray="6 4"' if dashed else '') + f' marker-end="url(#{name}-tip)"/>' + label(label_x if label_x is not None else (x1+x2)/2, y-13, text)
    return f'<a href="{href}" target="_blank" rel="noopener">{content}</a>' if href else content


def pte_diagram(lang, name, title):
    zh = lang == 'zh'
    parts = svg_start(name, 560, title)
    parts.append(label(28, 28, '64-bit PTE · Aperture = peer', 20, 'start'))

    def field(x, y, width, height, text, fill, stroke='var(--p2p-line)', size=17):
        return (f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1.7"/>'
                + label(x+width/2, y+height/2+6, text, size))

    # 64 bits at 13.5 px each. Bit 63 is on the left, bit 0 on the right.
    for high, low, text, fill, stroke, size in [
        (63, 36, '其他字段' if zh else 'Other fields', 'var(--bg-subtle)', 'var(--p2p-line)', 17),
        (35, 33, 'ID', 'var(--p2p-remote)', 'var(--p2p-peer)', 14),
        (32, 8, 'Peer PA[36:12]', 'var(--p2p-fill)', 'var(--p2p-line)', 18),
        (7, 0, '控制位' if zh else 'Control', 'var(--p2p-control)', 'var(--p2p-line)', 17),
    ]:
        x, width = 28+(63-high)*13.5, (high-low+1)*13.5
        parts.append(label(x+width/2, 62, f'{high}:{low}', 14))
        parts.append(f'<a href="{LINKS["pte"]}" target="_blank" rel="noopener">'
                     + field(x, 74, width, 64, text, fill, stroke, size) + '</a>')
    parts.append('<path d="M426.25 138 V158 H168 V178 M615.25 138 V178" '
                 'fill="none" stroke="var(--p2p-line)" stroke-width="1.7"/>')
    parts.append('<rect x="28" y="178" width="280" height="82" rx="3" '
                 'fill="var(--p2p-remote)" stroke="var(--p2p-peer)" stroke-width="1.7"/>')
    parts.append('<rect x="340" y="178" width="552" height="82" rx="3" '
                 'fill="var(--p2p-fill)" stroke="var(--p2p-line)" stroke-width="1.7"/>')
    parts += [label(44, 204, 'Peer ID · PTE[35:33]', 18, 'start'),
              label(44, 227, '目标 peer 编号' if zh else 'Target peer slot', 16, 'start'),
              label(44, 249, '与 PA[39:37] 复用' if zh else 'Shares bits with PA[39:37]', 15, 'start'),
              label(356, 204, '页基址 · PTE[32:8]' if zh else 'Page base · PTE[32:8]', 18, 'start'),
              label(356, 229, '编码 PA[36:12]' if zh else 'Encodes PA[36:12]', 16, 'start'),
              label(356, 250, '4 KiB 页内偏移由 VA[11:0] 提供' if zh else 'VA[11:0] supplies the offset within a 4 KiB page', 16, 'start'),
              label(28, 294, '控制位放大 · PTE[7:0]' if zh else 'Control bits expanded · PTE[7:0]', 20, 'start')]
    for high, low, text, fill in [
        (7, 7, 'AD', 'var(--p2p-control)'),
        (6, 6, 'RO', 'var(--p2p-control)'),
        (5, 3, '其他控制位' if zh else 'Other controls', 'var(--bg-subtle)'),
        (2, 1, 'Aperture', 'var(--p2p-remote)'),
        (0, 0, 'V', 'var(--p2p-fill)'),
    ]:
        x, width = 28+(7-high)*108, (high-low+1)*108
        parts.append(label(x+width/2, 318, str(high) if high == low else f'{high}:{low}', 14))
        parts.append(f'<a href="{LINKS["pte"]}" target="_blank" rel="noopener">'
                     + field(x, 330, width, 62, text, fill) + '</a>')
    parts += [label(28, 424, 'AD=1：禁止原子访问' if zh else 'AD=1: atomics disabled', 18, 'start'),
              label(340, 424, 'RO=1：只读' if zh else 'RO=1: read-only', 18, 'start'),
              label(620, 424, 'V=1：条目有效' if zh else 'V=1: valid entry', 18, 'start'),
              label(28, 464, 'Aperture · 目标地址空间' if zh else 'Aperture · target address space', 20, 'start')]
    for i, (bits, target) in enumerate([
        ('00', '本地显存' if zh else 'Local video memory'),
        ('01', 'Peer 显存' if zh else 'Peer video memory'),
        ('10', 'Coherent system memory'),
        ('11', 'Non-coherent system memory'),
    ]):
        x = 28+i*216
        parts.append(f'<rect x="{x}" y="480" width="216" height="62" '
                     f'fill="{"var(--p2p-remote)" if i == 1 else "var(--bg-subtle)"}" '
                     'stroke="var(--p2p-line)" stroke-width="1.7"/>')
        parts += [label(x+108, 505, bits, 19), label(x+108, 529, target, 14)]
    return parts


def figure(lang, kind):
    zh = lang == 'zh'
    name = f'{lang}-p2p-{kind}'
    if kind == 'mapping':
        title = '两个进程的映射，同一块显存' if zh else 'Two process mappings, one allocation'
        parts = svg_start(name, 366, title)
        for x, process, gpu, pointer in [(25, 'A', 1, 'pA = X'), (535, 'B', 0, 'pB = Y')]:
            parts.append(f'<rect x="{x}" y="22" width="360" height="114" rx="3" '
                         'fill="var(--p2p-fill)" stroke="var(--p2p-line)" stroke-width="2"/>')
            parts += [label(x+180, 51, f'进程 {process} 的 GPU 地址空间' if zh else
                            f'Process {process} · GPU address space', 18),
                      label(x+180, 78, f'{"Owner" if process == "A" else "Reader"} · GPU {gpu}', 14),
                      label(x+180, 112, pointer, 22)]
        parts.append('<path d="M205 136 V222 H715 V136" '
                     'fill="none" stroke="var(--p2p-line)" stroke-width="2"/>')
        parts.append('<path d="M460 222 V274" fill="none" stroke="var(--p2p-line)" '
                     f'stroke-width="2" marker-end="url(#{name}-tip)"/>')
        parts += [label(225, 180, 'A 的映射' if zh else 'Mapping in A', 18, 'start'),
                  label(695, 180, 'B 的映射' if zh else 'Mapping in B', 18, 'end'),
                  box(305, 274, 310, '同一块物理显存' if zh else 'Same physical allocation',
                      '位于 GPU 1' if zh else 'Located on GPU 1', remote=True)]
        caption = ('pA 与 pB 都映射到 GPU 1 的同一分配；虚拟地址 X 与 Y 的数值可以不同。'
                   if zh else 'pA and pB map to the same allocation on GPU 1. Virtual addresses X and Y may differ.')
    elif kind == 'pte':
        title = 'GP100 VER2 PTE：目标与权限' if zh else 'GP100 VER2 PTE: target and permissions'
        parts = pte_diagram(lang, name, title)
        caption = ('位号从高到低排列。灰色区域包含本图省略的其他字段；Peer ID 的解释适用于 Aperture=peer。'
                   if zh else 'Bits run from high to low. Gray regions contain other fields omitted here. Peer ID applies when aperture=peer.')
    else:
        title = 'Peer 访问的三种物理路径' if zh else 'Three physical paths for peer access'
        parts = svg_start(name, 430, title)
        routes = [('PCIe', 'PCIe fabric', 'switch / root complex'), ('NVLink', 'NVLink', 'direct link'), ('NVSwitch', 'NVSwitch', 'NVLink switching fabric')]
        for i,(kind,mid,sub) in enumerate(routes):
            y = 48+i*130
            parts += [label(25,y-13,kind,18,'start'), box(25,y,180,'GPU 0','load issuer'),box(340,y,240,mid,sub,True),box(715,y,180,'GPU 1','peer memory'),
                      arrow(name,208,337,y+34,'request'),arrow(name,583,712,y+34,'request')]
        caption = '箭头表示请求方向，数据沿可用的互联路径返回。PCIe 的具体经过点取决于拓扑；NVSwitch 转发 NVLink 流量。三行是不同系统配置。' if zh else 'Arrows show requests; data returns over the available interconnect. PCIe traversal depends on topology. NVSwitch forwards NVLink traffic. The rows represent different system configurations.'
    parts.append('</svg>')
    return f'<figure class="p2p-figure"><div class="p2p-toolbar"><span>{title}</span><span><button type="button" data-size="fit" aria-pressed="true">{"适宽" if zh else "Fit width"}</button> <button type="button" data-size="actual" aria-pressed="false">{"原尺寸" if zh else "Actual size"}</button></span></div><div class="p2p-viewport">' + ''.join(parts) + f'</div><figcaption>{caption}</figcaption></figure>'


def lab(lang):
    zh = lang == 'zh'
    peer_options = ''.join(f'<option value="{i}"' + (' selected' if i == 3 else '') + f'>{i}</option>' for i in range(8))
    return f'''<div class="p2p-lab" data-lang="{lang}">
<div class="p2p-lab-controls"><label>Aperture<select data-aperture><option value="peer">01 · peer</option><option value="local">00 · local</option></select></label>
<label>Peer ID<select data-peer>{peer_options}</select></label><label>{'页内偏移' if zh else 'Page offset'}<input data-offset type="number" min="0" max="4095" step="1" value="128"></label></div>
<div class="p2p-lab-fields"><div><small>PTE[35:33]</small><strong data-peer-value>011 · ID 3</strong></div><div><small>PTE[32:8] = PA[36:12]</small><strong data-pa-value>0x12345</strong></div><div><small>PTE[2:1]</small><strong data-aperture-value>01 · peer</strong></div></div>
<p class="p2p-word" data-pte>PTE = 0x0000000601234503</p><p data-route aria-live="polite"></p>
<p>{'4 KiB 页，页基址固定为 0x12345000，Valid=1，其余展示外字段设为 0。这里只计算教学用位模式，不读取或修改 GPU 页表。' if zh else 'A 4 KiB page at base 0x12345000, with Valid=1 and other unshown fields zero. This computes an illustrative bit pattern; it does not access GPU page tables.'}</p></div>'''


ZH = r'''
<h1>GPU P2P 显存访问</h1>
<p>GPU P2P（Peer-to-Peer）让一张 GPU 的 kernel 通过有效映射，直接读写另一张 GPU 的显存。源数据可以留在原来的 GPU 上，消费者使用普通指针访问它，省去经 CPU 内存中转的数据拷贝。这条路径贯穿 CUDA 的访问授权、GPU 地址转换、NCCL Device API，以及 NVLink／PCIe 互联：驱动建立映射，GPU 硬件执行访问，通信库提供 peer 指针与同步接口。</p>
<aside class="p2p-note"><p>同进程与节点内 IPC 示例采用 Linux 64 位、同一主机内两张支持 P2P 的 GPU 与 cudaMalloc 分配；跨节点示例采用 VMM fabric handle。P100 的 GP100 页表格式用于说明地址转换；NCCL LSA 示例采用 2.32.3（12df1a11afad）的接口、ncclMemAlloc 分配和支持 Device API 的设备。</p></aside>

<p>在 PyTorch 中建立同类 peer 映射并编写计算 kernel，可接着阅读<a href="pytorch-symmetric-memory.html#zh-internals">《PyTorch 对称内存与 GPU P2P 访问》第三章</a>：其中逐项对照本章的 CUDA IPC、VMM 与 fabric handle，并给出双卡 Triton 和 MegaMoE 场景。</p>

<h2 id="zh-kernel">1. Kernel 与访问映射</h2>
<h3 id="zh-load">同一条 load</h3>
<p>设 GPU 1 持有输入，GPU 0 执行计算。下面的 kernel 将输入加一后写入 GPU 0 的本地输出。<code>src</code> 可以指向本地显存，也可以指向已映射、已授权的 peer 显存：</p>
@@kernel@@
<p>Kernel 程序员写的仍是 <code>src[i]</code>。同一个已编译 kernel 可以接收这两种地址，指令本身不携带“GPU 1”这样的 CUDA 设备编号。以本文源文件和 CUDA 12.4.131、<code>-O3 -arch=sm_60</code> 的实际编译结果为例：</p>
<pre class="code"><code>// PTX: src[i] and the result store
ld.global.f32  %f1, [%rd5];
add.f32        %f2, %f1, 0f3F800000;
st.global.f32  [%rd7], %f2;

// SASS: the source read
LDG.E R2, [R2];</code></pre>
<p>这次全局读取的目标由地址翻译与硬件路由决定，kernel 使用普通 load 即可完成 peer 读取。数据宽度、向量化或缓存提示变化时，编译器也可能选择其他 load 形式。<a href="@@ptx@@">PTX 的 ld 指令</a> · <a href="@@guide@@">CUDA peer memory access</a></p>

<h3 id="zh-single-process">同进程映射</h3>
<p>访问方向写作 <strong>reader → owner</strong>：GPU 0 读取 GPU 1，查询就是 <code>cudaDeviceCanAccessPeer(&amp;ok, 0, 1)</code>。查询成功后，在 GPU 0 为当前设备时调用 <code>cudaDeviceEnablePeerAccess(1, 0)</code>。第二个参数是保留 flags，必须为 0。授权是单向的；反向访问需要单独开启。<a href="@@peer@@">Peer access API</a></p>
<p>以下片段假设 P2P 能力查询已通过，<code>n</code> 为元素数，<code>bytes = n * sizeof(float)</code>。正文保留关键调用，初始化、错误处理、同步和释放见<a href="#zh-build">完整示例</a>。</p>
@@same_process@@
<p>同一进程的 UVA 让这个分配使用的指针值可直接传给另一张 GPU 的 kernel。UVA 提供统一的虚拟地址组织；P2P 授权提供实际访问能力。示例的 remote 分配始终位于 owner GPU，未使用 Unified Memory 的迁移机制。<a href="@@guide@@">统一地址与 peer 访问</a></p>

<h3 id="zh-ipc">节点内跨进程映射</h3>
<p>UVA 统一的是单个进程内的虚拟地址空间。跨进程时，各进程的 GPU 虚拟地址空间和页表映射各自独立，需要以 CUDA IPC 句柄为中介，将 peer 的显存分配映射到本进程的地址空间。Owner 将分配导出为 <code>cudaIpcMemHandle_t</code>，经普通 OS IPC 传给 Reader；Reader 导入后得到本进程可用的指针。两个指针通过各自的映射访问同一块物理显存。<a href="@@uva@@">UVA</a> · <a href="@@ipc@@">CUDA IPC</a></p>
@@figure:mapping@@
<div class="p2p-table"><table><thead><tr><th>步骤</th><th>同进程、两张 GPU</th><th>两个进程、两张 GPU</th></tr></thead><tbody>
<tr><td>共享对象</td><td>同进程中的 cudaMalloc 分配</td><td>Owner 导出的分配句柄</td></tr>
<tr><td>建立访问</td><td>Reader 开启对 Owner 的 peer access</td><td>Reader 在当前设备上导入 IPC 句柄</td></tr>
<tr><td>Kernel 指针</td><td>原分配的 UVA 指针</td><td>cudaIpcOpenMemHandle 返回的本地有效指针</td></tr>
<tr><td>结束访问</td><td>等待 kernel；必要时关闭 peer access</td><td>等待 kernel；cudaIpcCloseMemHandle</td></tr>
<tr><td>释放分配</td><td>Owner 在使用结束后 cudaFree</td><td>Owner 收到导入方已关闭映射的通知后 cudaFree</td></tr>
</tbody></table></div>
<p><code>send_handle</code> 和 <code>receive_handle</code> 是示例自定义的 CPU 进程间通信函数。<code>send_handle</code> 将句柄长度和 <code>cudaIpcMemHandle_t</code> 的原始字节写入标准输出；<code>run_ipc.py</code> 经管道转交给 Reader 的标准输入，再由 <code>receive_handle</code> 读回句柄。管道传递的是分配句柄，显存数据由 <code>peer_load</code> 通过 GPU 互联读取。</p>
@@ipc_columns@@
<p>Reader 调用 <code>cudaIpcOpenMemHandle</code> 建立映射；<code>cudaIpcMemLazyEnablePeerAccess</code> 允许导入操作按需尝试开启设备间访问。使用完成后，Reader 用 <code>cudaIpcCloseMemHandle</code> 关闭映射，Owner 负责释放分配。<a href="@@ipc@@">IPC 导入、地址与生命周期约束</a></p>

<h3 id="zh-fabric-mapping">跨节点映射</h3>
<p>跨节点时，各节点有独立的 OS、驱动实例和进程地址空间，共享分配需要跨越这些边界识别。<code>cudaIpcMemHandle_t</code> 用于同一节点内的进程间共享；在支持 Multi-Node NVLink 的系统中，VMM 使用 <code>CU_MEM_HANDLE_TYPE_FABRIC</code> 导出 <code>CUmemFabricHandle</code>，让另一节点的驱动导入同一块物理显存，并将它映射到接收进程的 GPU 虚拟地址空间。<a href="@@multi_gpu@@">多节点 CUDA 编程模型</a> · <a href="@@fabric_memory@@">VMM fabric handle</a></p>
<p>这条路径要求 GPU 位于可互访的 NVLink fabric 内，节点已配置同一 IMEX domain，导出与导入进程有权使用同一 IMEX channel。IMEX 服务负责跨 OS 协调内存导入、导出及生命周期；驱动建立映射后，GPU 的 load／store 经 NVLink fabric 访问远端显存。<a href="@@imex@@">IMEX 的职责</a> · <a href="@@imex_channels@@">IMEX channel 与访问权限</a></p>
<p>下面保留导出与导入的关键调用，使用 CUDA 12.4 起提供的 fabric handle。两端已初始化各自的 CUDA context，并确认 <code>CU_DEVICE_ATTRIBUTE_HANDLE_TYPE_FABRIC_SUPPORTED</code>。<code>ownerDevice</code> 与 <code>readerDevice</code> 分别是各自节点上的本地设备编号；<code>bytes</code> 按 <code>cuMemGetAllocationGranularity</code> 查询的分配粒度对齐。Reader 的 <code>local</code> 是预先分配的本地输出，<code>n</code> 是双方约定的 float 元素数。</p>
@@fabric_columns@@
<p><code>send_fabric</code>／<code>receive_fabric</code> 表示应用自定义的 CPU 通信：用 TCP socket 或 MPI 传递 <code>CUmemFabricHandle</code> 的字节和分配大小。Owner 的 <code>alloc</code> 与 Reader 的 <code>imported</code> 是各自进程中的 VMM allocation handle；<code>peerVA</code> 才是 Reader 保留并映射后供 kernel 使用的地址。<code>cuMemSetAccess</code> 为本地 Reader GPU 授予读权限。<a href="@@vmm@@">导出、导入、映射与权限 API</a></p>
<p>Owner 初始化数据时，也需为 <code>alloc</code> 保留地址、建立映射并授予本地写权限。初始化完成后通知 Reader 就绪，再执行读取；使用结束后，两端等待相关 GPU 操作完成，依次解除各自的映射、释放地址区间和 allocation handle（<code>cuMemUnmap</code>、<code>cuMemAddressFree</code>、<code>cuMemRelease</code>）。句柄传递只完成共享分配的建立，数据就绪与使用结束仍由应用协调。<a href="@@vmm@@">VMM 资源生命周期</a></p>

<h3 id="zh-ordering">同步与权限</h3>
<p>映射建立后，程序仍需保证生产者和消费者的执行顺序。可下载的完整示例使用 host 等待：Owner 初始化完成后发布句柄，Reader 的 kernel 完成并关闭映射后发送 ACK，Owner 收到 ACK 后才能安全复用或释放源内存。同进程也可以用跨设备的 <code>cudaStreamWaitEvent</code> 建立 GPU 依赖；节点内跨进程可使用可导出的 CUDA event。<a href="@@events@@">跨设备 event 等待</a> · <a href="@@ipc@@">IPC event</a></p>
<p>访问授权随分配方式变化：<code>cudaMalloc</code> 的 peer access 由设备间授权或 legacy IPC 导入建立；VMM 分配通过 <code>cuMemSetAccess</code> 授予指定设备访问权；stream-ordered memory pool 也有单独的访问配置。可访问性、读写权限和执行顺序需要分别满足。<a href="@@vmm@@">VMM 接口</a> · <a href="https://docs.nvidia.com/cuda/archive/12.4.1/cuda-runtime-api/group__CUDART__MEMORY__POOLS.html">Memory pool 访问接口</a></p>

<h2 id="zh-pte">2. P100 的地址转换</h2>
<h3 id="zh-control-data">驱动配置与硬件执行</h3>
<p>驱动在映射建立阶段验证目标分配与访问能力，建立虚拟地址到目标内存的映射，并维护 peer 关系、权限与生命周期。<code>cudaDeviceEnablePeerAccess</code>、IPC 导入和 VMM 是不同的 API 入口，具体调用链取决于驱动实现。</p>
<p>映射有效后，SM 发出 global load。GPU 的地址转换硬件使用 TLB 中的翻译结果，或在缺失时查页表，得到目标地址及其属性；互联硬件据此处理 peer 请求并返回数据。正常的已映射访问无需 CPU 驱动逐条介入。结合公开 PTE 格式，可以将这条路径概括为：</p>
<pre class="code">CPU / driver: allocation → peer mapping + access permissions
                                    ↓
GPU SM: load VA → address translation → aperture + target address
                                       ├─ local → local memory path
                                       └─ peer  → peer route → remote memory</pre>
<p>这是 API 语义与硬件格式支持的机制解释，省略了具体缓存、请求合并和互联内部流水级。下面的 GP100 字段给出了“local 或 peer”如何进入地址翻译结果的公开证据。<a href="@@pdf@@">Pascal MMU Format Changes，第 4 页</a></p>

<h3 id="zh-pte-fields">PTE 中的目标信息</h3>
<p>P100 使用 GP100。NVIDIA 公开的 Pascal MMU 文档描述了最多 49 位的虚拟地址和五级页表格式。这里取 <strong>VER2 格式、4 KiB 普通页</strong>；GPU 页表头文件同时含有旧格式定义，解读时应使用 <code>NV_MMU_VER2_PTE_*</code> 这一组位位置。<a href="@@pdf@@">GP100 MMU 文档</a> · <a href="@@pte@@">GP100 VER2 PTE 定义</a></p>
@@figure:pte@@
<p>文档说 Peer ID 与 <code>PA[39:37]</code> 复用，而头文件把它定位到 <code>PTE[35:33]</code>。两者采用不同的位编号：前者编号物理地址，后者编号编码后的 PTE。页基址省去低 12 位，再从 PTE 的 bit 8 开始存放，所以这些字段相差 4 位。<a href="@@pte@@">地址字段与 ADDRESS_SHIFT</a></p>
<p>Peer ID 是硬件映射中的 peer 编号，与 CUDA ordinal、NCCL rank 属于不同的编号体系。具体对应关系由驱动建立。公开驱动中的 <code>kbusGetNvlinkP2PPeerId_GP100</code> 根据拓扑、已有映射和保留 peer slot 取得编号。<a href="@@peer_id@@">Peer ID 分配代码</a></p>

<h3 id="zh-pte-example">一个编码例子</h3>
<p>假设页基址为 <code>0x12345000</code>，目标是 peer slot 3，页内偏移为 <code>0x80</code>。仅设置 Valid、Aperture、Peer ID 和页基址，可写出这个教学用编码：</p>
<pre class="code">PTE = ((0x12345000 &gt;&gt; 12) &lt;&lt; 8)
    | (3 &lt;&lt; 33)   # Peer ID
    | (1 &lt;&lt; 1)    # Aperture = peer
    | 1            # Valid
    = 0x0000000601234503

target = peer slot 3, address 0x12345000 + 0x80</pre>
@@lab@@
<p>Aperture 决定目标类别，页内偏移决定该页内的字节位置。上例只编码了目标与有效位；完整 PTE 还需按实际映射配置缓存、内存布局等属性。三位 Peer ID 属于 GP100 格式，现代 GPU 的格式和可寻址范围需按相应硬件资料解读。</p>

<h2 id="zh-nccl">3. NCCL Device API LSA</h2>
<p>NCCL Device API 将 peer 显存访问开放给用户自己的 CUDA kernel。LSA（Load/Store Accessible）使用 CUDA P2P，支持具有 P2P 连通性的 NVLink 或 PCIe 设备。Host 负责建立 communicator 和内存窗口，kernel 通过窗口取得 peer 指针，再执行普通 load／store。Device API 从 NCCL 2.28 开始提供，本节采用 2.32.3（12df1a11afad）的接口与源码。<a href="@@lsa_usage@@">Device API 使用指南</a></p>

<h3 id="zh-lsa-window">LSA team 与窗口</h3>
<p>LSA team 是可以通过 load／store 相互访问的一组 rank。<code>devComm.lsaRank</code> 表示自己在该 team 中的编号，<code>devComm.lsaSize</code> 表示 team 大小。传给 LSA 接口的是 team 内的 rank，和 CUDA 设备编号属于不同的编号体系。<a href="@@lsa_setup@@">ncclDevComm 字段</a></p>
<p>窗口 <code>ncclWindow_t</code> 把各 rank 注册的 buffer 组织起来，供 kernel 按“窗口、peer、偏移”寻址。每个 rank 仍拥有自己的物理分配；窗口注册负责建立 peer 映射。下面用两个 rank 演示：二者属于同一个 LSA team，各自读取对方的输入，加一后写入本地输出。输入在 kernel 执行期间保持不变。<a href="@@lsa_window@@">窗口注册</a></p>

<h3 id="zh-lsa-host">Host 初始化</h3>
<p>每个 rank 的进程或线程先绑定本地 GPU。Rank 0 调用 <code>ncclGetUniqueId</code> 生成 <code>id</code>，通过已有的 CPU 通信方式分发；随后各 rank 执行下面的初始化。继续注册窗口前，检查 <code>props.deviceApiSupport</code> 为 true，并且 <code>props.nLsaTeams == 1</code>，确保这个两 rank 示例中的双方能直接互访。<a href="@@lsa_example_host@@">官方示例的能力检查</a></p>
@@lsa_query@@
<p>输入用 <code>ncclMemAlloc</code> 分配，再注册为对称窗口。窗口要求使用支持的 VMM 分配或 NCCL 分配器。<code>ncclCommWindowRegister</code> 是 collective 调用，所有 rank 都要参与；本例按相同顺序注册同样大小的输入。输出仅由本地 GPU 写入，因此用普通 <code>cudaMalloc</code> 分配即可。<a href="@@lsa_window@@">分配器要求</a> · <a href="@@lsa_comms@@">窗口注册 API</a></p>
@@lsa_window_code@@
<p>接着创建 <code>ncclDevComm</code>，为 kernel 预留 barrier 资源。本例启动 4 个 CTA，每个 CTA 使用一个 barrier，因此将 <code>lsaBarrierCount</code> 设为 4。<code>ncclDevCommCreate</code> 是 host 侧 collective 调用，返回的通信描述可以按值传入 kernel。<a href="@@lsa_setup@@">设备通信器与资源需求</a></p>
@@lsa_comm_code@@
<p>如果同一线程管理多张 GPU，应把各 rank 的 collective 初始化、窗口注册和设备通信器创建分别放进对应的 <code>ncclGroupStart</code>／<code>ncclGroupEnd</code> 中，等 group 结束后再使用返回的对象。<a href="@@lsa_setup@@">设备通信器的 group 语义</a> · <a href="@@lsa_comms@@">窗口的 group 语义</a></p>

<h3 id="zh-lsa-kernel">Kernel 访问</h3>
<p><code>ncclGetLsaPointer(win, offset, peer)</code> 返回当前 GPU 可访问的 peer 指针，其中 <code>offset</code> 的单位是字节，<code>peer</code> 是 LSA team 内的 rank。本例从窗口起点读取，所以传入 0；随后 <code>src[i]</code> 按 float 元素索引。<a href="@@lsa_memory@@">LSA 指针接口</a></p>
@@lsa_kernel@@
<p>两个 rank 中，<code>(devComm.lsaRank + 1) % devComm.lsaSize</code> 恰好选中对方。<code>ncclGetLsaPointer</code> 的源码根据窗口中的 peer 映射基址、stride 和字节偏移计算地址；数据读取发生在下一步的 <code>src[i]</code>。这里沿用了第一章的普通 load，只是获取 peer 指针的工作交给了 NCCL。<a href="@@lsa_pointer_source@@">ncclGetLsaPointer 实现</a></p>
<div class="p2p-table"><table><thead><tr><th>LSA rank</th><th>本地输入</th><th>预期本地输出</th></tr></thead><tbody>
<tr><td>0</td><td>[0, 1, 2, 3]</td><td>[101, 102, 103, 104]</td></tr>
<tr><td>1</td><td>[100, 101, 102, 103]</td><td>[1, 2, 3, 4]</td></tr>
</tbody></table></div>

<h3 id="zh-lsa-sync">同步与执行</h3>
<p>两个 rank 都在各自的 stream 中完成输入初始化，再以相同的 grid 和 block 配置启动 kernel：</p>
@@lsa_launch@@
<p>入口 barrier 使用 acquire 语义，等待 team 中对应 CTA 到达后再读取 peer 数据；出口 barrier 使用 release 语义，等待对应 CTA 完成这一轮访问。它们沿用官方 LSA 示例的同步方式。<code>ncclCoopCta()</code> 表示整个 CTA 参与，<code>blockIdx.x</code> 选择这一组对应 CTA 使用的 barrier。<a href="@@lsa_example_kernel@@">官方 kernel</a> · <a href="@@lsa_barrier_source@@">LSA barrier 实现</a></p>
<p>每个 CTA 的所有线程都必须执行两次 barrier，包括没有分到数据的线程。因此，越界判断放在循环条件中，线程不能在 barrier 前提前返回。不同 CTA 使用不同的 barrier 编号，各 rank 对同一编号的调用顺序必须匹配；并发 kernel 也应使用各自独立的 barrier 资源。<a href="@@lsa_memory@@">Barrier session 的参与范围</a></p>

<h3 id="zh-lsa-cleanup">资源释放</h3>
<p>所有使用这些资源的 kernel 完成后，销毁设备通信器、注销窗口，再释放分配和 host communicator。窗口与通信器可以在多次 kernel 调用间复用，输入 buffer 的复用仍需等待 peer 读取结束。<a href="@@lsa_setup@@">设备通信器生命周期</a> · <a href="@@lsa_comms@@">窗口生命周期</a></p>
@@lsa_cleanup@@
<p><a href="@@lsa_example@@">官方完整 LSA 示例</a>包含 communicator 启动、输入初始化、结果校验和清理。它演示 AllReduce，本节将数据操作简化为 peer 读取与加一，保留相同的窗口和 barrier 使用流程。</p>

<h2 id="zh-links">4. NVLink 与 PCIe</h2>
<h3 id="zh-physical-path">物理路径</h3>
<p>P2P 描述 GPU 间直接访问内存的能力，实际请求可以走 PCIe、直连 NVLink，或由 NVSwitch 转发的 NVLink fabric。NVSwitch 是交换芯片，端点仍然是持有内存和发起访问的 GPU。</p>
@@figure:routes@@
<p>PCIe P2P 可能经过 PCIe switch 或平台的 root complex；是否可用取决于拓扑与系统配置。直接访问的 payload 无需在 CPU DRAM 建立中转副本。NVLink／NVSwitch 则提供另外的 GPU 互联路径。<a href="@@guide@@">CUDA P2P 的拓扑条件</a> · <a href="@@fabric@@">NVSwitch 软件与硬件结构</a></p>

<h3 id="zh-route-selection">链路选择与路由</h3>
<p>应用通常指定要访问哪张 GPU 的分配；CUDA 的 peer-access API 没有“这一次 load 走哪根 NVLink”的参数。Pascal Tuning Guide 明确说明：可用 NVLink 连接端点间的传输自动经 NVLink 路由。Peer 映射和系统路由配置将目标与可用链路关联起来，GPU 在执行访问时使用这套配置。<a href="@@pascal@@">NVLink 的透明路由</a></p>
<p>公开驱动中的 <code>kbusGetNvlinkP2PPeerId_GP100</code> 根据拓扑和已有状态选择 peer ID；建立映射的代码维护 peer mask，并通过内部控制接口设置 <code>USE_NVLINK_PEER</code>，启用 NVLink peer 路径。这里引用的是公开驱动 620.70.06 中的 GP100 架构函数，未追踪 P100 实机上的完整驱动调用链。<a href="@@peer_id@@">Peer ID</a> · <a href="@@route@@">NVLink peer 启用</a></p>
<div class="p2p-table"><table><thead><tr><th>层次</th><th>决定的内容</th></tr></thead><tbody>
<tr><td>CUDA 分配与映射</td><td>目标显存、访问设备、VA、权限与 peer 对应关系</td></tr>
<tr><td>NCCL LSA</td><td>LSA team、窗口注册、peer 指针与 barrier 资源</td></tr>
<tr><td>驱动／firmware／fabric 管理</td><td>GPU 侧 peer 路由、链路启用、交换结构路由与分区</td></tr>
<tr><td>GPU／交换芯片数据路径</td><td>按已建立的映射和路由处理实际请求与响应</td></tr>
</tbody></table></div>
<p>在 NVSwitch 系统中，Fabric Manager 与内核驱动负责 fabric 初始化和配置。第四代 NVSwitch 的文档进一步区分：NVLSM 配置交换机路由表，FM 管理 GPU 侧路由与 NVLink 配置。一次 <code>ld.global</code> 实际经过哪些交换端口、使用哪些并行链路，由平台的路径和路由策略决定。<a href="@@fabric@@">Fabric Manager / NVLSM 职责</a></p>

<h3 id="zh-multi-node">跨主机的边界</h3>
<p>普通 InfiniBand／Ethernet 集群通常由网络 transport 和 NIC 传输数据；GPUDirect RDMA 允许 NIC 访问 GPU 显存，但不自动让一个普通 CUDA 指针跨主机可解引用。支持 Multi-Node NVLink 的系统通过<a href="#zh-fabric-mapping">第一章的 fabric handle 映射流程</a>，将普通 load／store 访问扩展到支持的 NVLink 域。<a href="@@pascal@@">GPUDirect RDMA</a> · <a href="@@multi_gpu@@">多节点 NVLink 编程模型</a></p>

<h2 id="zh-validation">5. 运行与验证</h2>
<h3 id="zh-build">编译与运行</h3>
<p>将以下四个文件放进同一个目录：<a href="../assets/inside-cuda/gpu-peer-access/peer_load.cuh" download>peer_load.cuh</a>、<a href="../assets/inside-cuda/gpu-peer-access/same_process.cu" download>same_process.cu</a>、<a href="../assets/inside-cuda/gpu-peer-access/ipc_process.cu" download>ipc_process.cu</a>、<a href="../assets/inside-cuda/gpu-peer-access/run_ipc.py" download>run_ipc.py</a>。两个进程使用同一份 CUDA_VISIBLE_DEVICES 顺序；下面让可见 GPU 0 读取可见 GPU 1：</p>
<pre class="code"># Ampere example; select the SM target for your GPUs.
nvcc -std=c++17 -O3 -lineinfo -arch=sm_80 same_process.cu -o same_process
nvcc -std=c++17 -O3 -lineinfo -arch=sm_80 ipc_process.cu -o ipc_process

./same_process 0 1
python3 run_ipc.py --binary ./ipc_process --reader 0 --owner 1

# Inspect the same kernel without requiring a running GPU.
nvcc -std=c++17 -O3 -arch=sm_80 --ptx same_process.cu -o peer_load.ptx
cuobjdump --dump-sass ./same_process</pre>
<p>P100 对应 <code>sm_60</code>，可使用本文验证过的 CUDA 12.4 工具链。每个程序检查 65,536 个输出元素；成功时报告 <code>PASS: 65536 peer loads verified.</code>。IPC 启动器在 Owner 导出句柄后启动独立 Reader，等待 Reader 成功退出，再通知 Owner 释放。</p>
<aside class="p2p-note"><p>同进程、节点内 IPC 示例已通过 CUDA 12.4.131 的 sm_60 和 sm_80 目标编译，并检查了 sm_60 的 PTX 与 SASS。Fabric handle 片段通过 sm_80 目标编译。LSA 片段使用 NCCL 2.32.3 头文件通过 sm_80 目标编译，未链接 NCCL；编译时关闭了本例未使用的 GIN GDAKI 与 EFA 后端。验证环境没有可见 GPU，尚未进行双 GPU 或跨节点实机运行；PASS 是程序成功时的预期输出。</p></aside>

<h3 id="zh-observe">拓扑与传输证据</h3>
<pre class="code">nvidia-smi topo -m
nvidia-smi topo -p2p r
nvidia-smi topo -p2p w
nvidia-smi topo -p2p n
nvidia-smi nvlink --status

# Run your existing NCCL executable with connection diagnostics.
NCCL_DEBUG=INFO NCCL_DEBUG_SUBSYS=INIT,GRAPH,P2P ./your_nccl_program</pre>
<p><code>topo</code> 显示拓扑与 P2P 能力，<code>nvlink --status</code> 显示链路状态。NCCL 日志用于检查 communicator 初始化与拓扑识别；LSA 示例还通过 <code>ncclCommQueryProperties</code> 检查 Device API 支持情况和 LSA team 数量。<a href="@@smi@@">nvidia-smi 命令</a> · <a href="@@lsa_example_host@@">LSA 能力检查</a></p>
<p>某次 kernel 的实际传输字节数与所经链路，需要结合相应平台的 NVLink／PCIe 计数器测量。<code>ncclGetLsaPointer</code> 取得地址后，数据传输由 kernel 的 load／store 触发，沿已建立的 CUDA 映射和硬件路由执行。<a href="@@lsa_usage@@">LSA 访问模型</a></p>

<h3 id="zh-sources">源码索引</h3>
<ul><li><a href="@@pdf@@">GP100 MMU 格式</a>与<a href="@@pte@@">VER2 PTE 位定义</a>：地址翻译的目标字段。</li>
<li><a href="@@peer_id@@">公开驱动 peer ID 分配</a>与<a href="@@route@@">NVLink peer 启用</a>：映射与互联配置线索。</li>
<li><a href="@@fabric_memory@@">VMM fabric handle</a>与<a href="@@imex@@">IMEX 服务</a>：跨节点的分配识别与映射。</li>
<li><a href="@@lsa_example@@">NCCL LSA 完整示例</a>：窗口注册、设备通信器与 kernel 调用。</li>
<li><a href="@@lsa_pointer_source@@">ncclGetLsaPointer</a>与<a href="@@lsa_barrier_source@@">LSA barrier</a>：peer 地址计算与设备端同步。</li></ul>
'''


EN = r'''
<h1>GPU peer-to-peer memory access</h1>
<p>GPU peer-to-peer access lets a kernel address another GPU's device memory through an authorized mapping. The producer's data can stay on its GPU while a consumer reads it through an ordinary pointer, avoiding a staging copy through CPU memory. This connects CUDA access control, GPU address translation, the NCCL Device API, and NVLink or PCIe: the driver establishes mappings, hardware executes accesses, and the communication library provides peer pointers and synchronization interfaces.</p>
<aside class="p2p-note"><p>The same-process and intra-node IPC examples use 64-bit Linux, two P2P-capable GPUs in one host, and cudaMalloc allocations; the cross-node example uses VMM fabric handles. P100's GP100 page-table format illustrates address translation. The NCCL LSA example uses version 2.32.3, commit 12df1a11afad, ncclMemAlloc allocations, and devices that support the Device API.</p></aside>

<p>For PyTorch peer mappings and custom compute kernels, see <a href="pytorch-symmetric-memory.html#en-internals">PyTorch Symmetric Memory and GPU P2P Access, chapter 3</a>, which cross-references this article’s CUDA IPC, VMM, and fabric-handle paths and includes Triton and MegaMoE examples.</p>

<h2 id="en-kernel">1. Kernels and access mappings</h2>
<h3 id="en-load">The same load instruction</h3>
<p>GPU 1 owns the input; GPU 0 runs a kernel that adds one and stores into its local output. The source may be local memory or authorized, mapped peer memory:</p>
@@kernel@@
<p>The programmer writes <code>src[i]</code> in either case. The same compiled kernel accepts either pointer; its instruction does not encode a CUDA device ordinal. Compiling this source with CUDA 12.4.131 and <code>-O3 -arch=sm_60</code> produced:</p>
<pre class="code"><code>// PTX
ld.global.f32  %f1, [%rd5];
add.f32        %f2, %f1, 0f3F800000;
st.global.f32  [%rd7], %f2;

// SASS source read
LDG.E R2, [R2];</code></pre>
<p>Translation and hardware routing determine this load's destination, so an ordinary load suffices for peer access. Changes in data width, vectorization, or cache hints can produce other load forms. <a href="@@ptx@@">PTX ld</a> · <a href="@@guide@@">CUDA peer access</a></p>

<h3 id="en-single-process">One process, two GPUs</h3>
<p>Express access as <strong>reader → owner</strong>. GPU 0 reading GPU 1 queries <code>cudaDeviceCanAccessPeer(&amp;ok, 0, 1)</code>, then calls <code>cudaDeviceEnablePeerAccess(1, 0)</code> with GPU 0 current. The second argument is reserved flags and must be zero. Access is directional; the reverse direction requires its own enable call. <a href="@@peer@@">Peer access API</a></p>
<p>The snippets assume a successful P2P capability check, with <code>n</code> elements and <code>bytes = n * sizeof(float)</code>. They show the essential calls; initialization, error handling, synchronization, and cleanup are in the <a href="#en-build">complete examples</a>.</p>
@@same_process@@
<p>Within this process, UVA permits passing the allocation's pointer to the other GPU. Address-space organization and access authorization are separate requirements. The allocation stays on its owner; this example does not use managed-memory migration. <a href="@@guide@@">Unified addresses and peer access</a></p>

<h3 id="en-ipc">Intra-node, cross-process mappings</h3>
<p>UVA unifies virtual addressing within a single process. Across processes, each process has its own GPU virtual address space and page-table mappings. A CUDA IPC handle lets the receiving process map the peer's allocation into its own address space. The owner exports the allocation as a <code>cudaIpcMemHandle_t</code> and passes it through OS IPC; the reader imports it to obtain a pointer valid in its process. The two pointers access the same physical allocation through their respective mappings. <a href="@@uva@@">UVA</a> · <a href="@@ipc@@">CUDA IPC</a></p>
@@figure:mapping@@
<div class="p2p-table"><table><thead><tr><th>Step</th><th>One process</th><th>Two processes</th></tr></thead><tbody>
<tr><td>Shared object</td><td>An allocation in the process</td><td>An exported allocation handle</td></tr>
<tr><td>Access setup</td><td>Reader enables peer access to owner</td><td>Reader imports on its current device</td></tr>
<tr><td>Kernel pointer</td><td>The allocation's UVA pointer</td><td>The pointer returned by cudaIpcOpenMemHandle</td></tr>
<tr><td>End access</td><td>Wait for kernel; disable access if appropriate</td><td>Wait for kernel; close imported mapping</td></tr>
<tr><td>Free allocation</td><td>Owner frees after use completes</td><td>Owner frees after the importer acknowledges closure</td></tr>
</tbody></table></div>
<p><code>send_handle</code> and <code>receive_handle</code> are CPU IPC helpers defined by the example. <code>send_handle</code> writes the handle length and raw <code>cudaIpcMemHandle_t</code> bytes to stdout. <code>run_ipc.py</code> relays them through pipes to the reader's stdin, where <code>receive_handle</code> reads the handle back. The pipe carries the allocation handle; <code>peer_load</code> reads GPU data over the GPU interconnect.</p>
@@ipc_columns@@
<p>The reader establishes its mapping with <code>cudaIpcOpenMemHandle</code>; <code>cudaIpcMemLazyEnablePeerAccess</code> lets import attempt peer-access setup as needed. After use completes, the reader closes the mapping with <code>cudaIpcCloseMemHandle</code>, and the owner frees the allocation. <a href="@@ipc@@">Import and allocation lifetime</a></p>

<h3 id="en-fabric-mapping">Cross-node mappings</h3>
<p>Nodes have separate OS instances, GPU drivers, and process address spaces. Sharing an allocation requires a handle that identifies it across those boundaries. <code>cudaIpcMemHandle_t</code> supports sharing between processes on one node. On Multi-Node NVLink systems, VMM exports a <code>CUmemFabricHandle</code> using <code>CU_MEM_HANDLE_TYPE_FABRIC</code>. Another node's driver imports the allocation and maps the same physical GPU memory into the receiving process's GPU virtual address space. <a href="@@multi_gpu@@">Multi-node CUDA model</a> · <a href="@@fabric_memory@@">VMM fabric handles</a></p>
<p>This path requires reachable GPUs within an NVLink fabric, nodes configured in one IMEX domain, and exporter and importer access to the same IMEX channel. IMEX coordinates memory import, export, and lifetime across OS instances. Once the drivers establish the mappings, GPU loads and stores access remote memory over the NVLink fabric. <a href="@@imex@@">IMEX responsibilities</a> · <a href="@@imex_channels@@">IMEX channels and permissions</a></p>
<p>The snippets show the export and import calls using fabric handles, available since CUDA 12.4. Each side has initialized its CUDA context and confirmed <code>CU_DEVICE_ATTRIBUTE_HANDLE_TYPE_FABRIC_SUPPORTED</code>. <code>ownerDevice</code> and <code>readerDevice</code> are device ordinals local to their respective nodes. <code>bytes</code> is aligned to the allocation granularity queried through <code>cuMemGetAllocationGranularity</code>. The reader's <code>local</code> points to an allocated local output, and <code>n</code> is the agreed number of float elements.</p>
@@fabric_columns@@
<p><code>send_fabric</code> and <code>receive_fabric</code> represent application CPU communication: a TCP socket or MPI transfers the <code>CUmemFabricHandle</code> bytes and allocation size. The owner's <code>alloc</code> and the reader's <code>imported</code> are VMM allocation handles local to their processes. <code>peerVA</code> is the address reserved and mapped by the reader for its kernel; <code>cuMemSetAccess</code> grants the reader's local GPU read permission. <a href="@@vmm@@">Export, import, mapping, and access APIs</a></p>
<p>To initialize the data, the owner also reserves an address range, maps <code>alloc</code>, and grants local write access. It signals readiness after initialization completes, allowing the reader to start. After the GPU operations finish, both sides remove their mappings and release their address reservations and allocation handles with <code>cuMemUnmap</code>, <code>cuMemAddressFree</code>, and <code>cuMemRelease</code>. The application coordinates data readiness and completion separately from sharing the allocation handle. <a href="@@vmm@@">VMM resource lifetime</a></p>

<h3 id="en-ordering">Ordering and permissions</h3>
<p>After establishing a mapping, the application must still order producer and consumer execution. The downloadable examples use host waits: the owner publishes after initialization completes, and the reader acknowledges after its kernel finishes and its mapping closes. The owner can then safely reuse or free the allocation. Same-process streams can also use cross-device event waits, while exported CUDA events support process boundaries within one node. <a href="@@events@@">Cross-device event waits</a> · <a href="@@ipc@@">IPC events</a></p>
<p>Access control follows the allocation type: cudaMalloc peer access uses device peer enablement or legacy IPC import; VMM allocations use <code>cuMemSetAccess</code> for device permissions; stream-ordered pools have separate access settings. Reachability, permissions, and execution ordering must all hold. <a href="@@vmm@@">VMM</a> · <a href="https://docs.nvidia.com/cuda/archive/12.4.1/cuda-runtime-api/group__CUDART__MEMORY__POOLS.html">Pool access</a></p>

<h2 id="en-pte">2. P100 address translation</h2>
<h3 id="en-control-data">Setup and execution</h3>
<p>During setup, the driver validates the allocation and access capability, establishes mappings and permissions, and maintains peer relationships and lifetimes. Peer enablement, IPC, and VMM are different API entry points; their complete internal call chains are implementation details.</p>
<p>With a valid mapping, the SM issues a global load. Translation uses a cached TLB result or a page-table walk, producing an address and target attributes. Interconnect hardware handles a peer request and returns its data. An ordinary mapped load does not call the CPU driver for each element. The mechanism can be summarized as:</p>
<pre class="code">CPU / driver: allocation → peer mapping + access permissions
                                    ↓
GPU SM: load VA → address translation → aperture + target address
                                       ├─ local → local memory path
                                       └─ peer  → peer route → remote memory</pre>
<p>This is a mechanism-level explanation inferred from API semantics and the published format. Cache pipelines, transaction merging, and internal interconnect stages are omitted. GP100's PTE fields provide concrete evidence for the target information. <a href="@@pdf@@">Pascal MMU format, page 4</a></p>

<h3 id="en-pte-fields">Target fields in a PTE</h3>
<p>P100 uses GP100. Its published MMU format supports up to 49-bit virtual addresses and a five-level layout. This example uses a <strong>VER2-format, ordinary 4 KiB page</strong>. The header also contains older definitions; the positions here come from <code>NV_MMU_VER2_PTE_*</code>. <a href="@@pdf@@">GP100 format</a> · <a href="@@pte@@">VER2 definitions</a></p>
@@figure:pte@@
<p>The document's PA[39:37] and the header's PTE[35:33] describe different bit-numbering spaces. Dropping twelve page-offset bits and encoding from PTE bit 8 produces the four-bit difference. <a href="@@pte@@">Address fields and shift</a></p>
<p>A peer ID identifies a hardware mapping slot, in a separate numbering scheme from CUDA ordinals and NCCL ranks. The driver establishes that correspondence. Its public <code>kbusGetNvlinkP2PPeerId_GP100</code> code assigns IDs using topology, existing mappings, and reserved peer slots. <a href="@@peer_id@@">Peer ID assignment</a></p>

<h3 id="en-pte-example">An encoding example</h3>
<p>Take page base <code>0x12345000</code>, peer slot 3, and byte offset <code>0x80</code>. Setting only validity, aperture, peer ID, and the base gives:</p>
<pre class="code">PTE = ((0x12345000 &gt;&gt; 12) &lt;&lt; 8)
    | (3 &lt;&lt; 33)   # Peer ID
    | (1 &lt;&lt; 1)    # Aperture = peer
    | 1            # Valid
    = 0x0000000601234503

target = peer slot 3, address 0x12345000 + 0x80</pre>
@@lab@@
<p>The aperture selects the target class; the offset selects a byte in the page. The example encodes only the target and validity. A complete PTE also needs cache, layout, and other attributes appropriate to the mapping. The three-bit peer ID belongs to GP100; formats and addressing limits for later GPUs require their own hardware documentation.</p>

<h2 id="en-nccl">3. NCCL Device API LSA</h2>
<p>NCCL's Device API exposes peer memory access to user CUDA kernels. LSA (Load/Store Accessible) uses CUDA P2P over NVLink or PCIe where P2P connectivity is available. Host code establishes communicators and memory windows; the kernel obtains peer pointers from those windows and uses ordinary loads and stores. The Device API was introduced in NCCL 2.28. This section uses the interfaces and source from 2.32.3, commit 12df1a11afad. <a href="@@lsa_usage@@">Device API guide</a></p>

<h3 id="en-lsa-window">LSA teams and windows</h3>
<p>An LSA team contains ranks that can communicate through memory loads and stores. <code>devComm.lsaRank</code> is the local rank within that team; <code>devComm.lsaSize</code> is its size. LSA interfaces use team ranks, which have a separate numbering scheme from CUDA device ordinals. <a href="@@lsa_setup@@">Device communicator fields</a></p>
<p>A window, <code>ncclWindow_t</code>, organizes registered buffers across ranks so kernels can address data by window, peer, and offset. Each rank owns its physical allocation; window registration establishes the peer mappings. The example uses two ranks in one LSA team. Each reads the other's input, adds one, and writes its local output. Inputs remain unchanged throughout the kernel. <a href="@@lsa_window@@">Window registration</a></p>

<h3 id="en-lsa-host">Host setup</h3>
<p>Each rank's process or thread binds its local GPU. Rank 0 obtains <code>id</code> with <code>ncclGetUniqueId</code> and distributes it using the application's CPU communication mechanism. Each rank then performs the setup below. Before registering windows, check that <code>props.deviceApiSupport</code> is true and <code>props.nLsaTeams == 1</code>, so both ranks in this example can access each other directly. <a href="@@lsa_example_host@@">Official capability checks</a></p>
@@lsa_query@@
<p>Allocate input with <code>ncclMemAlloc</code> and register a symmetric window. Windows require a supported VMM allocation or the NCCL allocator. <code>ncclCommWindowRegister</code> is collective: every rank participates. This example registers equally sized inputs in the same order. Output is written only by the local GPU, so ordinary <code>cudaMalloc</code> suffices. <a href="@@lsa_window@@">Allocation requirements</a> · <a href="@@lsa_comms@@">Window API</a></p>
@@lsa_window_code@@
<p>Create <code>ncclDevComm</code> with the barrier resources needed by the kernel. The example launches four CTAs and reserves one barrier per CTA by setting <code>lsaBarrierCount</code> to four. <code>ncclDevCommCreate</code> is a host-side collective call; the returned descriptor can be passed to the kernel by value. <a href="@@lsa_setup@@">Device communicator requirements</a></p>
@@lsa_comm_code@@
<p>When one thread manages multiple GPUs, group the ranks' collective initialization, window registration, and device communicator creation in their respective <code>ncclGroupStart</code>/<code>ncclGroupEnd</code> scopes. Use returned objects after the group has completed. <a href="@@lsa_setup@@">Device communicator group semantics</a> · <a href="@@lsa_comms@@">Window group semantics</a></p>

<h3 id="en-lsa-kernel">Kernel access</h3>
<p><code>ncclGetLsaPointer(win, offset, peer)</code> returns a peer pointer accessible from the current GPU. <code>offset</code> is measured in bytes and <code>peer</code> is an LSA team rank. The example passes zero for the window's start, then indexes <code>src[i]</code> in float elements. <a href="@@lsa_memory@@">LSA pointer accessors</a></p>
@@lsa_kernel@@
<p>With two ranks, <code>(devComm.lsaRank + 1) % devComm.lsaSize</code> selects the other rank. The <code>ncclGetLsaPointer</code> implementation calculates an address from the window's peer-mapping base, stride, and byte offset. The subsequent <code>src[i]</code> performs the data load. This is the ordinary load from chapter 1, with NCCL providing the peer pointer. <a href="@@lsa_pointer_source@@">Pointer implementation</a></p>
<div class="p2p-table"><table><thead><tr><th>LSA rank</th><th>Local input</th><th>Expected local output</th></tr></thead><tbody>
<tr><td>0</td><td>[0, 1, 2, 3]</td><td>[101, 102, 103, 104]</td></tr>
<tr><td>1</td><td>[100, 101, 102, 103]</td><td>[1, 2, 3, 4]</td></tr>
</tbody></table></div>

<h3 id="en-lsa-sync">Synchronization and launch</h3>
<p>Each rank initializes its input on its stream before launching the kernel. Both use the same grid and block configuration:</p>
@@lsa_launch@@
<p>The entry barrier uses acquire ordering and waits for the team's corresponding CTAs before reading peer input. The exit barrier uses release ordering and waits for those CTAs to finish the round of accesses. This follows the official LSA example. <code>ncclCoopCta()</code> makes the whole CTA participate, while <code>blockIdx.x</code> selects the barrier used by corresponding CTAs across ranks. <a href="@@lsa_example_kernel@@">Official kernel</a> · <a href="@@lsa_barrier_source@@">Barrier implementation</a></p>
<p>Every thread in a CTA must execute both barriers, including threads with no data to process. Bounds checking therefore belongs in the loop condition, with no early return before a barrier. Different CTAs use distinct barrier indices, and ranks must call each index in matching order. Concurrent kernels also need independent barrier resources. <a href="@@lsa_memory@@">Barrier participation</a></p>

<h3 id="en-lsa-cleanup">Resource lifetime</h3>
<p>After all kernels using these resources have completed, destroy the device communicator, deregister the window, then release the allocations and host communicator. Windows and communicators can be reused across kernel launches; reusing an input buffer still requires its peers to finish reading it. <a href="@@lsa_setup@@">Device communicator lifetime</a> · <a href="@@lsa_comms@@">Window lifetime</a></p>
@@lsa_cleanup@@
<p>The <a href="@@lsa_example@@">complete official LSA example</a> includes communicator startup, input initialization, verification, and cleanup. It implements AllReduce. This section simplifies the data operation to a peer read plus one while retaining its window and barrier workflow.</p>

<h2 id="en-links">4. NVLink and PCIe</h2>
<h3 id="en-physical-path">Physical paths</h3>
<p>P2P describes direct access to another GPU's memory. Requests may travel over PCIe, a direct NVLink connection, or an NVLink fabric with NVSwitch forwarding. NVSwitch switches traffic; the GPUs issue requests and own the memory.</p>
@@figure:routes@@
<p>A PCIe route can traverse switches or a platform root complex, subject to topology and support. Direct payload access needs no staging allocation in CPU DRAM. NVLink and NVSwitch provide other interconnect paths. <a href="@@guide@@">Topology requirements</a> · <a href="@@fabric@@">NVSwitch structure</a></p>

<h3 id="en-route-selection">Link selection and routing</h3>
<p>The application identifies the target allocation; CUDA peer-access APIs expose no per-load NVLink-port parameter. The Pascal guide documents automatic NVLink routing between connected endpoints. Peer mappings and system routing associate the destination with available links, and hardware uses that configuration during execution. <a href="@@pascal@@">Transparent NVLink routing</a></p>
<p>In the public driver, <code>kbusGetNvlinkP2PPeerId_GP100</code> selects a peer ID from topology and existing state. Mapping code maintains peer masks and sets <code>USE_NVLINK_PEER</code> through an internal control interface to enable the NVLink peer path. These references cover GP100 architecture functions in driver 620.70.06; the full call chain on a running P100 has not been traced here. <a href="@@peer_id@@">Peer ID selection</a> · <a href="@@route@@">Peer route enablement</a></p>
<div class="p2p-table"><table><thead><tr><th>Layer</th><th>What it determines</th></tr></thead><tbody>
<tr><td>CUDA allocation/mapping</td><td>Memory target, accessing device, VA, permissions, peer relationship</td></tr>
<tr><td>NCCL LSA</td><td>LSA teams, window registration, peer pointers, barrier resources</td></tr>
<tr><td>Driver/firmware/fabric management</td><td>GPU peer routes, link enablement, switch routes, partitions</td></tr>
<tr><td>GPU/switch data path</td><td>Actual request and response processing under that configuration</td></tr>
</tbody></table></div>
<p>NVSwitch systems use Fabric Manager and kernel drivers for fabric setup. Fourth-generation documentation assigns switch routing tables to NVLSM and GPU-side routing and NVLink configuration to FM. The platform's paths and routing policy determine which switch ports and parallel links a load traverses. <a href="@@fabric@@">FM and NVLSM responsibilities</a></p>

<h3 id="en-multi-node">Across hosts</h3>
<p>Ordinary InfiniBand/Ethernet clusters use network transports and NICs. GPUDirect RDMA enables NIC access to GPU memory; it does not make an arbitrary remote-host CUDA pointer dereferenceable. Supported Multi-Node NVLink systems use the <a href="#en-fabric-mapping">fabric-handle mapping workflow in chapter 1</a> to extend ordinary loads and stores across their NVLink domain. <a href="@@pascal@@">GPUDirect RDMA</a> · <a href="@@multi_gpu@@">Multi-node NVLink programming</a></p>

<h2 id="en-validation">5. Build and verify</h2>
<h3 id="en-build">Compile and run</h3>
<p>Save these four files together: <a href="../assets/inside-cuda/gpu-peer-access/peer_load.cuh" download>peer_load.cuh</a>, <a href="../assets/inside-cuda/gpu-peer-access/same_process.cu" download>same_process.cu</a>, <a href="../assets/inside-cuda/gpu-peer-access/ipc_process.cu" download>ipc_process.cu</a>, and <a href="../assets/inside-cuda/gpu-peer-access/run_ipc.py" download>run_ipc.py</a>. Both children inherit the same CUDA_VISIBLE_DEVICES ordering. Visible GPU 0 reads GPU 1:</p>
<pre class="code"># Ampere example; select the SM target for your GPUs.
nvcc -std=c++17 -O3 -lineinfo -arch=sm_80 same_process.cu -o same_process
nvcc -std=c++17 -O3 -lineinfo -arch=sm_80 ipc_process.cu -o ipc_process

./same_process 0 1
python3 run_ipc.py --binary ./ipc_process --reader 0 --owner 1

# Compile/disassemble without a running GPU.
nvcc -std=c++17 -O3 -arch=sm_80 --ptx same_process.cu -o peer_load.ptx
cuobjdump --dump-sass ./same_process</pre>
<p>P100 uses sm_60 with a supporting toolkit such as the CUDA 12.4 compiler used here. Each program verifies 65,536 output values and reports <code>PASS: 65536 peer loads verified.</code> on success. The launcher starts an independent reader after the owner publishes its handle, then acknowledges successful reader completion so the owner can free the allocation.</p>
<aside class="p2p-note"><p>The same-process and intra-node IPC programs compiled with CUDA 12.4.131 for sm_60 and sm_80, and the sm_60 PTX/SASS were inspected. The fabric-handle snippets compiled for sm_80. The LSA snippets compiled for sm_80 against NCCL 2.32.3 headers, without linking NCCL; the unused GIN GDAKI and EFA backends were disabled for this check. The validation environment has no visible GPU. Two-GPU and cross-node execution remain unverified; PASS is the expected successful output.</p></aside>

<h3 id="en-observe">Topology and transport evidence</h3>
<pre class="code">nvidia-smi topo -m
nvidia-smi topo -p2p r
nvidia-smi topo -p2p w
nvidia-smi topo -p2p n
nvidia-smi nvlink --status

# Your existing NCCL executable:
NCCL_DEBUG=INFO NCCL_DEBUG_SUBSYS=INIT,GRAPH,P2P ./your_nccl_program</pre>
<p>Topology queries show connections and P2P capabilities; link-status queries show available links. NCCL logs help inspect communicator initialization and topology detection. The LSA example also queries <code>ncclCommQueryProperties</code> for Device API support and the number of LSA teams. <a href="@@smi@@">nvidia-smi commands</a> · <a href="@@lsa_example_host@@">LSA capability checks</a></p>
<p>Measuring a kernel's transferred bytes and identifying the links used requires the platform's NVLink or PCIe counters. After <code>ncclGetLsaPointer</code> returns an address, the kernel's loads and stores trigger data transfers through the established CUDA mappings and hardware routes. <a href="@@lsa_usage@@">LSA access model</a></p>

<h3 id="en-sources">Source index</h3>
<ul><li><a href="@@pdf@@">GP100 MMU format</a> and <a href="@@pte@@">VER2 PTE fields</a>: translation targets.</li>
<li><a href="@@peer_id@@">Public driver peer-ID assignment</a> and <a href="@@route@@">NVLink peer enablement</a>: configuration clues.</li>
<li><a href="@@fabric_memory@@">VMM fabric handles</a> and <a href="@@imex@@">IMEX</a>: identifying and mapping allocations across nodes.</li>
<li><a href="@@lsa_example@@">Complete NCCL LSA example</a>: window registration, device communicator, and kernel launch.</li>
<li><a href="@@lsa_pointer_source@@">ncclGetLsaPointer</a> and <a href="@@lsa_barrier_source@@">LSA barriers</a>: peer address calculation and device synchronization.</li></ul>
'''


def expand(body, lang):
    pieces = dict(LINKS)
    pieces['kernel'] = code('peer_load.cuh', 'kernel')
    pieces['same_process'] = snippet(HOST_SNIPPETS['same_process'])
    pieces['ipc_columns'] = ipc_columns(lang)
    pieces['fabric_columns'] = ipc_columns(lang, fabric=True)
    pieces['lab'] = lab(lang)
    pieces.update({key: snippet(value) for key, value in LSA_SNIPPETS.items()})
    for kind in ['mapping','pte','routes']: pieces['figure:'+kind] = figure(lang, kind)
    return re.sub(r'@@([\w:]+)@@', lambda m: pieces[m[1]], body)


def main():
    meta = {
        'title':'GPU P2P 显存访问', 'title_en':'GPU peer-to-peer memory access',
        'slug':'gpu-peer-to-peer-memory', 'date':'2026-11-09',
        'tags':'CUDA, GPU, P2P, NCCL, NVLink, 页表',
        'tags_en':'CUDA, GPU, P2P, NCCL, NVLink, Page Tables',
        'reading':'25 分钟', 'reading_en':'25 min',
        'summary':'读另一张 GPU 的显存，kernel 照样写 src[i]，指令里不带设备编号。驱动建好映射后，地址翻译找到对端，硬件路由再经 NVLink 或 PCIe 送达请求。',
        'summary_en':'Kernels read peer GPU memory with plain src[i]; the instruction names no device. Driver mappings let address translation find the peer; routing then carries the request over NVLink or PCIe.',
        'series':'inside-cuda', 'series_title':'Inside CUDA',
        'series_title_en':'Inside CUDA', 'series_order':'4',
    }
    metadata = '\n'.join(f'<meta name="post:{k}" content="{escape(v, quote=True)}">' for k,v in meta.items())
    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{meta['title']}</title>
{metadata}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/inside-cuda/gpu-peer-access/style.css?v=content-fit-4">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="../assets/inside-cuda/gpu-peer-access/page.js" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>{render_series_nav(meta, ROOT / 'posts')}</aside><main class="content">
<div class="lang-zh">{expand(ZH,'zh')}</div><div class="lang-en">{expand(EN,'en')}</div>
</main></div></body></html>
'''
    target = ROOT / 'posts/gpu-peer-to-peer-memory.html'
    target.write_text(html)
    print('Wrote', target)


if __name__ == '__main__':
    main()
