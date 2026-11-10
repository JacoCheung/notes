#!/usr/bin/env python3
"""Build the Symmetric Memory article; embed the downloadable example verbatim."""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PT = 'https://github.com/pytorch/pytorch/blob/v2.9.0/'
DG = 'https://github.com/deepseek-ai/DeepGEMM/blob/5081f8513af57e61696de4f4f04b0e707ffb503e/'
C10 = PT + 'torch/csrc/distributed/c10d/symm_mem/'
MEGA = DG + 'deep_gemm/include/deep_gemm/'
DEMO = ROOT / 'assets/pytorch-internals/symmetric-memory/p2p_read.py'

def code(s, lang='python'):
    return f'<pre class="code" data-language="{lang}"><code>{escape(s.strip())}</code></pre>'

def snippet(name):
    m = re.search(r'^# BEGIN '+name+r'\n(.*?)^# END '+name, DEMO.read_text(), re.M | re.S)
    if m is None:
        # Host snippets are indented within main().
        m = re.search(r'^    # BEGIN '+name+r'\n(.*?)^    # END '+name, DEMO.read_text(), re.M | re.S)
        import textwrap
        return code(textwrap.dedent(m[1]))
    return code(m[1])

def link(url, label):
    return f'<a href="{url}">{label}</a>'

PYAPI = link(PT+'torch/distributed/_symmetric_memory/__init__.py#L1657-L1740', 'empty / rendezvous')
ALLOC = link(C10+'CUDASymmetricMemory.cu#L346-L413', 'CUDA allocator')
RDV = link(C10+'CUDASymmetricMemory.cu#L600-L717', 'CUDA rendezvous')
MAP = link(C10+'CUDASymmetricMemoryUtils.cpp#L227-L248', 'map_block')
VIEW = link(C10+'SymmetricMemory.cpp#L332-L387', 'get_buffer / get_remote_tensor')
BARRIER = link(C10+'CUDASymmetricMemory.cu#L204-L217', 'barrier')
BUF = link(DG+'deep_gemm/mega/__init__.py#L18-L76', 'SymmBuffer')
WRAP = link(DG+'deep_gemm/mega/__init__.py#L168-L190', 'fp8_fp4_mega_moe wrapper')
SYMPTR = link(MEGA+'layout/sym_buffer.cuh#L9-L41', 'SymBuffer::map')
LAYOUT = link(MEGA+'layout/mega_moe.cuh', 'MegaMoE layout')
PULL = link(MEGA+'impls/sm100_fp8_fp4_mega_moe.cuh#L530-L608', 'dispatch pull')
PUSH = link(MEGA+'impls/sm100_fp8_fp4_mega_moe.cuh#L1322-L1352', 'combine write-back')
READY = link(MEGA+'impls/sm100_fp8_fp4_mega_moe.cuh#L1407-L1441', 'combine readiness')
TEST = link(DG+'tests/test_mega_moe.py', 'test_mega_moe.py')

def diagram(lang):
    zh = lang == 'zh'
    title = 'Rank 0 到 GPU 1 的地址映射' if zh else 'Peer address mapping from rank 0 to GPU 1'
    labels = ['Rank 0 · GPU 0 kernel', 'peer + i → tl.load', 'Rank 0 · buffer_ptrs[1]', '映射到 GPU 1 的显存', 'NVLink / PCIe', 'Rank 1 · GPU 1 HBM', 'x[i] = 10', '映射建立在初始化阶段；每次访问由 GPU 执行。'] if zh else ['Rank 0 · GPU 0 kernel', 'peer + i → tl.load', 'Rank 0 · buffer_ptrs[1]', 'Maps GPU 1 memory', 'NVLink / PCIe', 'Rank 1 · GPU 1 HBM', 'x[i] = 10', 'Mappings are established at initialization; the GPU executes each access.']
    return f'''<figure class="sm-figure"><svg viewBox="0 0 840 250" role="img" aria-labelledby="{lang}-mapping-title" xmlns="http://www.w3.org/2000/svg"><title id="{lang}-mapping-title">{title}</title>
<g fill="none" stroke="currentColor" stroke-width="1.5"><rect x="16" y="25" width="246" height="140" rx="6"/><rect x="296" y="25" width="246" height="140" rx="6"/><rect x="576" y="25" width="246" height="140" rx="6"/><path d="M262 95h34m-8 -6 8 6-8 6M542 95h34m-8 -6 8 6-8 6"/></g>
<g fill="currentColor" text-anchor="middle" font-family="sans-serif" font-size="17"><text x="139" y="62">{labels[0]}</text><text x="139" y="112">{labels[1]}</text><text x="419" y="62">{labels[2]}</text><text x="419" y="112">{labels[3]}</text><text x="699" y="62">{labels[5]}</text><text x="699" y="112">{labels[6]}</text><text x="559" y="192" font-size="14">{labels[4]}</text><text x="420" y="232" font-size="16">{labels[7]}</text></g></svg><figcaption>{title}</figcaption></figure>'''

