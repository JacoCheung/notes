#!/usr/bin/env python3
"""Build the bilingual CUPTI memory tracing guide from its runnable examples."""
from html import escape
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/pytorch-internals/cupti-memory'
REV = 'ba56102387ef21a3b04b357e5b183d48f0afefc7'
ALLOC = f'https://github.com/pytorch/pytorch/blob/{REV}/c10/cuda/CUDACachingAllocator.cpp'
CUPTI = 'https://docs.nvidia.com/cupti/12.8/'
VMM = 'https://docs.nvidia.com/cuda/archive/12.8.1/cuda-driver-api/group__CUDA__VA.html'
SOURCES = {
    'overview': (CUPTI+'index.html', 'CUPTI 12.8'),
    'nsys': ('https://docs.nvidia.com/nsight-systems/InstallationGuide/', 'Nsight Systems / CUPTI'),
    'usage': (CUPTI+'main/main.html#callback-api', 'CUPTI Callback usage'),
    'callbacks': (CUPTI+'api/group__CUPTI__CALLBACK__API.html', 'Callback API'),
    'data': (CUPTI+'api/structCUpti__CallbackData.html', 'CUpti_CallbackData'),
    'activity': (CUPTI+'api/group__CUPTI__ACTIVITY__API.html', 'Activity API'),
    'api': (CUPTI+'api/structCUpti__ActivityAPI.html', 'CUpti_ActivityAPI'),
    'memory': (CUPTI+'api/structCUpti__ActivityMemory4.html', 'CUpti_ActivityMemory4'),
    'copy': (CUPTI+'api/structCUpti__ActivityMemcpy6.html', 'CUpti_ActivityMemcpy6'),
    'vmm': (VMM, 'CUDA VMM API'),
    'cache': ('https://docs.pytorch.org/docs/2.8/notes/cuda.html#memory-management', 'PyTorch memory management'),
    'native': (ALLOC+'#L985-L1009', 'cudaMalloc path'),
    'reserve': (ALLOC+'#L375-L392', 'ExpandableSegment: reserve'),
    'create': (ALLOC+'#L399-L484', 'ExpandableSegment: create'),
    'map': (ALLOC+'#L646-L669', 'Map and access'),
    'release': (ALLOC+'#L672-L699', 'Unmap and release'),
    'destroy': (ALLOC+'#L638-L643', 'Release VA range'),
    'pages': (ALLOC+'#L2426-L2440', 'Allocator segment size'),
    'free': (ALLOC+'#L3054-L3097', 'Release cached allocation'),
}


def source(key):
    url, title = SOURCES[key]
    return f'<a href="{url}">{escape(title)}</a>'


def code(text, language='cpp'):
    return f'<pre class="code" data-language="{language}"><code>{escape(text)}</code></pre>'


def svg_text(x, y, text, size=17, anchor='middle', weight=400):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}">{escape(text)}</text>'


def callback_diagram(lang):
    uid = f'{lang}-cupti-callback'
    xs = [125, 500, 875]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 850" role="img" aria-labelledby="{uid}">',
             f'<title id="{uid}">Synchronous ENTER and EXIT callbacks around a CUDA API</title>',
             f'<defs><marker id="{uid}-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="var(--trace-rule)"/></marker></defs>']
    for x, name in zip(xs, ['PyTorch allocator', 'CUDA API', 'CUPTI subscriber']):
        parts.append(f'<path d="M{x} 100 V820" stroke="var(--trace-rule)" stroke-width="1.7" stroke-dasharray="6 5"/>')
        parts.append(f'<rect x="{x-118}" y="24" width="236" height="72" rx="4" fill="var(--trace-fill)" stroke="var(--trace-rule)" stroke-width="2"/>')
        parts.append(svg_text(x, 56, name, 18, weight=600))
        parts.append(svg_text(x, 80, 'same calling CPU thread', 13))
    for actor, start, end in [(0, 140, 775), (1, 140, 775), (2, 212, 275), (2, 492, 705)]:
        parts.append(f'<rect x="{xs[actor]-8}" y="{start}" width="16" height="{end-start}" fill="var(--trace-fill)" stroke="var(--trace-rule)" stroke-width="2"/>')
    steps = [
        (0, 1, 150, 'cudaMalloc / cuMemCreate', 'callbacks', False),
        (1, 2, 220, 'ENTER: save timestamp', 'data', False),
        (2, 1, 270, 'return from callback', 'usage', True),
        (1, 1, 380, 'CUDA executes the API', 'vmm', False),
        (1, 2, 500, 'EXIT: result + parameters', 'data', False),
        (2, 2, 610, 'decode fields; write CSV', 'data', False),
        (2, 1, 700, 'return from callback', 'usage', True),
        (1, 0, 770, 'return status to caller', 'data', True),
    ]
    for a, b, y, label, key, returned in steps:
        x1, x2 = xs[a], xs[b]
        dash = ' stroke-dasharray="6 4"' if returned else ''
        parts.append(f'<a href="{SOURCES[key][0]}" target="_blank" rel="noopener">')
        if a == b:
            direction = -1 if a == 2 else 1
            parts.append(f'<path d="M{x1+8*direction} {y-12} h{46*direction} v24 h{-46*direction}" fill="none" stroke="var(--trace-rule)" stroke-width="1.8" marker-end="url(#{uid}-arrow)"/>')
            mid = x1+direction*180
        else:
            direction = 1 if x2 > x1 else -1
            mid = (x1+x2)/2
            parts.append(f'<path d="M{x1+8*direction} {y} H{x2-10*direction}" fill="none" stroke="var(--trace-rule)" stroke-width="1.8"{dash} marker-end="url(#{uid}-arrow)"/>')
        lines = textwrap.wrap(label, 30)
        width = max(len(line) for line in lines)*8.2+16
        parts.append(f'<rect x="{mid-width/2}" y="{y-22*len(lines)-8}" width="{width}" height="{22*len(lines)+2}" fill="var(--trace-bg)"/>')
        for i, line in enumerate(lines):
            parts.append(svg_text(mid, y-22*(len(lines)-i)+5, line, 16))
        parts.append('</a>')
    parts.append('</svg>')
    return ''.join(parts)


def vmm_diagram(lang):
    uid = f'{lang}-cupti-vmm'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 440" role="img" aria-labelledby="{uid}">',
             f'<title id="{uid}">Virtual reservation, physical handles, and mapping are separate resources</title>']
    for x, width, name in [(25, 590, 'Virtual address range'), (665, 310, 'Physical allocations')]:
        parts.append(f'<rect x="{x}" y="25" width="{width}" height="365" rx="4" fill="var(--trace-fill)" stroke="var(--trace-rule)" stroke-width="2"/>')
        parts.append(svg_text(x+width/2, 60, name, 20, weight=600))
    parts.append(f'<a href="{SOURCES["reserve"][0]}" target="_blank" rel="noopener">')
    parts.append(svg_text(320, 98, 'cuMemAddressReserve: address space only', 17))
    parts.append('<rect x="45" y="125" width="550" height="70" fill="var(--trace-bg)" stroke="var(--trace-rule)" stroke-dasharray="5 4"/>')
    parts.append(svg_text(320, 167, 'unmapped VA has no physical backing', 17))
    parts.append('</a>')
    parts.append(f'<a href="{SOURCES["create"][0]}" target="_blank" rel="noopener">')
    parts.append(svg_text(820, 98, 'cuMemCreate → handles', 17))
    for i in range(4):
        x = 685+i*67
        parts.append(f'<rect x="{x}" y="125" width="57" height="70" fill="var(--trace-physical)" stroke="var(--trace-rule)"/>')
        parts.append(svg_text(x+28, 155, f'H{i}', 17))
        parts.append(svg_text(x+28, 178, '20 MiB', 12))
    parts.append('</a>')
    parts.append(f'<a href="{SOURCES["map"][0]}" target="_blank" rel="noopener">')
    parts.append(svg_text(320, 225, 'cuMemMap: VA interval → physical handle', 17))
    parts.append(svg_text(320, 247, 'cuMemSetAccess: allow device access', 17))
    for i in range(4):
        x = 45+i*89
        parts.append(f'<rect x="{x}" y="267" width="89" height="72" fill="var(--trace-physical)" stroke="var(--trace-rule)"/>')
        parts.append(svg_text(x+44, 296, f'VA → H{i}', 15))
        parts.append(svg_text(x+44, 320, '20 MiB', 13))
    parts.append('<rect x="401" y="267" width="194" height="72" fill="var(--trace-bg)" stroke="var(--trace-rule)" stroke-dasharray="5 4"/>')
    parts.append(svg_text(498, 308, 'unmapped remainder', 15))
    parts.append(svg_text(820, 285, '64 MiB tensor request', 17))
    parts.append(svg_text(820, 316, '80 MiB mapped backing', 17, weight=600))
    parts.append('</a>')
    parts.append(svg_text(500, 420, 'Illustrative PyTorch 2.8 large-pool case: four 20 MiB allocator chunks, not a GPU page-size claim.', 15))
    parts.append('</svg>')
    return ''.join(parts)


def figure(name, lang):
    captions = {
        'callback': ('Runtime / Driver API callback 在调用 CUDA API 的 CPU 线程上同步执行。实心条标明调用范围，长度不代表实测耗时。消息可点击查看接口说明。', 'Runtime and Driver API callbacks execute synchronously on the calling CPU thread. Bars show call scopes, not measured durations. Messages link to API documentation.'),
        'vmm': ('地址预留、物理分配与映射分别记账。此处 80 MiB 来自 PyTorch 大池的 20 MiB 分配粒度；图形不按地址空间大小等比例绘制。', 'Track reserved addresses, physical allocations, and mappings separately. The 80 MiB example follows PyTorch’s 20 MiB large-pool chunks; VA ranges are not drawn to scale.'),
    }
    svg = callback_diagram(lang) if name == 'callback' else vmm_diagram(lang)
    label = 'Source-linked diagram' if lang == 'en' else '图中消息与 API 可点击查看来源'
    fit = 'Fit width' if lang == 'en' else '适应宽度'
    return f'<figure class="trace-figure"><div class="trace-toolbar"><span>{label}</span><span><button type="button" data-trace-fit="fit" aria-pressed="true">{fit}</button> <button type="button" data-trace-fit="actual" aria-pressed="false">100%</button></span></div><div class="trace-viewport" tabindex="0">{svg}</div><figcaption>{captions[name][lang=="en"]}</figcaption></figure>'


SNIPPETS = {
    'setup': '''# Linux, NVIDIA GPU + compatible driver, CUDA Toolkit 12.8 development files
python3 -m venv .venv
source .venv/bin/activate
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
nvidia-smi

# Save memory_trace.cpp, build.sh, allocator_demo.py, summarize.py here.
export CUDA_ROOT=/usr/local/cuda-12.8
export TRACE_BUILD="$PWD/build"
bash build.sh''',
    'run': '''mkdir -p traces

# Each command starts a fresh process. Keep the native cache enabled.
env -u PYTORCH_NO_CUDA_MEMORY_CACHING -u PYTORCH_ALLOC_CONF \\
  PYTORCH_CUDA_ALLOC_CONF=backend:native,expandable_segments:False \\
  python allocator_demo.py --library "$TRACE_BUILD/libmemory_trace.so" \\
  --trace traces/native.csv > traces/native-states.jsonl

env -u PYTORCH_NO_CUDA_MEMORY_CACHING -u PYTORCH_ALLOC_CONF \\
  PYTORCH_CUDA_ALLOC_CONF=backend:native,expandable_segments:True \\
  python allocator_demo.py --library "$TRACE_BUILD/libmemory_trace.so" \\
  --trace traces/vmm.csv > traces/vmm-states.jsonl

python summarize.py traces/native.csv
python summarize.py traces/vmm.csv
cat traces/native-states.jsonl
cat traces/vmm-states.jsonl''',
    'decode': '''// At CUPTI_API_EXIT for cudaMalloc:
const auto* p = static_cast<const cudaMalloc_v3020_params*>(info->functionParams);
const auto result = *static_cast<const cudaError_t*>(info->functionReturnValue);
const size_t requested_bytes = p->size;
if (result == cudaSuccess) {
    void* allocated_address = *p->devPtr;
    // Copy scalar fields into the trace while the callback data is valid.
}''',
    'activity-flow': '''Register buffers: cuptiActivityRegisterCallbacks(requestBuffer, completeBuffer)
Enable records:   cuptiActivityEnable(CUPTI_ACTIVITY_KIND_RUNTIME / DRIVER / ...)
Run workload:     CUPTI fills buffers, then delivers them asynchronously
Consume buffer:   cuptiActivityGetNextRecord(...) until MAX_LIMIT_REACHED
Check losses:     cuptiActivityGetNumDroppedRecords(context, streamId, &dropped)
Finish workload:  synchronize needed CUDA work outside callbacks
Drain records:    cuptiActivityFlushAll(0); release buffers after parsing''',
}