HOST = '''symm_mem.set_backend("CUDA")
x = symm_mem.empty(n, dtype=torch.float32, device=device)
hdl = symm_mem.rendezvous(x, group=dist.group.WORLD)
peer = hdl.get_buffer(peer_rank, x.shape, x.dtype)'''
VMM = '''// Simplified CUDA Driver API sequence; error handling omitted.
cuMemGetAllocationGranularity(&granularity, &prop, ...);
cuMemCreate(&allocation, aligned_bytes, &prop, 0);
cuMemAddressReserve(&va, aligned_bytes, 0, 0, 0);
cuMemMap(va, aligned_bytes, 0, allocation, 0);
cuMemSetAccess(va, aligned_bytes, &access_desc, 1);

// Exporter -> handle exchange -> importer
cuMemExportToShareableHandle(&shared, allocation, handle_type, 0);
cuMemImportFromShareableHandle(&peer_allocation, shared_arg, handle_type);
// Importer then reserves VA, maps peer_allocation, and sets local-device access.'''
MEGAHOST = '''# Schematic call site: x_fp8/x_sf and weights already have required layouts.
buffer = deep_gemm.get_symm_buffer_for_mega_moe(
    group, num_experts, num_max_tokens_per_rank, num_topk,
    hidden, intermediate_hidden, mma_type="fp8xfp4",
)
w1, w2 = deep_gemm.transform_weights_for_mega_moe(l1_weights, l2_weights)

# Each iteration, on the stream used to launch MegaMoE:
buffer.x[:num_tokens].copy_(x_fp8)
buffer.x_sf[:num_tokens].copy_(x_sf)
buffer.topk_idx[:num_tokens].copy_(topk_idx)
buffer.topk_weights[:num_tokens].copy_(topk_weights)
y = torch.empty((num_tokens, hidden), dtype=torch.bfloat16, device="cuda")
deep_gemm.fp8_fp4_mega_moe(y, w1, w2, buffer)'''
PTR = '''// Equivalent address arithmetic, simplified from layout::SymBuffer.
// Every pointer below belongs to the current process's GPU VA space.
local_base = buffer_ptrs[my_rank];
peer_base  = buffer_ptrs[peer_rank];
byte_offset = local_field_ptr - local_base;
peer_field_ptr = peer_base + byte_offset;
// SymBuffer::map implements local_field_ptr + (peer_base - local_base).'''
PULLCODE = '''// Source excerpt: expert rank pulls a source token through a mapped pointer.
const auto src_base_ptr = sym_buffer.map(
    buffer.input_token_buffer.get_data_buffer(src_token_idx).get_base_ptr(),
    current_rank_in_expert_idx);
// The dispatch warp uses src_base_ptr as the global source of tma_load_1d.
// Payload passes through local shared memory into the local L1 token buffer.'''
PUSHCODE = '''// Source excerpt: write one packed segment into the source rank's top-k slot.
const auto dst_token = buffer.combine_token_buffer.get_rank_buffer(dst_topk_idx)
                       .get_data_buffer(dst_token_idx);
// dst_ptr additionally selects the hidden-dimension segment within dst_token.
*sym_buffer.map(dst_ptr, dst_rank_idx) = packed;'''
SYNC = '''// Semantic sketch of the protocol; not a standalone CUDA implementation.
write_peer_payload();
finish_all_local_writers();
store_release_system(peer_ready_flag, launch_tag);

// On the token's source rank:
wait_load_acquire_system(local_ready_flag, launch_tag);
reduce_local_topk_slots_into_y();'''