ZH = r'''
<h1>用 CUPTI 追踪 PyTorch 显存分配</h1>
<p class="lead">PyTorch 的一次 Tensor 分配，可能复用缓存中的旧地址，也可能触发 CUDA runtime 的 cudaMalloc，或由 driver 的虚拟内存管理接口创建并映射新的物理内存。CUPTI 能记录这些 CUDA 调用的参数、返回值和发生时间，让 Tensor 生命周期、allocator 缓存与底层显存资源之间的关系可以逐项核对。本文以同一段 PyTorch 分配程序，对比普通 native allocator 与 expandable segments 两条路径，并给出可编译的追踪器和运行命令。</p>
<aside class="trace-note"><p>示例面向 Linux、CUDA Toolkit / CUPTI 12.8 与 PyTorch 2.8.0，PyTorch 源码固定到 <a href="https://github.com/pytorch/pytorch/tree/ba56102387ef21a3b04b357e5b183d48f0afefc7">ba56102387ef</a>。这里的 memory 事务指分配、释放和地址映射；kernel 内的 load/store、cache sector 与 DRAM transaction 属于另一种分析尺度。</p></aside>

<h2 id="zh-cupti">1. CUPTI 与 Nsight Systems</h2>
<h3 id="zh-role">CUDA 的观测接口</h3>
<p>CUPTI（CUDA Profiling Tools Interface）是 NVIDIA 提供的 CUDA profiling / tracing 接口。工具通过它订阅 CUDA API 调用，收集 kernel、memcpy 等活动记录，并将 CPU 提交与 GPU 执行关联起来。它随 CUDA Toolkit 提供头文件、动态库和示例，应用可以在进程内加载自己的采集器。{source:overview}</p>
<p>Nsight Systems 使用 CUPTI 收集 CUDA 相关信息，在此基础上组织时间线、统计与导出文件；它还采集 CPU 调度、OS runtime、NVTX 等其他信息。这些信息各有采集来源，不能把整个 nsys 都视为 CUPTI 的封装。直接使用 CUPTI 的价值在于定义自己的筛选范围和记录字段，例如只关心某几个显存 API 的参数。{source:nsys}</p>
<h3 id="zh-scale">显存事件的层次</h3>
<div class="trace-table"><table><thead><tr><th>观察对象</th><th>典型问题</th><th>对应入口</th></tr></thead><tbody>
<tr><td>PyTorch Tensor / allocator</td><td>哪次 Tensor 分配使用了缓存块？</td><td>Tensor 指针、memory_allocated / memory_reserved、allocator snapshot</td></tr>
<tr><td>CUDA 内存管理</td><td>何时调用 cudaMalloc、cuMemCreate、cuMemMap？参数是什么？</td><td>CUPTI Runtime / Driver API callbacks</td></tr>
<tr><td>GPU 数据搬运</td><td>一次 H2D 实际何时开始、何时结束？</td><td>MEMCPY activity；CPU API 区间不能替代 GPU 执行区间</td></tr>
<tr><td>Kernel 内存访问</td><td>Load/store 产生多少 cache / DRAM 流量？</td><td>硬件计数器与 Nsight Compute 等 profiling 工具</td></tr>
</tbody></table></div>
<p>MEMCPY activity 描述实际搬运的字节数和 GPU 起止时间；cudaMalloc callback 描述内存管理 API 的一次调用。两者可以同时出现在 CUDA 工作负载里，但记录的含义不同。{source:copy}。本项目的 <a href="gpu-memory-data-path-nsight-compute.html">GPU 访存路径与 Nsight Compute</a> 讨论 kernel 内的访存层次。</p>

<h2 id="zh-interfaces">2. Callback 与 Activity</h2>
<h3 id="zh-callback">同步 callback</h3>
<p>一个 subscriber 将回调函数注册给 CUPTI。Domain 区分 runtime、driver、resource 等事件来源，CBID 标识 domain 内的具体 API。本文只启用两个 runtime CBID 和七个 driver VMM CBID；未订阅的 API 不会出现在这份日志中。{source:callbacks}</p>
<div class="trace-table"><table><thead><tr><th>接口 / 字段</th><th>用途</th></tr></thead><tbody>
<tr><td>cuptiSubscribe</td><td>注册 callback 与用户状态，取得 subscriber handle</td></tr>
<tr><td>cuptiEnableCallback</td><td>为一个 domain + CBID 启用或禁用通知</td></tr>
<tr><td>CUPTI_API_ENTER / EXIT</td><td>在 CUDA API 执行前、返回调用者前运行 callback</td></tr>
<tr><td>functionParams</td><td>按该 CBID 对应的参数结构读取输入和输出参数</td></tr>
<tr><td>functionReturnValue</td><td>EXIT 时读取 cudaError_t 或 CUresult</td></tr>
<tr><td>correlationData / correlationId</td><td>前者保存同一次调用 ENTER / EXIT 之间的工具状态；后者关联对应 activity</td></tr>
<tr><td>cuptiUnsubscribe</td><td>停止订阅；应在回调代码所在动态库卸载前完成</td></tr>
</tbody></table></div>
<p>Runtime 和 Driver API callback 在调用线程上同步执行，日志写入会延长应用的执行路径。callback 内不应调用 CUDA runtime / driver API，也不应创建 CUDA Tensor；这可能引发递归或死锁。示例只读取参数、调用 CUPTI 时间戳接口并写入 CSV。{source:usage}</p>
{figure:callback}
<p>参数结构由 Toolkit 的 <code>generated_cuda_runtime_api_meta.h</code> 和 <code>generated_cuda_meta.h</code> 定义。<code>cudaMalloc_v3020_params</code> 中的 v3020 是该 API 参数版本标识，不要求使用 CUDA 3.2。分配地址位于输出参数 <code>*devPtr</code> 中，必须在 EXIT 且返回成功后读取；失败时仍可以记录请求大小和错误码。{source:data}</p>
{code:decode}
<p>functionParams 指向的结构只在 callback 有效期内可用。需要异步写日志时，应在回调内复制所需标量，不能把这些临时指针直接塞进后台队列。示例用 correlationData 保存 ENTER 时间戳，并在 EXIT 输出一条完整记录；start_ns / end_ns 是 host 侧 API 边界，不是 GPU 工作持续时间。</p>
<h3 id="zh-activity">异步 activity</h3>
<p>Activity API 让 CUPTI 把记录写入工具提供的 buffer，再异步交付给工具。RUNTIME / DRIVER activity 给出 API 名称对应的 CBID、时间、进程 / 线程与返回值；它们不提供 callback 那样的完整 functionParams。需要提取 VMM 的 handle、地址和映射长度时，callback 更直接。{source:api}</p>
{code:activity-flow}
<p>Buffer 解析需要处理结束状态、记录版本和丢失计数。<code>cuptiActivityFlushAll</code> 本身不隐式同步 CUDA 工作；希望得到完整 GPU 起止时间时，应用必须先完成所需同步。本文的可运行追踪器只使用 Callback API，因此不注册 activity buffer，也不需要 activity flush。{source:activity}</p>
<p><code>CUPTI_ACTIVITY_KIND_MEMORY2</code> 的 CUpti_ActivityMemory4 将分配与释放表示为独立记录，包含地址、字节数、memory kind 等信息。它适合补充内存生命周期视图；逐项重建 VMM 的 reserve、create、map、set-access 过程，仍应检查对应 Driver callback，不能用一条 MEMORY2 记录代替全部步骤。{source:memory}</p>
<p>Callback 的 correlationId 对应同一 domain 的 API activity。关联记录时需要保留进程与 domain，不能假设相邻 runtime 和 driver 记录共享同一个 ID；例如 CUpti_ActivityMemcpy6 分别提供 driver 的 correlationId 与 runtimeCorrelationId。callback、API activity 和内存 activity 也可能是同一操作的不同视角，不能重复计数。{source:data}；{source:copy}</p>

<h2 id="zh-allocator">3. PyTorch 显存路径</h2>
<h3 id="zh-native">缓存与 cudaMalloc</h3>
<p>Native caching allocator 优先从池中寻找可复用块。缓存不足时，普通路径通过 cudaMalloc 获得更大的分配，再将块交给 Tensor。Tensor 销毁后，allocator 通常保留空闲块供后续使用；只有向 CUDA 归还资源时，才会出现 cudaFree。因此一次 <code>torch.empty</code> 不必对应一次 cudaMalloc，<code>del tensor</code> 也不必对应 cudaFree。{source:native}；{source:free}</p>
<p><code>memory_allocated()</code> 统计 allocator 当前归于 Tensor 等活跃分配的大小，<code>memory_reserved()</code> 统计 allocator 管理的显存。两者都不是进程全部 CUDA 资源的总计；CUDA context、库内部或其他 allocator 的内存可能不包含在内。<code>empty_cache()</code> 释放可归还的空闲缓存，不能释放仍被活跃 Tensor 占用的内存。{source:cache}</p>
<h3 id="zh-vmm">Expandable segments 与 VMM</h3>
<p><code>backend:native,expandable_segments:True</code> 仍使用 PyTorch 的 native allocator，但改变其向 CUDA 获得内存的方式：先预留连续虚拟地址，再按需创建物理分配并映射。可扩展的是已映射的覆盖范围，缓存复用仍然存在。{source:reserve}；{source:create}</p>
<div class="trace-table"><table><thead><tr><th>Driver API</th><th>管理的资源</th><th>追踪字段</th></tr></thead><tbody>
<tr><td>cuMemAddressReserve</td><td>预留虚拟地址范围；此时不等于获得同样多的物理显存</td><td>成功后的 ptr、size</td></tr>
<tr><td>cuMemCreate</td><td>创建物理内存分配并返回 handle；尚未映射到可访问地址</td><td>成功后的 handle、size</td></tr>
<tr><td>cuMemMap</td><td>将物理分配关联到虚拟地址区间</td><td>ptr、size、handle、offset</td></tr>
<tr><td>cuMemSetAccess</td><td>设置指定设备对该范围的访问权限</td><td>ptr、size；需要分析多 GPU 权限时再扩展 desc 数组</td></tr>
<tr><td>cuMemUnmap</td><td>解除指定地址区间的映射</td><td>ptr、size</td></tr>
<tr><td>cuMemRelease</td><td>释放一个 allocation handle 引用；物理资源回收还取决于剩余引用 / 映射</td><td>handle；从对应成功 create 记录查找大小</td></tr>
<tr><td>cuMemAddressFree</td><td>归还已解除映射的虚拟地址预留</td><td>ptr、size</td></tr>
</tbody></table></div>
<p>这组 API 把地址空间、物理分配、映射和权限拆开管理。cuMemMap 后仍需设置访问权限，才可供相应设备使用。PyTorch 的释放路径先等待相关工作完成，再 unmap、release；整个 expandable segment 销毁时才 address-free。{source:vmm}；{source:map}；{source:release}；{source:destroy}</p>
{figure:vmm}
<aside class="trace-note"><p>三个容易混淆的量：cuMemAddressReserve 的 size 是虚拟地址范围；cuMemCreate 的 size 是物理分配大小；PyTorch memory_reserved 是 allocator 的显存统计，不等于预留的整个虚拟地址范围。<code>CU_MEM_ALLOCATION_TYPE_PINNED</code> 配合 DEVICE location 创建的是这里的设备物理内存，也不是 <a href="pytorch-dataloader.html#zh-device">DataLoader pin_memory</a> 使用的页锁定 CPU batch。</p></aside>
<p>本文固定版本的大池使用 20 MiB 分配块，小池使用 2 MiB。这是 allocator 的粒度，不代表 GPU 硬件页大小。一个全新的大池承接 64 MiB 请求，可能需要四个 20 MiB handle，映射总量为 80 MiB。地址预留范围则可能远大于这些实际物理分配。{source:pages}；{source:reserve}</p>

<h2 id="zh-example">4. 端到端示例</h2>
<h3 id="zh-build">环境与编译</h3>
<p>示例需要 NVIDIA GPU、兼容 CUDA 12.8 的驱动、CUDA Toolkit 12.8 开发文件，以及带 CUDA 的 PyTorch 2.8。C++ 追踪器使用普通 g++ 编译，不含 device kernel。安装了 PyTorch wheel 不等于系统已经有完整 CUDA 开发头文件；编译时的 CUPTI headers 和动态库应来自同一版本。</p>
<p>将 <a href="../assets/pytorch-internals/cupti-memory/memory_trace.cpp" download>memory_trace.cpp</a>、<a href="../assets/pytorch-internals/cupti-memory/build.sh" download>build.sh</a>、<a href="../assets/pytorch-internals/cupti-memory/allocator_demo.py" download>allocator_demo.py</a> 和 <a href="../assets/pytorch-internals/cupti-memory/summarize.py" download>summarize.py</a> 保存到同一目录。已有匹配环境时可跳过创建 venv 和安装 PyTorch：</p>
{code:setup}
<p>build.sh 默认使用 <code>$CUDA_ROOT/include</code>、<code>$CUDA_ROOT/extras/CUPTI/include</code> 和 <code>$CUDA_ROOT/extras/CUPTI/lib64</code>。发行版安装到其他位置时，可覆盖 CUDA_INCLUDE、CUPTI_INCLUDE 和 CUPTI_LIB。构建产物只链接 libcupti，使用 rpath 指向所选 CUPTI 库目录，无需为截获 cudaMalloc 另写 LD_PRELOAD wrapper。</p>
<details><summary>查看完整编译脚本</summary>{file:build.sh}</details>
<h3 id="zh-tracer">追踪器</h3>
<p>Python 用 ctypes 显式加载追踪器，在首次 CUDA 初始化前执行 trace_start，阶段切换时执行 trace_mark，结束时执行 trace_stop。CUPTI 的 domain / CBID 订阅拦截对应调用，所以即使 PyTorch 通过 driver 函数指针调用 VMM，也不依赖同名函数的 ELF 符号替换。</p>
<p>追踪器为每次完成的 API 调用记录 phase、PID / TID、domain、CBID、correlation ID、context UID、函数名、起止时间、返回值与内存字段。失败记录保留请求字节数，但不读取未定义的输出地址或 handle。cudaFree 和 cuMemRelease 本身没有 size 参数，因此其 bytes 留空。</p>
<details><summary>查看完整 C++ 追踪器</summary>{file:memory_trace.cpp}</details>
<p>这是便于阅读的同步 CSV 采集器：一个 mutex 保证每行完整，写入和 callback 都有开销。生产级工具通常在 callback 中复制标量到预分配队列，再由后台线程处理。示例的全局 phase 只适用于这段受控程序；多线程服务需要按线程或显式操作 ID 关联，不能据此把所有 CUDA 调用归因到某个 Python 算子。</p>
<h3 id="zh-workload">分配、复用与释放</h3>
<p>程序先分配 64 MiB 的 A，删除后用同样大小的 B 检查缓存复用；B 保持存活时，再分配 96 MiB 的 C，使池需要增长。最后删除 B、C 并 empty_cache。所有 Tensor 都使用 torch.empty，不填值、不做 H2D，这样观察的是 allocator 行为。每个阶段同时输出 PyTorch 内存统计与需要核对的地址。</p>
{file:allocator_demo.py}
<p>两种 allocator 配置必须在独立 Python 进程中运行，环境变量在导入 PyTorch 前生效。不要设置 PYTORCH_NO_CUDA_MEMORY_CACHING=1，否则会破坏这里要观察的缓存路径。下面显式选择 native backend，避免把 cudaMallocAsync backend 混入比较。</p>
{code:run}
<p>CSV 保存 CUDA API 事件，JSONL 保存每个阶段结束时的 PyTorch 统计。阶段标签不是 CUPTI 或 NVTX 的标准事件；它只是本例写入日志的标记，让没有 CUDA API 调用的 DROP_A、REUSE_B 等阶段也能被保留下来。</p>

<h2 id="zh-reading">5. 日志解读</h2>
<h3 id="zh-expected">两条路径的预期差异</h3>
<p>下表是根据固定版本 allocator 源码推导的预期行为，不是实机采集结果。具体调用次数取决于初始池状态、分配粒度、失败重试和平台支持；应以 CSV 中 result=0 的记录和 JSONL 统计核对。</p>
<div class="trace-table"><table><thead><tr><th>阶段</th><th>普通 native</th><th>Expandable segments</th><th>PyTorch 侧观察</th></tr></thead><tbody>
<tr><td>ALLOC_A：64 MiB</td><td>缓存不足时 cudaMalloc</td><td>Reserve VA；Create → Map → SetAccess</td><td>allocated 上升；reserved 可能超过请求大小</td></tr>
<tr><td>DROP_A</td><td>通常不调用 cudaFree</td><td>通常不调用 Unmap / Release</td><td>allocated 下降，缓存仍保留</td></tr>
<tr><td>REUSE_B：64 MiB</td><td>复用缓存时没有新 cudaMalloc</td><td>复用已有映射时没有新 Create / Map</td><td>比较 B 与 A 的地址，并查看 reserved 是否变化</td></tr>
<tr><td>GROW_C：96 MiB</td><td>缓存不足，再次 cudaMalloc</td><td>已有 VA 有空间时增加 Create / Map，不一定再次 Reserve</td><td>活跃分配达到 160 MiB；reserved 受粒度影响</td></tr>
<tr><td>DROP_ALL</td><td>回到空闲缓存</td><td>回到已映射的空闲缓存</td><td>本例活跃 Tensor 已全部删除</td></tr>
<tr><td>EMPTY_CACHE</td><td>cudaFree 可释放的缓存块</td><td>Unmap / Release；整个 segment 释放时 AddressFree</td><td>reserved 下降；不代表 CUDA context 等资源全部释放</td></tr>
</tbody></table></div>
<p>PyTorch 2.8 的 expandable 路径可能先尝试一种 handle 类型，再在不支持时回退。一个失败的 cuMemCreate 后跟着成功重试，并不表示分配了两份内存。错误码是判断资源是否建立的前提，而不是可以省略的诊断字段。{source:create}</p>
<h3 id="zh-accounting">地址、handle 与计数</h3>
<p>Native 路径可用成功 cudaMalloc 的 address → size 配对 cudaFree；VMM 路径则要分别维护 VA 范围、handle → size，以及 (VA interval, handle, offset) 映射。地址与 handle 都可能被再次使用，需要按发生顺序维护生命周期；不要把某个十六进制值当作全程唯一对象 ID。</p>
<p>例如同一份 80 MiB backing 既产生 80 MiB 的 create 记录，也产生 80 MiB 的 map 记录。二者相加得到的 160 MiB 没有“物理占用”的含义。Reserve 的巨大 size 更不能加入显存总量。通用 VMM 程序还允许多映射、共享 handle 与跨进程引用，cuMemRelease 的一次调用也不足以独立证明物理内存已回收。</p>
<p>配套汇总脚本只按 phase / domain / API 统计成功次数、失败次数及该 API 自身的 bytes 总和，刻意不输出跨 API 的“总显存”。Free / Release 缺少的 size 也不会被当作 0 字节释放。需要绘制占用曲线时，应补上生命周期配对与映射状态分析，并说明统计的是活跃 Tensor、allocator backing 还是保留的 VA。</p>
<details><summary>查看日志汇总脚本</summary>{file:summarize.py}</details>
<h3 id="zh-limits">观测范围与排查</h3>
<div class="trace-table"><table><thead><tr><th>现象</th><th>检查方向</th></tr></thead><tbody>
<tr><td>没有任何成功事件</td><td>检查 cuptiSubscribe 的错误、库版本、CUDA 可用性和启动时机。空日志不证明程序没有分配。</td></tr>
<tr><td>REUSE_B 没有 CUDA 分配调用</td><td>同时查看 data_ptr 与 reserved；缓存命中本来就可能没有底层 API。</td></tr>
<tr><td>打开 expandable_segments 后没有 VMM</td><td>确认在新进程中设置配置、使用 native backend，并检查平台不支持的 warning；不要把回退路径当成 VMM 结果。</td></tr>
<tr><td>与 nsys / torch.profiler 同用时报订阅失败</td><td>CUPTI 12.8 的 callback subscriber 限制为一个；采集器与这些 CUDA profiler 分开运行。</td></tr>
<tr><td>出现 cudaMallocAsync 或其他分配器</td><td>超出本例九个 CBID 的范围；需为实际 API 增加订阅、参数解码和相应生命周期语义。</td></tr>
<tr><td>耗时比无采集时长</td><td>同步 callback 和文件写入会扰动时序。本例用于解释调用与资源，不用于给 allocator 做性能排名。</td></tr>
</tbody></table></div>
<p>自动阶段标记不包含 Python 调用栈，CSV 不含 kernel、memcpy、隐式 driver 内部事件或其他进程的分配。本例主动取消订阅后发生的进程退出清理也不在观测范围内。若要联看完整时间线，可在另一次运行中使用 Nsight Systems；其 SQLite 表可参考本项目的 <a href="cheatsheet-cupti.html">CUPTI 表速查</a>。其中的表名属于 nsys 导出 schema，并不是本文自定义 CSV 的字段。{source:usage}</p>

<h2 id="zh-validation">6. 验证与源码</h2>
<p>本文追踪器在无 GPU 的 Linux 环境中，以 NVIDIA CUDA / CUPTI 12.8 开发文件编译并检查 host 端参数解码与日志汇总。当前环境无法执行真实 CUDA 分配；两种 allocator 的端到端命令和预期行为仍需在支持的 GPU 上验证。文中的 64 / 80 MiB 等推导不作为实测数据。</p>
<p>接口语义来自 {source:callbacks}、{source:data}、{source:activity} 和 {source:vmm}。Allocator 的关键实现为 {source:native}、{source:reserve}、{source:create}、{source:map}、{source:release}。更换 Toolkit 或 PyTorch 版本时，应核对参数结构、CBID、allocator 配置及平台能力，再复用这套采集方法。</p>
'''