zh = f'''
<h1>PyTorch 对称内存与 GPU P2P 访问</h1>
<p>在多 GPU 程序中，计算与数据可能位于不同设备。GPU P2P 访问允许本地 kernel 通过已映射的地址读取另一张 GPU 的输入，或向其写入输出。PyTorch 的 Symmetric Memory（对称内存）为这种访问提供了分配、映射和同步接口。</p>
<p>理解对称内存需要区分三个概念：物理存储归属哪张 GPU，kernel 使用的地址映射到哪块存储，以及生产者和消费者按什么顺序访问数据。本文先建立这三个概念之间的关系，再分析双 GPU 程序、CUDA 后端实现和 MegaMoE 的设备侧通信。</p>

<h2 id="zh-what">1. 对称内存的编程模型</h2>
<h3 id="zh-symmetric">1.1 缓冲区归属与地址计算</h3>
<p>对称内存由一组分布在不同 rank 上的缓冲区组成。每个 rank 各自分配显存，对应的缓冲区具有相同的大小、dtype 和字段布局。各 rank 按相同顺序参与 rendezvous，交换分配信息并建立 peer 映射。完成后，一个 rank 的 kernel 就可以访问组内其他 rank 的对应缓冲区。</p>
<p>每块缓冲区保留自己的物理存储和数据内容，各进程也独立管理虚拟地址。对称性体现在共同的布局约定：同一字段在各缓冲区中占据相同的相对位置。设 rank r 的缓冲区在当前进程中的映射基址为 B[r]，字段的字节偏移为 δ，则字段地址为 <code>B[r] + δ</code>。选择不同的 r，便得到该字段在不同 GPU 上的映射地址。</p>
{diagram('zh')}
<p>图中，GPU 0 执行读取，GPU 1 持有数据。Rank 0 通过本进程中的 peer 地址发起 load，硬件沿着映射和互联路由访问 GPU 1 的显存。地址的有效性由初始化阶段建立，数据传输则发生在 kernel 执行访问时。<a href="gpu-peer-to-peer-memory.html#zh-kernel">《GPU P2P 显存访问》第一章</a>介绍了这一硬件访问过程。</p>

<h3 id="zh-interfaces">1.2 接口职责与访问阶段</h3>
<p>PyTorch 将一次 peer 访问分为资源初始化和数据访问两个阶段。初始化阶段创建本地 Tensor，通过 rendezvous 建立 peer 映射，并取得可传入 kernel 的 Tensor view。数据访问阶段由程序安排输入生成、peer 读取和缓冲区复用。两类操作的职责如下。{PYAPI} · {VIEW}</p>
<table><thead><tr><th>操作</th><th>产生的对象或状态</th><th>程序中的用途</th></tr></thead><tbody>
<tr><td><code>symm_mem.empty</code></td><td>由 symmetric allocator 管理的本地 Tensor</td><td>为后续 rendezvous 提供可共享的分配</td></tr>
<tr><td><code>rendezvous</code></td><td>包含 peer 映射、指针和同步接口的 handle</td><td>建立组内访问关系</td></tr>
<tr><td><code>get_buffer</code></td><td>指向已有 peer 存储的 Tensor view</td><td>向本地 kernel 提供输入或输出地址</td></tr>
<tr><td>Kernel 与同步操作</td><td>数据读写及生产、消费之间的执行顺序</td><td>完成计算，并协调可见性和缓冲区复用</td></tr>
</tbody></table>
<p>peer view 与远端缓冲区共享同一份物理数据，payload 在 kernel 访问时通过 GPU 互联传输。程序因此可以将远端读取与计算放入同一个 kernel，或将计算结果直接写入 peer 的目标区域。跨 rank 的数据竞争由程序的同步协议处理；训练算子还需要定义对应的反向通信与 autograd 接口。</p>

<h2 id="zh-example">2. 双 GPU P2P 访问示例</h2>
<p>考虑两个 rank，每个 rank 使用一张 GPU，并分配包含 1025 个 float 的输入 x 和同样大小的本地输出 y。在第 step 轮，rank 0 将 x 填为 step，rank 1 将 x 填为 10 + step。每张 GPU 读取另一张 GPU 的 x，将各元素加一后写入自己的 y。这个例子同时包含远端读取、本地计算和跨轮次缓冲区复用。</p>

<h3 id="zh-host">2.1 内存初始化</h3>
<p>程序先选定 CUDA symmetric-memory backend，再创建 x 并调用 rendezvous。返回的 handle 用于取得另一 rank 的 Tensor view：<code>get_buffer(1 - rank, x.shape, x.dtype)</code>。输出 y 由本地分配提供。以下代码将初始化与三轮访问放在一起，展示这些对象的使用关系。</p>
{snippet('access')}
<p>peer 的 device 是发起访问的当前 CUDA device，物理数据则位于另一张 GPU。把 peer 传给 kernel 后，kernel 在本地设备上执行，使用 peer 携带的地址读取远端显存。原始 Tensor x、handle 和 peer view 在整个访问期间保持存活。</p>

<h3 id="zh-kernel">2.2 远端读取 Kernel</h3>
<p>kernel 对输入指针执行逐元素读取，并将加一结果写入本地输出。这里 src 对应前面构造的 peer view，dst 对应 y。</p>
{snippet('kernel')}
<p><code>tl.load(src + i)</code> 发出的访问由已有映射、设备权限和互联路由解析到 peer 显存。通信 API 的作用已在初始化阶段体现为这个可用地址。load 和加一在同一个 Triton kernel 中完成，计算直接消费远端数据，省去了单独的整块 staging 拷贝。1025 个元素使最后一个 block 只包含部分有效索引，由 mask 限制访问范围。</p>

<h3 id="zh-ordering">2.3 执行顺序与缓冲区生命周期</h3>
<p>一轮访问包含两个跨 rank 依赖：读取必须发生在所有输入准备完成之后，下一轮写入必须发生在所有旧输入读取完成之后。代码中的两次 <code>hdl.barrier</code> 分别建立这两个顺序。</p>
<table><thead><tr><th>阶段</th><th>当前 rank 的操作</th><th>建立的顺序</th></tr></thead><tbody>
<tr><td>输入生成</td><td><code>x.fill_</code></td><td>在当前 stream 上写入本轮输入</td></tr>
<tr><td>输入就绪</td><td>第一次 <code>hdl.barrier</code></td><td>所有 rank 的输入准备完毕后开始 peer 读取</td></tr>
<tr><td>读取与计算</td><td><code>peer_read_add_one</code></td><td>读取 peer 的 x，生成本地 y</td></tr>
<tr><td>读取完成</td><td>第二次 <code>hdl.barrier</code></td><td>所有 peer 读取结束后允许下一轮覆盖 x</td></tr>
</tbody></table>
<p>在 PyTorch v2.9.0 的 CUDA backend 中，<code>hdl.barrier</code> 将使用 signal pads 的同步 kernel 排入当前 CUDA stream。Python 调用完成入队后返回，GPU 按 stream 顺序执行 barrier。同一 channel 上的 barrier 调用顺序须在所有 rank 中一致。多 stream 程序还需要用 event 或 stream wait 连接生产者、barrier 和消费者，形成完整依赖链。{BARRIER}</p>
<p><code>torch.cuda.synchronize()</code> 等待本进程当前设备上的工作，代码用它保证本地数值检查发生在 kernel 完成之后。跨 rank 的读取完成由第二次 handle barrier 协调。三轮访问结束后，所有 rank 再次会合，随后释放 peer view、handle 和原始 Tensor。缓冲区的复用和释放都以本地及远端访问完成为条件。</p>

<h3 id="zh-launch">2.4 执行环境与预期结果</h3>
<p>示例使用 Linux 单机、两个进程和两张支持双向 P2P 的 NVIDIA GPU。安装 PyTorch 2.9.0 对应的 CUDA wheel 与 Triton 后，可以通过 <code>nvidia-smi topo -m</code> 和设备 P2P 能力查询检查拓扑；VMM 导入还依赖驱动、PyTorch 构建和容器权限。下载<a href="../assets/pytorch-internals/symmetric-memory/p2p_read.py" download>完整 p2p_read.py</a>后运行：</p>
{code('CUDA_VISIBLE_DEVICES=0,1 torchrun --standalone --nproc-per-node=2 p2p_read.py', 'bash')}
<p>完整脚本在创建进程组前设置 CUDA device，在首次 symmetric allocation 前选择 backend。为沿用独立分配的地址模型，脚本在导入 torch 前关闭新版 PyTorch 引入的 implicit pool。对称内存位于仍在演进的下划线模块中，迁移版本时应核对接口签名和 backend 行为。</p>
<p>三轮访问后，按代码推算，rank 0 的 y 全为 13，rank 1 的 y 全为 3。示例已按源码核对并通过语法检查，双 GPU 执行验证尚未完成。</p>

<h2 id="zh-internals">3. CUDA 后端的内存分配与地址映射</h2>
<p>第二章中的 peer 指针来自一组资源建立操作。CUDA backend 先创建可共享的物理分配，再交换分配句柄，将 peer 显存映射到当前进程的 GPU 地址空间，最后包装为 Tensor view。下面沿这条调用链分析各层接口。</p>

<h3 id="zh-call-chain">3.1 物理显存分配</h3>
{code(HOST)}
<p>Python 的 <code>empty</code> 调用 <code>_SymmetricMemory.empty_strided_p2p</code>，进入对应 allocator。CUDA allocator 计算数据区与 signal pad 所需空间，查询 allocation granularity，按粒度对齐后通过 <code>cuMemCreate</code> 创建物理分配。分配属性中的 <code>CU_MEM_ALLOCATION_TYPE_PINNED</code> 与 DEVICE location 共同描述 GPU 物理存储。{PYAPI} · {ALLOC}</p>
<p>分配句柄表示这块存储，虚拟地址则由地址预留和映射操作提供。Owner 为本地访问建立映射；其他 rank 在导入句柄后，为同一块物理存储建立各自的映射。</p>

<h3 id="zh-handle-exchange">3.2 句柄交换与 Peer 映射</h3>
<p><code>rendezvous</code> 解析 ProcessGroup、登记组信息，并进入 C++ 的句柄交换流程。同一主机内使用 POSIX FD 时，Store 负责交换 rendezvous 元数据，<code>IpcChannel</code> 通过 Unix socket 的 <code>SCM_RIGHTS</code> 传递文件描述符。接收进程由此获得自己的有效 FD，再将它导入为 allocation handle。FD 整数是进程内编号，这里的资源传递依赖操作系统对文件描述符的处理。{RDV} · {link(C10+'CUDASymmetricMemoryUtils.cpp#L91-L176','FD 传递实现')}</p>
<p>CUDA Driver 的调用过程可概括为下面的顺序示意，其中省略了类型声明和错误处理：</p>
{code(VMM, 'cpp')}
<p>{MAP} 用 <code>cuMemAddressReserve</code> 预留虚拟地址，用 <code>cuMemMap</code> 将 allocation 映射到该地址，再用 <code>cuMemSetAccess</code> 设置当前 GPU 对这段地址的访问权限。物理存储、地址范围和设备权限由这些操作分别建立。映射完成后，peer buffer 的地址就可以进入 handle 的指针表。</p>

<h3 id="zh-peer-view">3.3 Tensor View 与访问偏移</h3>
<p><code>get_buffer</code> 从 peer 指针表取出基址，加上请求的偏移，检查访问范围，再用 <code>at::for_blob</code> 构造 Tensor view。这个 view 引用已有 peer 存储，数据由使用它的 kernel 读取或写入。<code>get_buffer</code> 的 storage_offset 以元素为单位：对于 float32，offset=4 对应 16 字节。{VIEW}</p>
<p>本文示例使用独立分配。较新的池化或子分配实现还需要处理 Tensor 相对 allocation 的偏移，迁移时应结合对应版本的 <code>get_remote_tensor</code> 等接口计算地址。peer view 的有效期依赖原始分配和映射 handle，因此程序需要将三者保留到所有访问结束。</p>
<p>地址映射落实到页表与硬件寻址的过程，可参照<a href="gpu-peer-to-peer-memory.html#zh-pte">《GPU P2P 显存访问》第二章</a>。该文以 P100 的 PTE 位域说明地址转换；具体字段格式属于对应硬件代际。</p>

<h3 id="zh-compare">3.4 CUDA IPC 与 VMM 接口对照</h3>
<p>上一篇从 CUDA 程序的角度建立 peer 访问。PyTorch CUDA backend 将同类资源管理封装在 allocator 和 rendezvous 中，使用 VMM 完成分配与映射。各项职责可以按下表对应。</p>
<table><thead><tr><th>职责</th><th>上一篇的 CUDA 示例</th><th>PyTorch v2.9.0 CUDA backend</th></tr></thead><tbody>
<tr><td>同进程的访问授权</td><td><a href="gpu-peer-to-peer-memory.html#zh-single-process">cudaMalloc + cudaDeviceEnablePeerAccess</a></td><td>VMM 分配使用 cuMemSetAccess 对映射区授权</td></tr>
<tr><td>节点内跨进程共享</td><td><a href="gpu-peer-to-peer-memory.html#zh-ipc">cudaIpcGetMemHandle / cudaIpcOpenMemHandle</a></td><td>cuMemExportToShareableHandle / cuMemImportFromShareableHandle，使用 POSIX FD 类型</td></tr>
<tr><td>跨受支持 fabric 共享</td><td><a href="gpu-peer-to-peer-memory.html#zh-fabric-mapping">VMM + CU_MEM_HANDLE_TYPE_FABRIC</a></td><td>具备 fabric 支持及相应系统配置时使用 fabric handle</td></tr>
<tr><td>Kernel 数据访问</td><td>对映射地址执行 load/store</td><td>get_buffer 或 buffer_ptrs 提供 peer 映射地址</td></tr>
<tr><td>可见性与缓冲区复用</td><td>访问方与 owner 协调同步和生命周期</td><td>程序用 handle 的 barrier / signal 接口安排生产、消费与复用顺序</td></tr>
</tbody></table>

<h3 id="zh-backends">3.5 后端与通信域</h3>
<p>PyTorch v2.9.0 的接口可以选择 CUDA、NVSHMEM 或 NCCL backend，具体能力由构建、库版本和硬件决定。本文的 CUDA 路径使用 VMM 映射支持直接 peer load/store，其访问范围取决于映射所覆盖的 GPU 通信域。</p>
<p>在支持 Multi-Node NVLink 的系统中，fabric handle 可作为句柄数据在节点间交换，导入依赖可互访的硬件拓扑和 IMEX 配置；具体过程见<a href="gpu-peer-to-peer-memory.html#zh-fabric-mapping">上一篇的跨节点映射</a>。普通 RDMA 网络上的远端显存访问则由相应网络通信机制完成。kernel 使用的 <code>tl.load</code> 地址始终需要是当前进程、当前访问设备可用的映射地址。</p>

<h3 id="zh-multicast">3.6 Multicast 映射</h3>
<p>设备支持时，CUDA symmetric memory 还可能建立 multicast 映射，供适配的多播／归约 kernel 使用。第二章的读取路径使用 unicast peer pointer，每次访问指向一个 peer。PyTorch 初始化时可能同时尝试可用的 multicast 优化，具体 kernel 选择哪种地址决定其访问方式。</p>

<h2 id="zh-megamoe">4. MegaMoE 中的通信与计算融合</h2>
<h3 id="zh-projects">4.1 MoE 数据流</h3>
<p>在 expert parallel MoE 中，token 位于 source rank，目标 expert 的权重分布在不同 rank 上。一次计算包含 dispatch、两层线性变换 L1 和 L2、两层之间的 SwiGLU，以及将专家输出返回 source 的 combine。通信与计算的组织取决于输入和权重的分布。</p>
<p>本章分析 DeepGEMM 中的 MegaMoE。DeepGEMM 提供计算 kernel，DeepEP 提供 expert parallel 通信；官方测试将 DeepEP dispatch → GEMM → combine 组成的非融合流程作为 baseline，与 MegaMoE 比较。{TEST}</p>
<p>MegaMoE 将上述阶段合并到一个 mega-kernel，由不同 warp 分工并按 tile 推进，使 NVLink 数据传输与 Tensor Core 计算重叠。token 和结果仍经 GPU 互联传输，性能收益取决于负载、路由、形状与硬件。下图表示一个 source rank 与 expert rank 之间的数据流。{link(DG+'README.md#mega-moe','DeepGEMM Mega MoE 接口说明')}</p>
<pre class="code"><code>source rank A                     expert rank B
symmetric input x  ── peer pull ──► local L1 token ring
                                   L1 GEMM → SwiGLU → L2 GEMM
combine[token, topk_slot] ◄─ store ─ expert result
wait ready → reduce top-k → y</code></pre>

<h3 id="zh-mega-buffer">4.2 共享缓冲区布局</h3>
<p>MegaMoE 将输入、路由信息和通信 workspace 放入一块具有统一字段布局的缓冲区。多 rank 情况下，Python 的 <code>SymmBuffer</code> 用 <code>symm_mem.empty(num_bytes, dtype=torch.int8)</code> 分配 workspace，调用 rendezvous，并保留 <code>handle.buffer_ptrs</code>。单 rank 情况使用 torch.empty。{BUF}</p>
<p>C++ 布局函数计算字段大小与偏移，Python 为 x、x_sf、topk_idx、topk_weights 等字段创建输入 view。其余空间容纳控制信号、token ring、中间结果和 combine 数据。专家权重保存在所属 rank，通信围绕输入、路由信息和专家输出展开。{LAYOUT}</p>
<p>下面的调用示意展示 buffer 的准备和使用。调用前，输入需要完成对应版本要求的量化、scale 编码和权重布局转换；官方测试包含这些准备步骤和 reference 对比。{TEST}</p>
{code(MEGAHOST)}
<p>Python wrapper 将 <code>sym_buffer.buffer</code>、<code>sym_buffer.handle.buffer_ptrs</code>、rank 和形状参数传给 C++，后者构造布局并准备 JIT kernel。布局参数确定字段位置，peer 指针表确定各 rank 缓冲区在当前进程中的基址。{WRAP}</p>

<h3 id="zh-peer-map">4.3 Peer 地址计算</h3>
<p><code>layout::SymBuffer</code> 将第一章的基址加偏移模型用于设备侧寻址。它保存本 rank 的映射基址，以及各 peer 基址相对该地址的差值。对于指向某个本地字段的 ptr，<code>map(ptr, dst_rank)</code> 加上目标 rank 的基址差值，便得到同一字段的 peer 地址。{SYMPTR}</p>
{code(PTR, 'cpp')}
<p><code>buffer_ptrs</code> 中保存的都是当前进程已导入的 GPU 地址，字段偏移由各 rank 共同的布局确定。因而，本地与远端缓冲区可以具有不同的虚拟地址数值，同时使用相同的字段定位逻辑。</p>

<h3 id="zh-dispatch">4.4 Dispatch 输入传输</h3>
<p>在本文所用的 SM100 FP8/FP4 实现中，dispatch 先按路由统计各 expert 接收的 token，向 peer workspace 写入 source token/top-k 索引与计数，再通过 NVLink barrier 协调元数据就绪。expert rank 根据这些信息定位 token 来源，并从 source rank 拉取 payload。这个阶段由元数据 push 和 payload pull 组成。{link(MEGA+'impls/sm100_fp8_fp4_mega_moe.cuh#L370-L433','路由元数据与 barrier')}</p>
{code(PULLCODE, 'cpp')}
<p><code>sym_buffer.map</code> 计算远端全局地址。dispatch warp 使用一维 TMA load 将 token 分块读入本地 shared memory，再写到本地 L1 token ring，供 GEMM 消费。dispatch 还读取量化 scale 和路由权重，并保存 <code>(source_rank, source_token, topk_slot)</code>，作为输出写回的地址信息。ring 槽位在先前 GEMM 消费完成后复用。{PULL}</p>

<h3 id="zh-combine">4.5 Combine 输出写回与归约</h3>
<p>L2 epilogue 根据保存的 source metadata，将专家结果直接写入 token 原属 rank 的 combine buffer。每条 top-k 路径对应一个独立槽位，expert rank 写入该槽位，source rank 等待相关 peer 完成后，在本地归约这些结果并生成 y。多个 expert 的输出通过槽位分离，再由本地归约合并；本文路径以此取代对 y 的远端 atomicAdd。{PUSH} · {READY}</p>
{code(PUSHCODE, 'cpp')}
<p>这次写回使用与 dispatch 相同的寻址方法：先由布局确定目标 token 和 top-k slot，再由 peer 基址确定目标 rank 的存储。两次传输的方向相反，地址计算都遵循共同的缓冲区布局。</p>

<h3 id="zh-kernel-sync">4.6 设备侧同步与缓冲区复用</h3>
<p>计算与通信融合后，kernel 内部需要协调多个执行范围。rank 间使用 NVLink barrier 和 system-scope 信号；同一 GPU 上的 CTA 与 warp 通过任务计数、ring 就绪状态和 grid sync 协作；TMA、shared memory、Tensor Memory 与 MMA 之间还有各自的完成和复用依赖。<code>__syncthreads()</code> 则用于一个 CTA 内的线程同步。</p>
<p>combine 的完成协议体现了这些层次之间的关系。所有本地 L2 writer 先经 grid sync 会合，再使用 <code>ptx::st_rel_sys</code> 向目标 rank 发布 readiness tag。source rank 用 <code>ptx::ld_acq_sys</code> 等待本次 launch 对应的 tag，随后读取本地 combine slots。tag 与 grid index 关联，使本轮完成状态能够与历史状态区分。下面用伪代码表示这一顺序。{READY}</p>
{code(SYNC, 'cpp')}
<p>实际实现还用 mbarrier、fence 和 wait 协调 TMA 异步代理与 shared memory 复用。writer 会合、release/acquire 信号和这些异步操作的完成关系，共同构成数据发布与消费的协议。{link(MEGA+'comm/barrier.cuh','NVLink / grid barrier 实现')}</p>
<p>第二章通过每轮两次全组 barrier 保护输入的生产与复用。MegaMoE 将同样的依赖细化到 kernel 内部的任务和流水阶段，使通信与计算可以交叠执行。初始化时建立的共享布局和 peer 映射，为这些设备侧操作提供持续有效的地址。</p>

<h3 id="zh-sources">实现版本与源码索引</h3>
<p>API 与 CUDA backend 源码基于 PyTorch <strong>v2.9.0</strong>，MegaMoE 源码基于 DeepGEMM <strong>5081f8513af5</strong>，核对日期为 2026-11-10。第四章分析的 SM100 kernel 使用 Blackwell 架构，并有对应的软件版本要求。</p>
<ol><li>{PYAPI} → {ALLOC} → {RDV} → {MAP}：从 Python 接口到 CUDA 分配和映射。</li><li>{VIEW} → {BARRIER}：Tensor view 的构造与 stream 上的同步。</li><li>{BUF} → {WRAP} → {SYMPTR}：MoE workspace、kernel 参数与 peer 地址计算。</li><li>{PULL} → {PUSH} → {READY} → {TEST}：数据传输、完成信号与 reference 验证。</li></ol>
'''

en = f'''
<h1>PyTorch Symmetric Memory and GPU P2P Access</h1>
<p>GPU P2P access lets a kernel read or write memory owned by another GPU through an address mapped into the calling process. PyTorch <strong>Symmetric Memory</strong> provides the allocation, rendezvous, peer pointers, and synchronization interfaces needed to build this access into a compute kernel.</p>
<p>The programming model has three parts: each rank owns a buffer, mappings make peer buffers addressable, and synchronization orders production, consumption, and reuse. The following chapters develop this model with a two-GPU example, trace its CUDA implementation, and apply it to the fused communication and computation in MegaMoE.</p>

<h2 id="en-what">1. Programming Model</h2>
<h3 id="en-symmetric">1.1 Buffer Ownership and Addressing</h3>
<p>Each rank allocates a buffer on its GPU and participates in rendezvous in the same order. Corresponding buffers have the same size, dtype, and field layout. Rendezvous establishes peer mappings, after which each rank can obtain an address for every accessible peer buffer. Physical storage and data remain separately owned by their respective ranks.</p>
<p>Each process has its own virtual addresses. Let B[r] be the address at which rank r's buffer is mapped in the calling process, and let δ be a field's byte offset within that buffer. The field's peer address is <code>B[r] + δ</code>. The shared layout gives δ the same meaning across ranks, so a kernel can translate a local field position into its peer counterpart even when the base addresses differ.</p>
{diagram('en')}
<h3 id="en-interfaces">1.2 Interface Responsibilities</h3>
<p>Allocation creates local storage; rendezvous makes peer storage addressable; a Tensor view packages an address for a kernel. The caller then establishes the execution order for each use of that storage.</p>
<table><thead><tr><th>Interface</th><th>Result</th><th>Use</th></tr></thead><tbody>
<tr><td><code>symm_mem.empty</code></td><td>A local Tensor backed by a symmetric allocator</td><td>Participate in rendezvous to establish peer mappings</td></tr>
<tr><td>Rendezvous handle</td><td>Peer mappings, pointers, and synchronization interfaces</td><td>Order production, consumption, and reuse</td></tr>
<tr><td><code>get_buffer</code></td><td>A Tensor view that aliases mapped peer storage</td><td>Pass the view to a kernel while preserving the mapping's lifetime</td></tr>
<tr><td>Custom kernel</td><td>Reads and writes through mapped peer addresses</td><td>Define race-free access and, for training, backward communication</td></tr>
</tbody></table>
<p>A kernel can consume peer data while computing or write an output directly into a peer destination. The ordinary load/store access behind this model is described in <a href="gpu-peer-to-peer-memory.html#en-kernel">GPU peer-to-peer memory access, chapter 1</a>. PyTorch supplies the allocation and address interfaces through {PYAPI} and {VIEW}.</p>

<h2 id="en-example">2. Two-GPU P2P Example</h2>
<p>Consider two ranks, each with an input buffer of 1025 float values. At iteration step, rank 0 fills its input with step and rank 1 with 10 + step. Each rank reads the other rank's input, adds one, and stores the result in a local output y. The kernel uses blocks of 256 elements, so the final block also exercises the mask for the partial block.</p>
<h3 id="en-host">2.1 Memory Initialization</h3>
<p>The script selects the local CUDA device before creating the process group and selects the symmetric allocator backend before the first symmetric allocation. It then creates x, establishes peer mappings, obtains the other rank's view, and allocates a local output. The following host code also contains the execution loop:</p>
{snippet('access')}
<p>The peer view's device is the <strong>calling rank's CUDA device</strong>, which issues the memory access. Its storage resides on the other GPU. The handle and the original Tensor retain the resources used by this view throughout the loop.</p>
<h3 id="en-kernel">2.2 Peer-Read Kernel</h3>
{snippet('kernel')}
<p>The src argument is the peer view's mapped address. Each <code>tl.load(src + i)</code> follows that mapping to the peer GPU, and the corresponding store writes the computed value into local y. Mapping and permissions are established before launch, so each load can use the pointer directly. The load generates inter-GPU traffic while the addition executes in the same kernel, eliminating a separate full-buffer staging copy before computation.</p>
<h3 id="en-ordering">2.3 Execution Order and Buffer Lifetime</h3>
<p>The two barriers enforce distinct dependencies. The first publishes each rank's input before peer consumption. The second completes peer consumption before the next iteration overwrites that input.</p>
<table><thead><tr><th>Order</th><th>Action</th><th>Dependency</th></tr></thead><tbody>
<tr><td>1</td><td>Fill x</td><td>Produce this iteration's input on the current stream</td></tr>
<tr><td>2</td><td>First handle barrier</td><td>Publish inputs before peer reads</td></tr>
<tr><td>3</td><td>Peer load and addition</td><td>Read remote input and write local y</td></tr>
<tr><td>4</td><td>Second handle barrier</td><td>Complete all peer reads before reusing x</td></tr>
</tbody></table>
<p>In the CUDA backend examined here, <code>hdl.barrier</code> enqueues a signal-pad synchronization kernel on the current CUDA stream. The Python call submits that work; completion follows GPU execution. All ranks issue calls for the same channel in matching order. When several streams participate, events or stream waits must connect the producer, barrier, and consumer to establish the required dependencies. {BARRIER}</p>
<p><code>torch.cuda.synchronize()</code> waits for this process's current device. The cross-rank handle barriers coordinate peer access, and the local device wait makes the output ready for validation. The complete script executes three iterations, coordinates teardown across ranks, and retains the original Tensor, handle, and peer view until their local and remote uses have finished.</p>
<p>A peer view aliases an existing allocation, so its lifetime depends on that allocation and mapping. Training operators also need explicit backward communication and autograd integration for accesses across ranks.</p>
<h3 id="en-launch">2.4 Execution Environment</h3>
<p>The example assumes Linux, two processes on one host, one NVIDIA GPU per process, and mutual P2P access. Use a CUDA PyTorch 2.9.0 installation with matching Triton. Inspect topology with <code>nvidia-smi topo -m</code> and check device peer-access capabilities. Successful VMM import additionally depends on driver support, the PyTorch build, and container permissions.</p>
<p>Download <a href="../assets/pytorch-internals/symmetric-memory/p2p_read.py" download>p2p_read.py</a> and run:</p>
{code('CUDA_VISIBLE_DEVICES=0,1 torchrun --standalone --nproc-per-node=2 p2p_read.py', 'bash')}
<p>For newer PyTorch builds, the script disables the later implicit memory pool before importing torch, retaining the dedicated-allocation model used here. The underscored interface is evolving; version upgrades require checking its signatures and backend behavior.</p>
<p>After three iterations, the expected output is 13 on rank 0 and 3 on rank 1. The example has been checked against source; two-GPU execution remains unverified. These values are expectations derived from the program.</p>

<h2 id="en-internals">3. CUDA Allocation and Address Mapping</h2>
<h3 id="en-call-chain">3.1 Physical Allocation</h3>
<p>The host interface separates allocation, rendezvous, and view creation:</p>
{code(HOST)}
<p><code>empty</code> calls <code>_SymmetricMemory.empty_strided_p2p</code>. The CUDA allocator calculates the space for the data buffer and signal pads, rounds it to the queried allocation granularity, and creates the physical allocation. PINNED allocation type together with DEVICE location describes GPU allocation in this path. {PYAPI} · {ALLOC}</p>
<h3 id="en-handle-exchange">3.2 Handle Exchange and Peer Mapping</h3>
<p><code>rendezvous</code> resolves the process group, registers its information, and enters C++. The owner maps its allocation locally, while each peer imports the allocation handle and establishes a mapping in its own address space. Allocation, address reservation, mapping, and device authorization are separate steps in this sequence:</p>
{code(VMM, 'cpp')}
<p>The sequence sketch omits type declarations and error handling. The {MAP} helper reserves virtual address space with <code>cuMemAddressReserve</code>, maps the allocation with <code>cuMemMap</code>, and grants access with <code>cuMemSetAccess</code>.</p>
<p>A POSIX file descriptor is a process-local resource number. This implementation exchanges rendezvous metadata through a Store and transfers usable descriptors through Unix sockets with <code>SCM_RIGHTS</code>. The receiver obtains its own descriptor and imports the allocation. This descriptor transfer is the operation that makes the handle usable in the receiving process. Fabric handles can be exchanged as handle data under their corresponding reachability requirements. {RDV} · {link(C10+'CUDASymmetricMemoryUtils.cpp#L91-L176','FD transfer')}</p>
<h3 id="en-peer-view">3.3 Tensor Views and Access Offsets</h3>
<p><code>get_buffer</code> adds an offset to an existing peer pointer, checks the requested size, and constructs a Tensor view with <code>at::for_blob</code>. View creation wraps the mapping; the Triton kernel performs the payload read when it executes.</p>
<p>The storage_offset argument is measured in elements: four float32 elements correspond to 16 bytes. Newer pooled or suballocated buffers also carry an offset within their underlying allocation. Code using those paths should use the offset semantics of its PyTorch version, including interfaces such as <code>get_remote_tensor</code>. {VIEW}</p>
<p>The address translation behind the mapped pointer is discussed in <a href="gpu-peer-to-peer-memory.html#en-pte">P100 page tables in the previous article</a>. Its PTE bit fields describe the P100 generation; the page-table example is scoped to that hardware.</p>
<h3 id="en-compare">3.4 CUDA IPC and VMM Interfaces</h3>
<table><thead><tr><th>Task</th><th>Previous CUDA example</th><th>PyTorch v2.9.0 CUDA backend</th></tr></thead><tbody>
<tr><td>Authorize ordinary same-process allocations</td><td><a href="gpu-peer-to-peer-memory.html#en-single-process">cudaMalloc + cudaDeviceEnablePeerAccess</a></td><td>VMM uses cuMemSetAccess for the mapped region</td></tr>
<tr><td>Share within a host</td><td><a href="gpu-peer-to-peer-memory.html#en-ipc">cudaIpcGetMemHandle / cudaIpcOpenMemHandle</a></td><td>Export/import shareable handles with POSIX FD type</td></tr>
<tr><td>Share across a supported NVLink fabric</td><td><a href="gpu-peer-to-peer-memory.html#en-fabric-mapping">VMM + FABRIC handles</a></td><td>Can select fabric handles when supported and configured</td></tr>
<tr><td>Access from a kernel</td><td>Load/store through a mapped pointer</td><td>Peer views or buffer_ptrs supply mapped pointers</td></tr>
<tr><td>Visibility and reuse</td><td>Coordinate owner and reader</td><td>Schedule handle barriers/signals around production, consumption, and reuse</td></tr>
</tbody></table>
<h3 id="en-backends">3.5 Backends and Communication Domains</h3>
<p>The v2.9.0 interface supports selecting CUDA, NVSHMEM, or NCCL, subject to build, library, and hardware capabilities. This article selects CUDA and follows direct peer access through VMM mappings.</p>
<p>Communication domains determine how a peer allocation can be reached. Ordinary RDMA-connected hosts access remote GPU memory through network communication mechanisms. A local <code>tl.load</code> requires an address valid in the calling process's GPU address space. Supported Multi-Node NVLink fabrics extend mapped access under specific hardware and IMEX conditions; see <a href="gpu-peer-to-peer-memory.html#en-fabric-mapping">the fabric mapping workflow</a>.</p>
<h3 id="en-multicast">3.6 Multicast Mapping</h3>
<p>On suitable hardware, CUDA symmetric memory can also establish multicast mappings for kernels that use them. Initialization may attempt these supported optimizations. The two-GPU kernel in this article uses a unicast peer pointer and reads one peer buffer.</p>

<h2 id="en-megamoe">4. Communication and Computation in MegaMoE</h2>
<h3 id="en-projects">4.1 MoE Data Flow and Kernel Fusion</h3>
<p>In an expert-parallel MoE layer, tokens originate on source ranks and expert weights reside on expert ranks. The data path consists of dispatch, two linear transformations L1 and L2 with SwiGLU between them, and combine. MegaMoE fuses these phases into one mega-kernel, using specialized warps and tile-level progress to overlap NVLink input/output transfers with Tensor Core computation. Performance depends on routing, tensor shapes, load, and hardware. {link(DG+'README.md#mega-moe','Mega MoE interface')}</p>
<p>The implementation examined here belongs to <strong>DeepGEMM</strong>, whose test compares it with a non-fused dispatch → GEMM → combine baseline using <strong>DeepEP</strong> for expert-parallel communication. {TEST}</p>
<pre class="code"><code>source rank A                     expert rank B
symmetric input x  ── peer pull ──► local L1 token ring
                                   L1 GEMM → SwiGLU → L2 GEMM
combine[token, topk_slot] ◄─ store ─ expert result
wait ready → reduce top-k → y</code></pre>
<p>This chapter follows the pinned SM100 implementation, with its Blackwell hardware and software requirements.</p>
<h3 id="en-mega-buffer">4.2 Shared Buffer Layout</h3>
<p>For multiple ranks, Python's <code>SymmBuffer</code> allocates an int8 workspace with <code>symm_mem.empty</code>, calls rendezvous, and retains <code>handle.buffer_ptrs</code>. A C++ layout function calculates field sizes and offsets. Python creates input views for x, x_sf, topk_idx, and topk_weights; the other fields hold control signals, token rings, intermediate results, and combine slots. A single-rank run uses torch.empty. {BUF} · {LAYOUT}</p>
<p>The call site below assumes inputs have already been quantized and their scales and weights arranged in the required formats. Preparation from BF16 inputs and reference checks are included in the official test.</p>
{code(MEGAHOST)}
<p>The Python wrapper passes the workspace, buffer_ptrs, rank, and dimensions to C++, which constructs layouts and launches the JIT kernel. Expert weights stay on their owning rank while the kernel exchanges token data and results. {WRAP} · {TEST}</p>
<h3 id="en-peer-map">4.3 Peer Address Calculation</h3>
<p><code>layout::SymBuffer</code> stores the current rank's base and each peer base's difference from it. The map method adds that difference to a local field pointer, preserving the field's offset within the shared layout:</p>
{code(PTR, 'cpp')}
<p>Every address in buffer_ptrs is a valid imported address in the <strong>calling process</strong>. These mapped bases and the common field offsets provide the address translation even when the processes use different virtual addresses. {SYMPTR}</p>
<h3 id="en-dispatch">4.4 Dispatch Input Transfer</h3>
<p>The pinned SM100 FP8/FP4 implementation first counts routed tokens and pushes source-token/top-k indices and counts into peer workspaces. An NVLink barrier coordinates this metadata phase. Expert ranks then use the metadata to locate source tokens and pull their payloads. {link(MEGA+'impls/sm100_fp8_fp4_mega_moe.cuh#L370-L433','Routing metadata and barrier')}</p>
{code(PULLCODE, 'cpp')}
<p>The mapped global address becomes the source of a one-dimensional TMA load into local shared memory, followed by storage into the local L1 token ring. Dispatch also reads scales and routing weights, and saves source rank, token index, and top-k slot for write-back. Reusing a ring slot requires completion of its prior GEMM consumers. {PULL}</p>
<h3 id="en-combine">4.5 Combine Write-Back and Reduction</h3>
<p>The L2 epilogue uses saved source metadata to write results directly into the token owner's combine buffer. Each top-k path has a separate slot. The source waits for participating peers and reduces its local slots into y. This separates expert writes by destination slot and performs their accumulation locally, avoiding conflicting overwrites and remote atomicAdd into y along this path. {PUSH} · {READY}</p>
{code(PUSHCODE, 'cpp')}
<h3 id="en-kernel-sync">4.6 Device Synchronization and Buffer Reuse</h3>
<p>The kernel coordinates three scopes of work: rank-level NVLink barriers and system-scope signals; per-GPU CTA/warp tasks and ring counters; and asynchronous TMA, shared-memory, Tensor-Memory, and MMA dependencies. <code>__syncthreads()</code> has CTA scope. Grid synchronization and the rank-level protocol establish dependencies across the broader scopes. The following pseudocode summarizes the protocol:</p>
{code(SYNC, 'cpp')}
<p>For combine, all local L2 writers rendezvous through grid synchronization. A <code>ptx::st_rel_sys</code> then publishes a readiness tag to destination ranks. The source uses <code>ptx::ld_acq_sys</code> to wait for the current launch's tag before reading its local combine slots. The tag is tied to the grid index, distinguishing the completion state of successive launches.</p>
<p>TMA adds asynchronous proxy and shared-memory reuse requirements. The complete implementation combines the release/acquire protocol with mbarriers, fences, and waits to satisfy these dependencies. {READY} · {link(MEGA+'comm/barrier.cuh','NVLink and grid barriers')}</p>
<p>The two-GPU example and MegaMoE both establish allocations and mappings at initialization, address peer fields with base + offset, and explicitly order visibility and reuse. MegaMoE applies this structure at finer granularity: communication, computation, and buffer reuse progress through task and pipeline stages inside the kernel.</p>
<h3 id="en-sources">Implementation Versions and Source Index</h3>
<p class="sm-note">The API and CUDA backend analysis use PyTorch <strong>v2.9.0</strong>. MegaMoE source references use DeepGEMM <strong>5081f8513af5</strong>, inspected on 2026-11-10.</p>
<ol><li>{PYAPI} → {ALLOC} → {RDV} → {MAP}: Python to CUDA mapping.</li><li>{VIEW} → {BARRIER}: peer views and stream synchronization.</li><li>{BUF} → {WRAP} → {SYMPTR}: MoE workspace, arguments, and peer pointers.</li><li>{PULL} → {PUSH} → {READY} → {TEST}: payload, readiness, and reference validation.</li></ol>
'''