EN = r'''
<h1>Tracing PyTorch memory allocation with CUPTI</h1>
<p class="lead">A PyTorch Tensor allocation may reuse a cached address, call the CUDA runtime’s cudaMalloc, or create and map physical memory through driver virtual memory management APIs. CUPTI exposes the arguments, results, and timing of these CUDA calls, connecting Tensor lifetimes to allocator caches and underlying resources. A single allocation workload compares the ordinary native allocator with expandable segments, using a compilable tracer and explicit launch commands.</p>
<aside class="trace-note"><p>The example targets Linux, CUDA Toolkit / CUPTI 12.8, and PyTorch 2.8.0, with PyTorch source pinned to <a href="https://github.com/pytorch/pytorch/tree/ba56102387ef21a3b04b357e5b183d48f0afefc7">ba56102387ef</a>. Memory operations here mean allocation, release, and address mapping. Kernel load/store instructions, cache sectors, and DRAM transactions are a different observation level.</p></aside>

<h2 id="en-cupti">1. CUPTI and Nsight Systems</h2>
<h3 id="en-role">Observing CUDA</h3>
<p>CUPTI, the CUDA Profiling Tools Interface, provides NVIDIA’s interfaces for CUDA profiling and tracing. Tools subscribe to API calls, collect kernel and memcpy activities, and correlate CPU submissions with GPU execution. The Toolkit supplies headers, libraries, and samples for building a collector loaded into the application process. {source:overview}</p>
<p>Nsight Systems uses CUPTI for CUDA information and adds timeline presentation, statistics, and export. Its CPU scheduling, OS runtime, and NVTX views involve other collection mechanisms too. A custom CUPTI tool gives control over selection and fields, such as the arguments of a small set of allocation APIs. {source:nsys}</p>
<h3 id="en-scale">Memory observation levels</h3>
<div class="trace-table"><table><thead><tr><th>Object</th><th>Question</th><th>Observation</th></tr></thead><tbody>
<tr><td>PyTorch Tensor / allocator</td><td>Did this allocation reuse a cached block?</td><td>Tensor pointers, allocated / reserved statistics, allocator snapshots</td></tr>
<tr><td>CUDA memory management</td><td>When were cudaMalloc, cuMemCreate, and cuMemMap called, with which arguments?</td><td>CUPTI Runtime / Driver API callbacks</td></tr>
<tr><td>GPU transfers</td><td>When did an H2D copy actually execute?</td><td>MEMCPY activity; CPU API intervals do not substitute for GPU intervals</td></tr>
<tr><td>Kernel memory accesses</td><td>How much cache / DRAM traffic did load/store instructions cause?</td><td>Hardware metrics and tools such as Nsight Compute</td></tr>
</tbody></table></div>
<p>A MEMCPY activity describes transfer bytes and device timestamps. A cudaMalloc callback describes a memory-management API invocation. Both may occur in a workload but carry different meanings. {source:copy}. The <a href="gpu-memory-data-path-nsight-compute.html">GPU memory-path article</a> covers memory accesses inside kernels.</p>

<h2 id="en-interfaces">2. Callback and Activity</h2>
<h3 id="en-callback">Synchronous callbacks</h3>
<p>A subscriber registers a callback with CUPTI. A domain identifies runtime, driver, resource, or another event category; a CBID identifies a particular API within that domain. This tracer enables two runtime CBIDs and seven driver VMM CBIDs. Calls outside that selection are absent from its log. {source:callbacks}</p>
<div class="trace-table"><table><thead><tr><th>Interface / field</th><th>Purpose</th></tr></thead><tbody>
<tr><td>cuptiSubscribe</td><td>Register a callback and user state; obtain a subscriber handle</td></tr>
<tr><td>cuptiEnableCallback</td><td>Enable or disable notifications for one domain + CBID</td></tr>
<tr><td>CUPTI_API_ENTER / EXIT</td><td>Run before the API executes and before it returns to its caller</td></tr>
<tr><td>functionParams</td><td>Decode inputs and outputs using the structure matching that CBID</td></tr>
<tr><td>functionReturnValue</td><td>Read cudaError_t or CUresult at EXIT</td></tr>
<tr><td>correlationData / correlationId</td><td>Per-call ENTER / EXIT tool state versus correlation to activity records</td></tr>
<tr><td>cuptiUnsubscribe</td><td>Stop notifications before unloading the library containing the callback</td></tr>
</tbody></table></div>
<p>Runtime and Driver API callbacks execute synchronously on the calling thread. Logging therefore adds work to the application’s execution path. Do not call CUDA runtime / driver APIs or create CUDA tensors inside these callbacks: recursion or deadlock may result. This example reads parameters, obtains CUPTI timestamps, and writes CSV. {source:usage}</p>
{figure:callback}
<p>The Toolkit’s generated_cuda_runtime_api_meta.h and generated_cuda_meta.h define parameter structures. The v3020 suffix in cudaMalloc_v3020_params identifies an API parameter version, not a requirement to install CUDA 3.2. The allocated address is an output, <code>*devPtr</code>, and must only be read at a successful EXIT. A failed call still has a request size and an error worth recording. {source:data}</p>
{code:decode}
<p>functionParams is valid only during the callback. An asynchronous logger must copy needed scalar values before returning, rather than retain these temporary pointers. The example stores the ENTER timestamp in correlationData and writes one record at EXIT. Its start_ns / end_ns delimit host API execution, not GPU work.</p>
<h3 id="en-activity">Asynchronous activities</h3>
<p>The Activity API fills tool-provided buffers and delivers records asynchronously. RUNTIME / DRIVER activities contain CBID, timing, process / thread IDs, and return values. They do not expose the full functionParams available to callbacks. Callbacks are the direct route to VMM handles, addresses, and mapping lengths. {source:api}</p>
{code:activity-flow}
<p>Buffer handling must account for end-of-buffer status, record versions, and dropped records. cuptiActivityFlushAll does not implicitly synchronize CUDA work; the application must complete the necessary work first when complete GPU timestamps are required. The runnable tracer below uses only callbacks, so it neither registers activity buffers nor performs an activity flush. {source:activity}</p>
<p>CUpti_ActivityMemory4, enabled with CUPTI_ACTIVITY_KIND_MEMORY2, gives separate allocation and release records with addresses, byte counts, and memory kinds. It can complement a lifetime view. Reconstructing VMM reservation, creation, mapping, and access operations still requires inspecting the corresponding driver callbacks; one MEMORY2 record is not a replacement for the entire sequence. {source:memory}</p>
<p>A callback’s correlationId matches its API activity within the corresponding domain. Preserve process and domain when joining records, and do not assume adjacent runtime and driver calls share an ID. CUpti_ActivityMemcpy6, for example, distinguishes the driver correlationId from runtimeCorrelationId. Callbacks, API activities, and memory activities can also describe the same underlying operation and must not be counted as independent allocations. {source:data}; {source:copy}</p>

<h2 id="en-allocator">3. PyTorch allocation paths</h2>
<h3 id="en-native">Caching and cudaMalloc</h3>
<p>The native caching allocator first searches for reusable blocks. When the ordinary path needs more memory, it obtains an allocation through cudaMalloc and assigns a block to the Tensor. Deleting a Tensor typically leaves an idle block in the pool; cudaFree appears when resources are returned to CUDA. Consequently, neither torch.empty nor del tensor implies a one-to-one CUDA allocation or free. {source:native}; {source:free}</p>
<p>memory_allocated() measures allocator-accounted live allocations such as Tensor storage, while memory_reserved() measures memory managed by the allocator. Neither is a complete inventory of all CUDA resources in the process: context memory, library allocations, and other allocators may be outside that accounting. empty_cache() returns eligible idle cached memory; it cannot free storage still owned by live Tensors. {source:cache}</p>
<h3 id="en-vmm">Expandable segments and VMM</h3>
<p>backend:native,expandable_segments:True retains the native allocator and changes how it obtains memory from CUDA. It reserves a contiguous virtual range, then creates physical allocations and maps them as needed. The mapped coverage can grow, while cache reuse remains part of the path. {source:reserve}; {source:create}</p>
<div class="trace-table"><table><thead><tr><th>Driver API</th><th>Resource effect</th><th>Recorded fields</th></tr></thead><tbody>
<tr><td>cuMemAddressReserve</td><td>Reserve virtual addresses, without allocating that many physical bytes</td><td>Successful output ptr; size</td></tr>
<tr><td>cuMemCreate</td><td>Create a physical allocation and return a handle, not yet an accessible mapping</td><td>Successful output handle; size</td></tr>
<tr><td>cuMemMap</td><td>Associate physical backing with a virtual interval</td><td>ptr, size, handle, offset</td></tr>
<tr><td>cuMemSetAccess</td><td>Set device access permissions</td><td>ptr, size; extend decoding to desc entries for multi-GPU permissions</td></tr>
<tr><td>cuMemUnmap</td><td>Remove a mapping</td><td>ptr, size</td></tr>
<tr><td>cuMemRelease</td><td>Release a handle reference; physical lifetime also depends on remaining references / mappings</td><td>handle; recover size from its successful creation</td></tr>
<tr><td>cuMemAddressFree</td><td>Return an unmapped virtual reservation</td><td>ptr, size</td></tr>
</tbody></table></div>
<p>These calls separate addresses, physical backing, mappings, and permissions. Mapping alone does not grant device access. PyTorch waits for relevant work before unmapping and releasing backing; destruction of the whole expandable segment releases its VA reservation. {source:vmm}; {source:map}; {source:release}; {source:destroy}</p>
{figure:vmm}
<aside class="trace-note"><p>Keep three quantities separate: cuMemAddressReserve size is virtual address space; cuMemCreate size is physical allocation; PyTorch memory_reserved is allocator memory accounting, not the entire reserved VA range. CU_MEM_ALLOCATION_TYPE_PINNED with a DEVICE location describes device physical memory here, not the page-locked CPU batches in <a href="pytorch-dataloader.html#en-device">DataLoader pin_memory</a>.</p></aside>
<p>The pinned PyTorch version uses 20 MiB chunks for its large pool and 2 MiB chunks for its small pool. These are allocator granularities, not GPU hardware page sizes. A fresh large pool serving a 64 MiB request can create four 20 MiB handles, giving 80 MiB of mapped backing. Its VA reservation can be much larger. {source:pages}; {source:reserve}</p>

<h2 id="en-example">4. End-to-end example</h2>
<h3 id="en-build">Environment and build</h3>
<p>The example requires an NVIDIA GPU, a driver compatible with CUDA 12.8, CUDA Toolkit 12.8 development files, and CUDA-enabled PyTorch 2.8. The tracer is ordinary C++ compiled with g++; it contains no device kernel. A PyTorch wheel does not by itself supply a complete system Toolkit installation. Match CUPTI headers to the library used at build and runtime.</p>
<p>Save <a href="../assets/pytorch-internals/cupti-memory/memory_trace.cpp" download>memory_trace.cpp</a>, <a href="../assets/pytorch-internals/cupti-memory/build.sh" download>build.sh</a>, <a href="../assets/pytorch-internals/cupti-memory/allocator_demo.py" download>allocator_demo.py</a>, and <a href="../assets/pytorch-internals/cupti-memory/summarize.py" download>summarize.py</a> in one directory. Skip environment creation and installation if a matching environment already exists:</p>
{code:setup}
<p>build.sh defaults to $CUDA_ROOT/include, $CUDA_ROOT/extras/CUPTI/include, and $CUDA_ROOT/extras/CUPTI/lib64. Override CUDA_INCLUDE, CUPTI_INCLUDE, and CUPTI_LIB for other layouts. The shared library links only libcupti and records its directory in rpath. Capturing cudaMalloc does not require a separate LD_PRELOAD symbol wrapper.</p>
<details><summary>Complete build script</summary>{file:build.sh}</details>
<h3 id="en-tracer">The tracer</h3>
<p>Python explicitly loads the library through ctypes, starts tracing before its first CUDA initialization, marks each phase, and stops tracing at the end. CUPTI subscribes to domains and CBIDs, so PyTorch’s calls through driver function pointers do not depend on ELF symbol interposition.</p>
<p>Each completed API record contains a phase, PID / TID, domain, CBID, correlation ID, context UID, name, timestamps, result, and memory fields. Failed calls retain request bytes but never dereference undefined output addresses or handles. cudaFree and cuMemRelease have no size argument, so their bytes field is empty.</p>
<details><summary>Complete C++ tracer</summary>{file:memory_trace.cpp}</details>
<p>This is a synchronous teaching logger. A mutex keeps CSV rows intact; both callbacks and writes add overhead. A production collector would typically copy scalar fields into preallocated queues for a background writer. The global phase is appropriate only for this controlled program. Multithreaded services need per-thread or explicit operation IDs, rather than treating the phase as attribution to a Python operator.</p>
<h3 id="en-workload">Allocation, reuse, and release</h3>
<p>The workload allocates a 64 MiB A, deletes it, then requests an equally sized B to inspect reuse. While B remains live, it allocates a 96 MiB C to grow the pool. It deletes B and C before empty_cache. All tensors use torch.empty, with no initialization or H2D, isolating allocator behavior. Each phase reports PyTorch memory statistics and the relevant addresses.</p>
{file:allocator_demo.py}
<p>Run the two configurations in separate Python processes, with allocator settings in place before importing torch. PYTORCH_NO_CUDA_MEMORY_CACHING=1 would disable the cache behavior being studied. The commands explicitly select the native backend to keep cudaMallocAsync outside this comparison.</p>
{code:run}
<p>CSV holds CUDA API events; JSONL holds PyTorch statistics after each phase. Phase markers are local log records, not standard CUPTI or NVTX events. They preserve phases such as DROP_A and REUSE_B even when those phases produce no selected CUDA calls.</p>

<h2 id="en-reading">5. Reading the trace</h2>
<h3 id="en-expected">Expected path differences</h3>
<p>The table is a source-derived expectation, not a measured GPU trace. Call counts depend on initial pool state, allocation granularity, retries, and platform support. Check successful CSV records, result=0, alongside JSONL statistics.</p>
<div class="trace-table"><table><thead><tr><th>Phase</th><th>Ordinary native</th><th>Expandable segments</th><th>PyTorch observation</th></tr></thead><tbody>
<tr><td>ALLOC_A: 64 MiB</td><td>cudaMalloc on a cache miss</td><td>Reserve VA; Create → Map → SetAccess</td><td>allocated rises; reserved can exceed request size</td></tr>
<tr><td>DROP_A</td><td>Typically no cudaFree</td><td>Typically no Unmap / Release</td><td>allocated falls while cache remains</td></tr>
<tr><td>REUSE_B: 64 MiB</td><td>No new cudaMalloc on a cache hit</td><td>No new Create / Map when reusing mapped backing</td><td>Compare B / A pointers and changes to reserved</td></tr>
<tr><td>GROW_C: 96 MiB</td><td>Another cudaMalloc if the cache is insufficient</td><td>More Create / Map; no new Reserve needed when the existing range has room</td><td>160 MiB of live Tensor storage; reserved follows granularity</td></tr>
<tr><td>DROP_ALL</td><td>Return blocks to idle cache</td><td>Return blocks to mapped idle cache</td><td>All workload Tensors have been deleted</td></tr>
<tr><td>EMPTY_CACHE</td><td>cudaFree eligible cached blocks</td><td>Unmap / Release; AddressFree on whole-segment destruction</td><td>reserved falls; context resources can remain</td></tr>
</tbody></table></div>
<p>The PyTorch 2.8 expandable path may try one handle type, then fall back if unsupported. A failed cuMemCreate followed by a successful retry is not two allocations. Return status determines whether a resource was established. {source:create}</p>
<h3 id="en-accounting">Addresses, handles, and counts</h3>
<p>For the ordinary path, match successful cudaMalloc address → size records to cudaFree. For VMM, separately track VA ranges, handle → size, and (VA interval, handle, offset) mappings. Both addresses and handles can be reused, so maintain lifetimes in event order rather than treating a hexadecimal value as a permanent object ID.</p>
<p>The same 80 MiB backing can generate 80 MiB of create records and 80 MiB of map records. Adding them into a 160 MiB physical total is incorrect. Large reservation sizes must also stay out of physical accounting. General VMM applications may share handles, create multiple mappings, or retain cross-process references; one cuMemRelease does not independently prove physical reclamation.</p>
<p>The summarizer groups by phase / domain / API, reporting successful calls, failures, and that API’s own byte sum. It does not output a cross-API memory total or treat the missing Free / Release size as zero-byte release. A memory-usage curve needs additional lifetime matching and mapping state, plus a definition of whether it measures live Tensors, allocator backing, or VA reservations.</p>
<details><summary>Complete summarizer</summary>{file:summarize.py}</details>
<h3 id="en-limits">Coverage and troubleshooting</h3>
<div class="trace-table"><table><thead><tr><th>Observation</th><th>What to check</th></tr></thead><tbody>
<tr><td>No successful events</td><td>Inspect subscription errors, library versions, CUDA availability, and start timing. An empty trace is not evidence of zero allocation.</td></tr>
<tr><td>No allocation calls in REUSE_B</td><td>Check data_ptr and reserved; a cache hit can legitimately produce no lower-level allocation API.</td></tr>
<tr><td>No VMM after enabling expandable segments</td><td>Use a fresh process and native backend; inspect unsupported-platform warnings. Do not label a fallback as VMM execution.</td></tr>
<tr><td>Subscription fails alongside nsys / torch.profiler</td><td>CUPTI 12.8 allows one callback subscriber; run the collector separately from those CUDA profilers.</td></tr>
<tr><td>cudaMallocAsync or another allocator is active</td><td>Outside these nine CBIDs; add the actual APIs, parameter structures, and lifetime semantics.</td></tr>
<tr><td>Execution is slower with tracing</td><td>Synchronous callbacks and file writes perturb timing. Use this collector to understand calls and resources, not rank allocator performance.</td></tr>
</tbody></table></div>
<p>Phase labels contain no Python stack. The CSV omits kernels, copies, implicit driver internals, other processes, and process-exit cleanup after unsubscription. Collect a separate Nsight Systems run for a full timeline. The project’s <a href="cheatsheet-cupti.html">CUPTI table cheatsheet</a> describes nsys SQLite export tables, not this custom CSV format. {source:usage}</p>

<h2 id="en-validation">6. Validation and source</h2>
<p>The tracer was compiled on Linux without a GPU using NVIDIA CUDA / CUPTI 12.8 development files, with host-side parameter decoding and log summarization checks. This environment cannot perform real CUDA allocations. The two end-to-end allocator runs remain to be verified on a supported GPU. Figures such as 64 / 80 MiB are derived examples, not measured results.</p>
<p>Interface references: {source:callbacks}, {source:data}, {source:activity}, and {source:vmm}. Allocator implementation: {source:native}, {source:reserve}, {source:create}, {source:map}, and {source:release}. When changing Toolkit or PyTorch versions, recheck structures, CBIDs, allocator configuration, and platform capabilities before reusing the collector.</p>
'''