meta = {
    'title': 'PyTorch 对称内存与 GPU P2P 访问',
    'title_en': 'PyTorch Symmetric Memory and GPU P2P Access',
    'slug': 'pytorch-symmetric-memory',
    'date': '2026-11-10',
    'tags': 'PyTorch, CUDA, P2P, Symmetric Memory, Triton, MoE',
    'tags_en': 'PyTorch, CUDA, P2P, Symmetric Memory, Triton, MoE',
    'reading': '25 分钟',
    'reading_en': '25 min',
    'summary': 'GPU 直接读对端缓冲区时，读要等对端写好输入，下一轮写入又要等对端读完旧数据。rendezvous 把对端显存映射进本进程，kernel 用普通 load/store 访问。',
    'summary_en': 'Reading peer buffers creates two dependencies: reads wait for inputs, and the next write waits for peers to finish reading. Rendezvous maps peer memory for plain kernel loads and stores.',
    'series': 'pytorch-internals',
    'series_title': 'PyTorch 内部机制',
    'series_title_en': 'PyTorch Internals',
    'series_order': '13',
}
head = '\n'.join(f'<meta name="post:{k}" content="{escape(v, quote=True)}">' for k, v in meta.items())
html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(meta['title'])}</title>
{head}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<style>
.sm-note {{ padding: 16px 20px; border-left: 3px solid var(--accent); background: var(--bg-subtle); }}
.sm-figure {{ overflow-x: auto; color: var(--fg); margin: 32px auto; }}
.sm-figure svg {{ display: block; width: 100%; max-width: 840px; min-width: 640px; height: auto; margin: auto; }}
.sm-figure figcaption {{ text-align: center; color: var(--fg-muted); font-size: 13px; margin-top: 10px; }}
.sm-table {{ overflow-x: auto; margin: 24px auto; }}
.sm-table table {{ margin: 0 auto; }}
</style></head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div></aside><main class="content">
<div class="lang-zh">{zh}</div>
<div class="lang-en">{en}</div>
</main></div></body></html>
'''
# Preserve a scroll container around wider API comparison tables on mobile.
html = html.replace('<table>', '<div class="sm-table"><table>').replace('</table>', '</table></div>')
(ROOT / 'posts/pytorch-symmetric-memory.html').write_text(html, encoding='utf-8')
print('Built posts/pytorch-symmetric-memory.html')