def expand(body, lang):
    body = re.sub(r'\{source:(\w+)\}', lambda m: source(m[1]), body)
    body = re.sub(r'\{figure:(\w+)\}', lambda m: figure(m[1], lang), body)
    body = re.sub(r'\{code:([\w-]+)\}', lambda m: code(SNIPPETS[m[1]], 'cpp' if m[1]=='decode' else 'bash' if m[1] in ('setup','run') else 'text'), body)
    body = re.sub(r'\{file:([\w.-]+)\}', lambda m: code((ASSETS/m[1]).read_text(), 'python' if m[1].endswith('.py') else 'bash' if m[1].endswith('.sh') else 'cpp'), body)
    return body


def main():
    metadata = {
        'title': '用 CUPTI 追踪 PyTorch 显存分配',
        'title_en': 'Tracing PyTorch memory allocation with CUPTI',
        'slug': 'cupti-pytorch-memory-tracing', 'date': '2026-10-29',
        'tags': 'PyTorch, CUDA, CUPTI, 显存, VMM',
        'tags_en': 'PyTorch, CUDA, CUPTI, Memory, VMM',
        'reading': '25 分钟', 'reading_en': '25 min',
        'summary': 'PyTorch 的 native caching allocator 优先复用缓存块，缓存不足时向 CUDA 申请资源。CUPTI 回调记录 API 参数和结果，可据此区分缓存复用、cudaMalloc 分配与 VMM 映射。',
        'summary_en': 'The native PyTorch caching allocator reuses cached blocks before requesting more CUDA resources. CUPTI callbacks record API arguments and results, allowing allocation traces to distinguish cache reuse, cudaMalloc allocations, and driver VMM mappings.',
        'series': 'pytorch-internals', 'series_title': 'PyTorch 内部机制',
        'series_title_en': 'PyTorch Internals', 'series_order': '11',
    }
    meta = '\n'.join(f'<meta name="post:{k}" content="{escape(v, quote=True)}">' for k,v in metadata.items())
    page = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{metadata['title']}</title>
{meta}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/pytorch-internals/cupti-memory/trace.css">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="../assets/pytorch-internals/cupti-memory/figures.js" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div></aside><main class="content">
<div class="lang-zh">{expand(ZH,'zh')}</div><div class="lang-en">{expand(EN,'en')}</div>
</main></div></body></html>\n'''
    path = ROOT/'posts/cupti-pytorch-memory-tracing.html'
    path.write_text(page)
    print('Wrote', path)


if __name__ == '__main__':
    main()
