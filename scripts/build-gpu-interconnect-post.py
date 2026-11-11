#!/usr/bin/env python3
"""Inside CUDA #2. Pinned source references; diagrams are source schematics.

Design: compact editorial diagrams, variance 3 / motion 1 / density 7.
Reuse the series' accessible popovers and proportional window-fit controls.
"""
from html import escape
from pathlib import Path
from post_series import render_series_nav
import json
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/inside-cuda/gpu-interconnect'
BASE = '../assets/inside-cuda/gpu-interconnect/'
SHARED = '../assets/inside-cuda/linux-stack/'
SOURCES = json.loads((ASSETS / 'sources.json').read_text())
REFS = SOURCES['refs']


def link(key, label=None):
    ref = REFS[key]
    attrs = ' target="_blank" rel="noopener"' if ref['url'].startswith('https:') else ''
    return f'<a href="{escape(ref["url"], quote=True)}"{attrs}>{label or escape(ref["label"])}</a>'


def code(value):
    return '<pre><code>' + escape(textwrap.dedent(value).strip()) + '</code></pre>'


# rdma-core 61.0 providers/mlx5/qp.c lines 754-802, verbatim; tabs shown as four spaces.
MLX5_DB_LISTING = '''\
754  static inline void post_send_db(struct mlx5_qp *qp, struct mlx5_bf *bf,
755                  int nreq, int inl, int size, void *ctrl)
756  {
757      struct mlx5_context *ctx;
758
759      if (unlikely(!nreq))
760          return;
761
762      qp->sq.head += nreq;
763
764      /*
765       * Make sure that descriptors are written before
766       * updating doorbell record and ringing the doorbell
767       */
768      udma_to_device_barrier();
769      qp->db[MLX5_SND_DBR] = htobe32(qp->sq.cur_post & 0xffff);
770
771      /* Make sure that the doorbell write happens before the memcpy
772       * to WC memory below
773       */
774      ctx = to_mctx(qp->ibv_qp->context);
775      if (bf->need_lock)
776          mmio_wc_spinlock(&bf->lock.lock);
777      else
778          mmio_wc_start();
779
780      if (!ctx->shut_up_bf && nreq == 1 && bf->uuarn &&
781          (inl || ctx->prefer_bf) && size > 1 &&
782          size <= bf->buf_size / 16)
783          mlx5_bf_copy(bf->reg + bf->offset, ctrl,
784                   align(size * 16, 64), qp);
785      else
786          mmio_write64_be(bf->reg + bf->offset, *(__be64 *)ctrl);
787
788      /*
789       * use mmio_flush_writes() to ensure write combining buffers are
790       * flushed out of the running CPU. This must be carried inside
791       * the spinlock. Otherwise, there is a potential race. In the
792       * race, CPU A writes doorbell 1, which is waiting in the WC
793       * buffer. CPU B writes doorbell 2, and it's write is flushed
794       * earlier. Since the mmio_flush_writes is CPU local, this will
795       * result in the HCA seeing doorbell 2, followed by doorbell 1.
796       * Flush before toggling bf_offset to be latency oriented.
797       */
798      mmio_flush_writes();
799      bf->offset ^= bf->buf_size;
800      if (bf->need_lock)
801          mlx5_spin_unlock(&bf->lock);
802  }'''

CODE = {
    'verbs-write': '''
        // Level 2: the same 4 KiB as an RC RDMA Write. PD, MR, CQ and an RTS QP
        // exist; remote_addr and rkey arrived from B out of band.
        struct ibv_sge sge = {
            .addr = (uintptr_t)buf, .length = 4096, .lkey = mr->lkey,
        };
        struct ibv_send_wr wr = {
            .sg_list = &sge, .num_sge = 1,
            .opcode = IBV_WR_RDMA_WRITE,
            .send_flags = IBV_SEND_SIGNALED,            // request a CQE
            .wr.rdma = { .remote_addr = remote_addr, .rkey = rkey },
        };
        struct ibv_send_wr *bad_wr;
        if (ibv_post_send(qp, &wr, &bad_wr))            // libmlx5: WQE ①, doorbell ②
            abort();

        struct ibv_wc wc;
        int n;
        while ((n = ibv_poll_cq(cq, 1, &wc)) == 0)      // read the CQ ring; no syscall
            ;
        if (n < 0 || wc.status != IBV_WC_SUCCESS)
            abort();
    ''',
    'mlx5-db': MLX5_DB_LISTING,
    'uar-map': '''
        #include <cuda_runtime.h>
        #include <cstdint>

        // cpu_reg = uar->reg_addr; bytes = this UAR's register span.
        cudaError_t map_uar_to_gpu(void* cpu_reg, size_t bytes,
                                  uint64_t** gpu_doorbell_ptr) {
            *gpu_doorbell_ptr = nullptr;
            unsigned flags = cudaHostRegisterPortable
                           | cudaHostRegisterMapped
                           | cudaHostRegisterIoMemory;
            cudaError_t rc = cudaHostRegister(cpu_reg, bytes, flags);
            if (rc != cudaSuccess) return rc;

            void* device_alias = nullptr;
            rc = cudaHostGetDevicePointer(&device_alias, cpu_reg, 0);
            if (rc != cudaSuccess) {
                cudaHostUnregister(cpu_reg);
                return rc;
            }
            *gpu_doorbell_ptr = static_cast<uint64_t*>(device_alias);
            return cudaSuccess;
        }
    ''',
    'uar-pte': '''
        // VER3 encoding example, following Hopper's UVM PTE builder.
        // Input: GPU-visible NIC page address, 4 KiB aligned, below 2^52.
        uint64_t encode_uar_pte(uint64_t nic_page_addr) {
            constexpr uint64_t address_mask = ((1ULL << 52) - 1) & ~0xfffULL;
            constexpr uint64_t pcf = 0x19;  // REGULAR_RW_NO_ATOMIC_UNCACHED_ACD
            constexpr uint64_t kind = 0x6;  // GENERIC_MEMORY
            return (nic_page_addr & address_mask)  // ADDRESS [51:12]
                 | (kind << 8)                   // KIND [11:8]
                 | (pcf << 3)                    // PCF [7:3]
                 | (3ULL << 1)                   // SYSTEM_NON_COHERENT [2:1]
                 | 1ULL;                         // VALID [0]
        }
    ''',
    'uar-store': '''
        // Called by the submitting thread after preparing WQEs and the DBR.
        // mlx5_db_be: the correctly encoded 64-bit mlx5 doorbell value.
        __device__ __forceinline__
        void ring_uar(uint64_t* gpu_doorbell_ptr, uint64_t mlx5_db_be) {
            asm volatile("fence.acq_rel.sys;" ::: "memory");
            asm volatile("st.mmio.relaxed.sys.global.b64 [%0], %1;"
                         : : "l"(gpu_doorbell_ptr), "l"(mlx5_db_be)
                         : "memory");
        }
    ''',
    'nv-kernel': '''
        #include <nvshmem.h>
        #include <nvshmemx.h>

        // Two PEs, one thread per PE, one transfer, signal initially zero.
        __global__ void send_once(void* dst, const void* src,
                                  size_t bytes, uint64_t* signal) {
            if (nvshmem_my_pe() == 0) {
                nvshmem_putmem_signal_nbi(dst, src, bytes, signal,
                                         1, NVSHMEM_SIGNAL_SET, 1);
                nvshmem_quiet();
            } else {
                nvshmem_signal_wait_until(signal, NVSHMEM_CMP_GE, 1);
                // This PE can now consume its local dst.
            }
        }
    ''',
    'gin-setup': '''
        // NCCL 2.32.3. Run on both ranks after communicator initialization.
        void *src, *dst;
        ncclWindow_t srcWin, dstWin;
        ncclMemAlloc(&src, bytes);
        ncclMemAlloc(&dst, bytes);
        ncclCommWindowRegister(comm, src, bytes, &srcWin, NCCL_WIN_COLL_SYMMETRIC);
        ncclCommWindowRegister(comm, dst, bytes, &dstWin, NCCL_WIN_COLL_SYMMETRIC);

        ncclDevCommRequirements reqs = NCCL_DEV_COMM_REQUIREMENTS_INITIALIZER;
        reqs.ginType = NCCL_GIN_TYPE_PROXY;  // level 3; NCCL_GIN_TYPE_GDAKI for levels 4-5
        reqs.ginConnectionType = NCCL_GIN_CONNECTION_FULL;
        reqs.ginContextCount = 1;
        reqs.ginSignalCount = 1;
        ncclDevComm devComm;
        ncclDevCommCreate(comm, &reqs, &devComm);
    ''',
    'gin-kernel': '''
        #include <nccl_device.h>

        // Exactly two ranks; launch <<<1, 1>>> once per rank.
        __global__ void exchange_once(ncclDevComm comm, ncclWindow_t srcWin,
                                     ncclWindow_t dstWin, size_t bytes) {
            ncclGin gin{comm, 0};
            int peer = 1 - comm.rank;
            gin.put(ncclTeamWorld(comm), peer,
                    dstWin, 0, srcWin, 0, bytes,
                    ncclGin_SignalInc{0});
            gin.waitSignal(ncclCoopThread{}, 0, 1); // incoming data is ready
            gin.flush(ncclCoopThread{});          // local src can be reused
        }
    ''',
}


def txt(x, y, words, size=15, anchor='middle', cls='', weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" class="{cls}" font-weight="{weight}">{escape(words)}</text>'


def svg_start(name, height, title, interactive=False):
    out = f'<svg class="cuda-diagram interconnect-diagram" viewBox="0 0 1160 {height}" xmlns="http://www.w3.org/2000/svg" role="{"group" if interactive else "img"}" aria-labelledby="{name}-title"><title id="{name}-title">{escape(title)}</title><defs>'
    for kind in ['control', 'setup', 'gpu', 'payload']:
        out += f'<marker id="{name}-{kind}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="head-{kind}" d="M0 0L10 5L0 10Z"/></marker>'
    return out + '</defs>'


# Descriptions are taken from the visible language's component table.
NETWORK_PATHS = 'cpu proxy ibgda nvgda gdaki ginproxy'
ALL_PATHS = NETWORK_PATHS + ' peer'
COMPONENTS = {
    'nccl': ('gpu-apis', 'nccl-api', 'cpu gdaki ginproxy'),
    'nvhost': ('gpu-apis', 'nv-select', 'proxy ibgda nvgda'),
    'cuda': ('nvidia-modules', 'vmm-doc', ALL_PATHS),
    'verbs': ('nic-driver', 'user-verbs', NETWORK_PATHS),
    'mlx5': ('nic-driver', 'mlx5-send', NETWORK_PATHS),
    'gpunetio': ('gpu-doorbell-impls', 'gpureadme', 'nvgda gdaki'),
    'nvdevice': ('gpu-apis', 'nv-dispatch', 'proxy ibgda nvgda'),
    'ibgda': ('gpu-doorbell-impls', 'ibgda-db', 'ibgda'),
    'gin': ('gpu-apis', 'gin-api', 'gdaki ginproxy'),
    'nvidia': ('nvidia-modules', 'gpu-core', ALL_PATHS),
    'uvm': ('nvidia-modules', 'uvm', ALL_PATHS),
    'peermem': ('gpu-registration', 'gdaki-reg', NETWORK_PATHS),
    'rdma': ('nic-driver', 'user-verbs', NETWORK_PATHS),
    'mlx5kernel': ('nic-driver', 'user-verbs', NETWORK_PATHS),
    'gpu': ('nvidia-modules', 'peer-post', ALL_PATHS),
    'nic': ('nic-driver', 'gpureadme', NETWORK_PATHS),
    'dev-uverbs': ('nic-driver', 'uverbs-fops', NETWORK_PATHS),
    'dev-core': ('nvidia-modules', 'gpu-fops', ALL_PATHS),
    'dev-uvm': ('nvidia-modules', 'uvm-fops', ALL_PATHS),
}


def box(x, y, w, title, subtitle, component, lang, h=54, paths=None, node_id=None):
    paths = COMPONENTS[component][2] if paths is None else paths
    compact = h <= 44
    size = 13 if compact or w < 200 else 14 if len(title) > 22 else 15
    css = 'node device-node' if component.startswith('dev-') else 'node'
    return f'<g class="{css}" data-node-id="{node_id or component}" data-paths="{paths}" data-component="{component}" data-component-title="{escape(title, quote=True)}" tabindex="0" role="button" aria-label="{escape(title, quote=True)}" aria-haspopup="dialog" aria-expanded="false" aria-controls="interconnect-info-{lang}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4"/>' + txt(x+w/2,y+(17 if compact else 23),title,size,weight=650) + txt(x+w/2,y+(34 if compact else 43),subtitle,11 if compact or w < 200 else 12,cls='muted') + '</g>'


def relationship(name, source, target, points, kind, paths, ref, description, label=None, both=False):
    """Source-linked edges also participate in the shared path-focus control."""
    d = 'M' + 'L'.join(f'{x} {y}' for x, y in points)
    start = f' marker-start="url(#{name}-{kind})"' if both else ''
    out = f'<a class="architecture-edge" data-from="{source}" data-to="{target}" data-paths="{paths}" data-points="{escape(json.dumps(points), quote=True)}" href="{escape(REFS[ref]["url"], quote=True)}" target="_blank" rel="noopener" aria-label="{escape(description, quote=True)}"><title>{escape(description)}</title>'
    out += f'<path class="edge-hit" d="{d}"/><path class="seq-edge {kind}" d="{d}" marker-end="url(#{name}-{kind})"{start}/>'
    if label:
        x,y,words = label
        width = len(words)*6.1+12
        out += f'<g class="relationship-label"><rect class="message-paper" x="{x-width/2}" y="{y-12}" width="{width}" height="17" rx="2"/>'
        out += txt(x,y,words,11,'middle',f'msg-{kind}')+'</g>'
    return out+'</a>'


def architecture(lang):
    zh = lang == 'zh'
    name = 'interconnect-stack-'+lang
    out = svg_start(name, 856, 'GPU interconnect: libraries, device files, drivers and payload', True)
    legend = [('control','CPU 调用 / 提交' if zh else 'CPU call / submission'),
              ('setup','初始化 / 注册 / 映射' if zh else 'Setup / registration / mapping'),
              ('gpu','GPU 调用 / 请求' if zh else 'GPU call / request'),
              ('payload','Payload 数据路径' if zh else 'Payload data path')]
    for i,(kind,title) in enumerate(legend):
        x=30+i*290
        out += f'<path class="seq-edge {kind}" d="M{x} 24h34" marker-end="url(#{name}-{kind})"/>'
        out += txt(x+44,28,title,12,'start')
    for x,y,w,h,title in [(16,48,710,294,'CPU 用户态 · host libraries / proxy' if zh else 'CPU USER SPACE · host libraries / proxy'),
                          (746,48,398,294,'GPU kernel · device API' if zh else 'GPU KERNEL · device API'),
                          (16,458,1128,210,'Linux 内核 · 资源与权限' if zh else 'LINUX · resources / access'),
                          (16,706,1128,134,'硬件 · 直接数据通路' if zh else 'HARDWARE · direct payload paths')]:
        heading_x = 276 if y == 458 else x+16
        out += f'<rect class="band" x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/>' + txt(heading_x,y+23,title,14,'start',weight=600)
    out += '<rect class="device-band" x="16" y="350" width="1128" height="96" rx="5"/>'
    out += txt(32,372,'设备文件' if zh else 'Device files',13,'start',weight=600)
    # Routed in the gaps between nodes; edges are painted before the cards.
    edges = [
        ('nccl','verbs',[(100,154),(100,280)],'control','cpu','nccl-proxy','NCCL NET/IB CPU proxy calls the verbs network backend',(76,253,'NET/IB')),
        ('nccl','verbs',[(134,154),(134,280)],'control','ginproxy','gin-verbs','GIN CPU proxy backend submits verbs work',(148,240,'GIN proxy')),
        ('nvhost','verbs',[(310,154),(310,214),(194,214),(194,280)],'control','proxy ibgda','nv-select','NVSHMEM proxy / IBGDA host setup uses verbs',(245,207,'verbs')),
        ('nvhost','gpuhost',[(506,127),(536,127)],'setup','nvgda','nv-gpunetio','NVSHMEM GPUNetIO transport creates its host resources',None),
        ('nccl','gpuhost',[(246,118),(260,118),(260,194),(588,194),(588,154)],'setup','gdaki','gdaki-host','NCCL GDAKI host setup calls GPUNetIO',(422,187,'GDAKI setup')),
        ('gpuhost','verbs',[(568,154),(568,230),(170,230),(170,280)],'setup','gdaki nvgda','gpureadme','GPUNetIO setup uses verbs resources',None),
        ('gpuhost','mlx5',[(621,154),(621,214),(450,214),(450,280)],'setup','gdaki nvgda','gpureadme','GPUNetIO setup uses mlx5 direct verbs / DevX',(488,253,'mlx5dv / DevX')),
        ('nccl','cuda',[(220,154),(220,260),(650,260),(650,280)],'setup','cpu gdaki ginproxy','device-doc','NCCL uses CUDA allocation, mapping and export',(358,253,'CUDA resources')),
        ('nvhost','cuda',[(480,154),(480,246),(680,246),(680,280)],'setup','proxy ibgda nvgda','nv-doc','NVSHMEM host setup uses CUDA resources',None),
        ('gpuhost','cuda',[(706,127),(716,127),(716,267),(695,267),(695,280)],'setup','gdaki nvgda','gpu-export','GPUNetIO uses CUDA to prepare GPU-accessible resources',None),
        ('verbs','mlx5',[(246,307),(276,307)],'control',NETWORK_PATHS,'mlx5-send','libibverbs dispatches to the mlx5 userspace provider',None),
        ('gin','gpudevice',[(850,154),(850,280)],'gpu','gdaki','gdaki-put','NCCL GIN GDAKI backend calls GPUNetIO device verbs',(817,188,'GDAKI')),
        ('nvdevice','ibgda',[(1043,154),(1043,280)],'gpu','ibgda','nv-dispatch','NVSHMEM selects its IBGDA device transport',(1085,213,'IBGDA')),
        ('nvdevice','gpudevice',[(990,154),(990,244),(900,244),(900,280)],'gpu','nvgda','nv-dispatch','NVSHMEM GPUNetIO device transport uses GPUNetIO device verbs',(956,237,'GPUNetIO')),
        ('nvdevice','nvhost',[(958,117),(946,117),(946,82),(391,82),(391,100)],'gpu','proxy','nv-dispatch','NVSHMEM device proxy publishes requests consumed by its host proxy',(627,95,'NVSHMEM proxy request')),
        ('gin','nccl',[(768,132),(738,132),(738,170),(141,170),(141,154)],'gpu','ginproxy','gin-proxy','GIN CPU proxy backend publishes requests for the NCCL host proxy',(395,163,'GIN proxy request')),
        ('gpuhost','gpudevice',[(706,144),(728,144),(728,218),(884,218),(884,280)],'setup','gdaki nvgda','gpu-export','GPUNetIO host setup exports QP / CQ descriptors for device code',(782,211,'export QP / CQ')),
        ('verbs','dev-uverbs',[(100,334),(100,350),(150,350),(150,388)],'setup',NETWORK_PATHS,'verbs-open','libibverbs opens the uverbs character device to obtain its command fd',None),
        ('mlx5','dev-uverbs',[(350,334),(350,388)],'setup',NETWORK_PATHS,'uverbs-fops','The mlx5 provider uses the uverbs fd for ioctl / write / mmap',None),
        ('dev-uverbs','rdma',[(150,430),(150,499)],'setup',NETWORK_PATHS,'uverbs-fops','The uverbs character device dispatches file operations to ib_uverbs',None),
        ('cuda','dev-core',[(621,334),(621,388)],'setup',ALL_PATHS,'gpu-fops','libcuda opens /dev/nvidiactl and per-GPU /dev/nvidiaN nodes',None),
        ('cuda','dev-uvm',[(684,334),(684,360),(977,360),(977,388)],'setup',ALL_PATHS,'uvm-fops','libcuda opens /dev/nvidia-uvm for UVM requests and mappings',None),
        ('dev-core','nvidia',[(650,430),(650,466),(957,466),(957,499)],'setup',ALL_PATHS,'gpu-fops','nvidia_fops dispatches core device requests to nvidia.ko',None),
        ('dev-uvm','uvm',[(977,430),(977,478),(1126,478),(1126,621),(1112,621)],'setup',ALL_PATHS,'uvm-fops','uvm_fops dispatches UVM device requests to nvidia-uvm.ko',None),
        ('rdma','mlx5kernel',[(246,526),(276,526)],'setup',NETWORK_PATHS,'user-verbs','RDMA core dispatches device resource operations to mlx5 drivers',None),
        ('mlx5kernel','peermem',[(506,526),(536,526)],'setup',NETWORK_PATHS,'gdr-doc','RDMA driver obtains GPU memory mappings via peer memory or DMA-BUF',None),
        ('peermem','nvidia',[(756,526),(802,526)],'setup',NETWORK_PATHS,'peermem','GPU memory registration cooperates with the NVIDIA GPU driver',None),
        ('uvm','nvidia',[(957,594),(957,553)],'setup',ALL_PATHS,'uvm','UVM cooperates with Kernel RM',(1024,579,'RM services'),True),
        ('mlx5kernel','nic',[(391,553),(391,662),(1075,662),(1075,754)],'setup',NETWORK_PATHS,'user-verbs','mlx5 drivers configure NIC hardware resources',(432,653,'NIC setup')),
        ('nvidia','gpu',[(957,553),(957,576),(646,576),(646,754)],'setup',ALL_PATHS,'gpu-core','GPU driver establishes GPU resources and mappings',(598,612,'GPU setup')),
        ('uvm','gpu',[(802,621),(710,621),(710,754)],'setup',ALL_PATHS,'uvm','UVM manages GPU virtual address mappings',None),
        ('mlx5','nic',[(506,307),(520,307),(520,689),(990,689),(990,754)],'control','cpu proxy ginproxy','mlx5-send','CPU fast path writes WQEs / rings doorbells after resource setup',(812,683,'CPU WQE / doorbell')),
        ('gpudevice','nic',[(850,334),(850,346),(1140,346),(1140,781),(1112,781)],'gpu','gdaki nvgda','gpu-submit','GPUNetIO device verbs submit WQEs and ring a direct GPU doorbell',(1050,451,'GPU WQE / doorbell')),
        ('ibgda','nic',[(1128,307),(1140,307),(1140,781),(1112,781)],'gpu','ibgda','ibgda-db','IBGDA device code submits WQEs and rings a direct GPU doorbell',None),
        ('gpu','nic',[(756,781),(866,781)],'payload',NETWORK_PATHS,'gdr-doc','GPUDirect RDMA payload moves directly between GPU memory and NIC',(811,769,'GDR / DMA'),True),
        ('gpu','peer',[(536,781),(276,781)],'payload','peer','peer-post','GPU peer memory traffic uses NVLink / PCIe, directly or through NVSwitch',(406,769,'NVLink / PCIe'),True),
    ]
    for edge in edges: out += relationship(name,*edge)
    nodes = [
        ('nccl',36,100,210,'libnccl.so','host control · CPU proxy','nccl'),
        ('nvhost',276,100,230,'libnvshmem_host.so','heap · transports · CPU proxy','nvhost'),
        ('gpuhost',536,100,170,'GPUNetIO host','QP / CQ setup · export','gpunetio'),
        ('verbs',36,280,210,'libibverbs.so','PD · MR · QP · CQ','verbs'),
        ('mlx5',276,280,230,'libmlx5','provider · mlx5dv / DevX','mlx5'),
        ('cuda',536,280,170,'libcuda.so.1','GPU allocation / mapping','cuda'),
        ('gin',768,100,170,'NCCL GIN','rank · window · signal','gin'),
        ('nvdevice',958,100,170,'libnvshmem_device.a','put / get / signal','nvdevice'),
        ('gpudevice',768,280,170,'GPUNetIO device','WQE · doorbell · CQE','gpunetio'),
        ('ibgda',958,280,170,'IBGDA device','mlx5 queue operations','ibgda'),
        ('rdma',36,499,210,'ib_uverbs · ib_core','Linux RDMA interface','rdma'),
        ('mlx5kernel',276,499,230,'mlx5_ib · mlx5_core','NIC resources / registration','mlx5kernel'),
        ('peermem',536,499,220,'nvidia-peermem / DMA-BUF','registration alternatives','peermem'),
        ('nvidia',802,499,310,'nvidia.ko','Kernel RM · GPU resources','nvidia'),
        ('uvm',802,594,310,'nvidia-uvm.ko','GPU virtual address mappings','uvm'),
        ('peer',36,754,240,'Peer GPU / VRAM','direct or NVSwitch','gpu'),
        ('gpu',536,754,220,'GPU / VRAM','SM · MMU · payload / queues','gpu'),
        ('nic',866,754,246,'NIC','IB / RoCE → remote NIC','nic'),
    ]
    for node_id,*node in nodes:
        out += box(*node,lang,node_id=node_id,paths='peer' if node_id=='peer' else None)
    for args in [
        (36,388,410,'/dev/infiniband/uverbsN','open · ioctl / write · mmap','dev-uverbs'),
        (536,388,280,'/dev/nvidiactl · /dev/nvidiaN','open · ioctl · mmap','dev-core'),
        (842,388,270,'/dev/nvidia-uvm','open · ioctl · mmap','dev-uvm'),
    ]:
        out += box(*args,lang,h=42)
    return out+'</svg>',856


# Message labels describe logical work; each arrow links to its implementation
# or, for hardware data movement, the public mechanism documentation.
SEQUENCES = {
    'rdma-write': {
        'actors': [('CPU A','libmlx5'),('A memory','SQ · CQ · 4 KiB'),('NIC A','RDMA requester'),('NIC B','RDMA responder'),('B memory','registered MR')],
        'actors_zh': [('A 的 CPU','libmlx5'),('A 主机内存','SQ · CQ · 4 KiB'),('A 网卡','RDMA 请求方'),('B 网卡','RDMA 响应方'),('B 主机内存','已注册 MR')],
        'rows': [
            (0,1,'① Write the RDMA Write WQE into the SQ ring; update the DBR','control','mlx5-send'),
            (0,2,'② MMIO doorbell write to the UAR page','control','mlx5-doorbell'),
            (1,2,'③ NIC A fetches the WQE and DMA-reads 4096 B','payload','dma-api'),
            (2,3,'④ RDMA Write: B address + rkey + 4096 B','payload','rdma-guide'),
            (3,3,'⑤ Validate rkey and MR access','control','verbs-mr'),
            (3,4,'⑥ NIC B DMA-writes 4096 B into B memory','payload','verbs-mr'),
            (3,2,'⑦ Acknowledgement','control','rdma-guide'),
            (2,1,'⑧ NIC A DMA-writes a CQE into the CQ ring','control','verbs-post-send'),
            (1,0,'⑨ ibv_poll_cq reads the CQE','control','mlx5-cq'),
        ],
        'labels_zh': [
            '① 在 SQ 环写入 RDMA Write 的 WQE，更新 DBR',
            '② 向 UAR 页写 doorbell（MMIO）',
            '③ A 网卡取得 WQE，DMA 读取 4096 B',
            '④ RDMA Write：B 的地址 + rkey + 4096 B',
            '⑤ 校验 rkey、MR 范围与远端写权限',
            '⑥ B 网卡把 4096 B DMA 写入 B 的内存',
            '⑦ 确认（ACK）',
            '⑧ A 网卡把 CQE DMA 写入 CQ 环',
            '⑨ ibv_poll_cq 读到 CQE',
        ],
        'bars': [(0,0,1),(0,8,8),(1,0,0),(1,2,2),(1,7,8),(2,1,7),(3,3,6),(4,5,5)],
    },
    'setup': {
        'actors':[('CPU library','host setup'),('verbs / mlx5','userspace provider'),('Linux drivers','RDMA + GPU'),('NIC','QP / MR'),('GPU memory','registered payload')],
        'rows':[
            (0,1,'Open device; allocate PD / CQ / QP','control','user-verbs'),
            (1,2,'uverbs: configure resources; map CPU queues / registers','control','user-verbs'),
            (2,3,'Create NIC resources and access protection','control','user-verbs'),
            (0,2,'Register GPU buffer: peer memory OR DMA-BUF','control','peermem'),
            (0,0,'Prepare connection information and memory access keys','control','user-verbs'),
            (1,3,'After setup: CPU provider submits a WR','control','mlx5-send'),
            (3,4,'NIC DMA accesses the registered GPU buffer','payload','gdr-doc'),
        ],
        'bars':[(0,0,4),(1,0,5),(2,1,3),(3,2,6),(4,6,6)],
    },
    'nvproxy': {
        'actors':[('User kernel','NVSHMEM API'),('Device transport','PROXY'),('CPU proxy','IBRC host transport'),('NIC','verbs / DMA'),('Peer GPU','target + signal')],
        'rows':[
            (0,1,'nvshmem_putmem_signal_nbi: select the proxy path','gpu','nv-dispatch'),
            (1,2,'Publish a request for host progress','gpu','nv-dispatch'),
            (2,3,'IBRC: build RDMA WRs; ibv_post_send','control','nv-proxy'),
            (3,4,'DMA / network payload; ordered remote notification','payload','nv-signal'),
            (3,2,'progress_send: poll CQ and track completed work','control','nv-proxy-cq'),
            (0,0,'nvshmem_quiet: wait for prior issued operations','gpu','nv-ordering'),
            (4,4,'signal_wait_until: receiver can consume its data','gpu','nv-signal'),
        ],
        'bars':[(0,0,5),(1,0,1),(2,1,4),(3,2,4),(4,3,6)],
    },
    'ibgda-path': {
        'actors':[('Host transport','IBGDA setup'),('User kernel','NVSHMEM API'),('IBGDA device','GPU queue state'),('NIC','mlx5 QP / CQ'),('Peer GPU','target + signal')],
        'rows':[
            (0,2,'Prepare GPU-accessible NIC resources and mappings','control','ibgda-host'),
            (1,2,'put / signal: dispatch to IBGDA','gpu','nv-dispatch'),
            (2,2,'Build WQEs; order writes and update queue state','gpu','ibgda-db'),
            (2,3,'Direct-GPU mode: update DBR and ring doorbell','gpu','ibgda-db'),
            (3,4,'NIC DMA / network transfer; ordered remote signal','payload','nv-signal'),
            (2,1,'quiet completion permits local source reuse','gpu','nv-ordering'),
            (4,4,'signal_wait_until: receiver data dependency','gpu','nv-signal'),
        ],
        'bars':[(0,0,0),(1,1,5),(2,0,5),(3,3,4),(4,4,6)],
    },
}


def sequence(kind,lang):
    spec = SEQUENCES[kind]
    name = f'interconnect-{kind}-{lang}'
    height = 104 + len(spec['rows'])*62 + 26
    actors = spec.get('actors_zh', spec['actors']) if lang == 'zh' else spec['actors']
    xs = [145,435,725,1015] if len(actors) == 4 else [120,350,580,810,1040]
    title = TITLES[kind][0 if lang == 'zh' else 1]
    out = svg_start(name,height,title)
    for i,(title,sub) in enumerate(actors):
        x=xs[i]
        out+=f'<g class="node"><rect x="{x-104}" y="16" width="208" height="54" rx="4"/>'
        out+=txt(x,39,title,15,weight=650)+txt(x,59,sub,12,cls='muted')+'</g>'
        out+=f'<path class="lifeline" d="M{x} 72V{height-14}"/>'
    for actor,begin,end in spec['bars']:
        y=102+begin*62
        out+=f'<rect class="activation" x="{xs[actor]-6}" y="{y-5}" width="12" height="{(end-begin)*62+27}" rx="1"/>'
    for i,(a,b,label,kind_,ref) in enumerate(spec['rows']):
        if lang == 'zh' and 'labels_zh' in spec:
            label = spec['labels_zh'][i]
        y=112+i*62
        x1,x2=xs[a],xs[b]
        # Keep labels inside the viewBox even for self-calls in the last lane.
        label_width = sum(14 if ord(char) > 255 else 8.5 for char in label) if 'labels_zh' in spec else len(label)*7.25
        w=min(1100,max(label_width, len(REFS[ref]['label'])*6.1)+14)
        # Self-calls start right of their loop when space allows, so the source label can sit beside it.
        lx=max(26,min(min(x1,x2)+(40 if a==b else 18),1138-w))
        path=f'M{x1+6} {y}H{x1+30}V{y+16}H{x1+6}' if a==b else f'M{x1+(6 if b>a else -6)} {y}H{x2+(-7 if b>a else 7)}'
        url=escape(REFS[ref]['url'],quote=True)
        out+=f'<a class="sequence-message" href="{url}" target="_blank" rel="noopener"><path class="seq-edge {kind_}" d="{path}" marker-end="url(#{name}-{kind_})"/>'
        out+=f'<rect class="message-paper" x="{lx-4}" y="{y-27}" width="{w}" height="21" rx="2"/>'
        out+=txt(lx,y-11,label,14,'start',f'msg-{kind_}',500)
        # Inline source links remain visible without overwhelming message labels.
        sy=y+23 if a!=b or lx>=x1+36 else y+34
        source=REFS[ref]['label'] if 'path' in REFS[ref] else 'documentation ↗'
        sw=len(source)*6.1+10
        out+=f'<rect class="message-paper" x="{lx-4}" y="{sy-12}" width="{sw}" height="17" rx="2"/>'
        out+=txt(lx,sy,source,11,'start','source-label')+'</a>'
    return out+'</svg>',height


TITLES = {
    'rdma-write':('RDMA Write · 把 4 KiB 从 A 写到 B','RDMA Write · 4 KiB from A to B'),
    'architecture':('GPU 互联：依赖与调用关系','GPU interconnect: dependencies and calls'),
    'setup':('资源建立 · CPU 控制路径','Resource setup · CPU control path'),
    'nvproxy':('NVSHMEM CPU proxy · IBRC','NVSHMEM CPU proxy · IBRC'),
    'ibgda-path':('NVSHMEM IBGDA · GPU 直接提交','NVSHMEM IBGDA · direct GPU submission'),
}
CAPTIONS = {
    'rdma-write':('两端已注册 MR，QP 处于 RTS，A 已拿到 B 的地址和 rkey。蓝色为控制，紫色为 payload。①② 由 A 的 CPU 在用户态完成；B 的 CPU 不参与。BlueFlame 写入时，② 把整个 WQE 一并写进 UAR（1.4 节）。', 'Both MRs are registered, the QP is in RTS, and A holds B\'s address and rkey. Blue: control. Purple: payload. A\'s CPU performs ① and ② in user space; B\'s CPU takes no part. With BlueFlame, ② also writes the whole WQE into the UAR (§1.4).'),
    'architecture':('箭头表示主要调用、资源依赖或数据流，分支按所选后端执行。选择路径可同时高亮节点与连线；点击节点查看说明，点击连线查看源码。GPU → NIC 展示直接 doorbell；CPU 代敲见第 4 章。','Arrows show principal calls, resource dependencies or data flow; branches depend on the backend. Select a path to highlight its nodes and edges. Nodes open explanations; edges link to source. GPU → NIC shows direct doorbells; CPU-rung doorbells are covered in chapter 4.'),
    'setup':('两端都要建立资源；图示一侧的准备与首次提交，显存注册二选一。之后的请求复用连接和注册信息。','Both endpoints establish resources. Shows one side\'s setup and first submission, with either GPU registration path. Later requests reuse connections and registrations.'),
    'nvproxy':('GPU 发布请求，CPU 构造并提交网卡 WR。图示远端 IBRC 路径与 GDR payload；接收端通知遵循 NVSHMEM signal 契约。','The GPU publishes requests; the CPU constructs and submits NIC WRs. Shows the remote IBRC path with GDR payload and NVSHMEM signal ordering.'),
    'ibgda-path':('图示 GPU 直接 doorbell（级别 5），CPU 代敲见第 4 章。应用 API 与 3.2 节的 IBRC 图相同，队列提交由 IBGDA 设备代码完成。','Direct GPU doorbells (level 5); CPU-rung doorbells are covered in chapter 4. The application API matches the IBRC sequence in §3.2; IBGDA device code performs queue submission.'),
}


def panel(lang):
    zh=lang=='zh'
    catalog={key:dict(layer='组件职责' if zh else 'Component responsibilities',row_description=1,section='#'+section+('' if zh else '-en'),section_label='章节说明' if zh else 'Section details',links=[dict(url=REFS[ref]['url'],label='源码 / 文档' if zh else 'Source / documentation')]) for key,(section,ref,paths) in COMPONENTS.items()}
    return f'''<script type="application/json" data-component-catalog>{json.dumps(catalog, ensure_ascii=False)}</script>
<div class="component-popover" id="interconnect-info-{lang}" popover="auto" hidden role="dialog" aria-labelledby="interconnect-title-{lang}">
<div class="component-layer" data-component-layer></div><div class="component-heading"><div class="component-title" id="interconnect-title-{lang}" data-component-title></div><button type="button" data-component-close>{'关闭' if zh else 'Close'}</button></div>
<div data-component-description></div><div class="component-meta" data-component-meta hidden><div data-component-meta-value></div></div>
<div class="component-references"><div data-component-links></div></div><a class="component-section" data-component-section><span></span> →</a></div>'''


def figure(kind,lang):
    idx=0 if lang=='zh' else 1
    title=TITLES[kind][idx]
    drawing,height=architecture(lang) if kind=='architecture' else sequence(kind,lang)
    focus=''
    if kind=='architecture':
        groups=[('普通 NCCL' if idx==0 else 'Ordinary NCCL',[('cpu','NET/IB · CPU proxy')]),('NVSHMEM',[('proxy','CPU proxy / IBRC'),('ibgda','IBGDA'),('nvgda','GPUNetIO')]),('NCCL GIN',[('ginproxy','CPU proxy'),('gdaki','GDAKI / GPUNetIO')]),('互联机制' if idx==0 else 'Interconnect mechanism',[('peer','CUDA peer / NVLink')])]
        destinations={'all':'#backend-map','cpu':'#proxy-compare','proxy':'#proxy-compare','ibgda':'#gpu-doorbell-impls','nvgda':'#gpu-doorbell-impls','gdaki':'#gpu-doorbell-impls','ginproxy':'#proxy-compare','peer':'gpu-peer-to-peer-memory.html'}
        destinations={key:href+('-en' if lang=='en' and href.startswith('#') else '') for key,href in destinations.items()}
        options=f'<option value="all" data-path-href="{destinations["all"]}">{"全部" if idx==0 else "All"}</option>'
        for group,items in groups:
            options+=f'<optgroup label="{group}">'+''.join(f'<option value="{key}" data-path-href="{destinations[key]}">{value}</option>' for key,value in items)+'</optgroup>'
        focus='<label>'+('路径 ' if idx==0 else 'Path ')+'<select data-path-focus>'+options+'</select></label>'
        focus+=f'<a class="path-reading-link" data-path-reading href="{destinations["all"]}">{"阅读路径说明" if idx==0 else "Read about this path"} →</a>'
    fit,actual=('适应窗口','原始尺寸') if idx==0 else ('Fit window','Actual size')
    return f'''<figure class="cuda-figure" data-size="fit" data-layout="{kind}" style="--diagram-ratio:{1160/height:.10f};--diagram-width:1160px"><div class="diagram-toolbar"><strong>{title}</strong>{focus}<button type="button" data-size-toggle aria-pressed="false" data-fit-label="{fit}" data-actual-label="{actual}">{actual}</button></div><div class="diagram-viewport" tabindex="0" role="region" aria-label="{title}">{drawing}</div><figcaption>{CAPTIONS[kind][idx]}</figcaption>{panel(lang) if kind=='architecture' else ''}</figure>'''


def inspection(lang):
    zh=lang=='zh'
    items=[
        ('GPU 拓扑' if zh else 'GPU topology','nvidia-smi topo -m','        GPU0  GPU1  NIC0\nGPU0     X    NV18  PIX\nGPU1    NV18   X    SYS',
         'NV# 表示一组 NVLink；PIX / SYS 描述 PCIe / 系统拓扑关系。应用是否启用 peer access 或 GDR，需结合配置与运行日志确认。' if zh else 'NV# denotes bonded NVLinks; PIX / SYS describe PCIe / system paths. Check application configuration and runtime logs to confirm whether peer access or GDR is enabled.'),
        ('RDMA 端口' if zh else 'RDMA port','rdma link show','link mlx5_0/1 state ACTIVE physical_state LINK_UP netdev eth2',
         '确认端口和对应设备；随后用 ibv_devinfo 核对 link_layer、能力与端口状态。' if zh else 'Identify the port and device, then inspect link_layer, capabilities and port state with ibv_devinfo.'),
        ('驱动绑定' if zh else 'Driver binding',"lspci -nnk | grep -A3 -Ei 'NVIDIA|Mellanox'",'Network controller: Mellanox Technologies ...\n    Kernel driver in use: mlx5_core',
         'mlx5_core 是 PCI 设备驱动；RDMA 功能还涉及 mlx5_ib、ib_core 等模块。' if zh else 'mlx5_core binds the PCI device; RDMA also involves mlx5_ib, ib_core and related modules.'),
        ('模块与辅助设备' if zh else 'Modules and auxiliary devices',"modinfo mlx5_ib | grep -E '^(alias|depends)'",'alias:          auxiliary:mlx5_core.rdma-rep\nalias:          auxiliary:mlx5_core.multiport\nalias:          auxiliary:mlx5_core.rdma\ndepends:        mlx5_core,ib_core,mlx_compat,ib_uverbs',
         'mlx5_ib 绑定 mlx5_core 创建的 .rdma 等辅助设备。mlx_compat 是 MLNX_OFED 的兼容层；发行版自带模块的依赖为 mlx5_core、ib_uverbs、ib_core。对 mlx5_core 执行同样的命令，可以看到 .eth 等别名。' if zh else 'mlx5_ib binds the .rdma and related auxiliary devices created by mlx5_core. mlx_compat is the MLNX_OFED compatibility layer; the distribution module depends on mlx5_core, ib_uverbs and ib_core. The same command on mlx5_core shows the .eth aliases.',
         '实测输出 · Linux 6.1.62 + MLNX_OFED 24.01' if zh else 'Measured · Linux 6.1.62 + MLNX_OFED 24.01'),
        ('运行时装载' if zh else 'Runtime libraries',"grep -E 'libnccl|nvshmem|libibverbs|libmlx5|gpunetio' /proc/12345/maps",'... /usr/lib/.../libnccl.so.2\n... /usr/lib/.../libibverbs.so.1\n... /usr/lib/.../libmlx5.so.1',
         '12345 替换为自己的进程 PID。dlopen 的 transport/provider 不一定出现在 ldd 中；静态链接或集成的代码也不一定表现为独立 .so。' if zh else 'Replace 12345 with your process PID. dlopen-loaded transports/providers may not appear in ldd; static or integrated code need not appear as a separate .so.'),
    ]
    out='<div class="cuda-inspection">'
    for title,cmd,output,note,*label in items:
        label=label[0] if label else ('示例输出' if zh else 'Example output')
        out+=f'<section class="inspection-item"><div class="inspection-heading"><strong>{title}</strong><span>{label}</span></div><pre class="inspection-command"><code>{escape(cmd)}</code></pre><pre class="inspection-output"><code>{escape(output)}</code></pre><p>{note}</p></section>'
    return out+'</div>'


def expand(lang):
    body=(ROOT/f'scripts/content/gpu-interconnect.{lang}.html').read_text()
    body=re.sub(r'\[\[([\w-]+)\|([^\]]+)\]\]',lambda m:link(m[1],m[2]),body)
    body=re.sub(r'\{\{code:([\w-]+)\}\}',lambda m:code(CODE[m[1]]),body)
    for kind in TITLES: body=body.replace('{{'+kind+'}}',figure(kind,lang))
    body=body.replace('{{inspection}}',inspection(lang))
    assert not re.search(r'\{\{[\w:-]+\}\}|\[\[[\w-]+\|', body)
    return body


def main():
    meta=dict(title='GPU 互联的软件与驱动',title_en='GPU interconnect software and drivers',slug='gpu-interconnect-software-stack',date='2026-11-09',tags='CUDA, NCCL, NVSHMEM, RDMA, NVLink',tags_en='CUDA, NCCL, NVSHMEM, RDMA, NVLink',reading='25 分钟',reading_en='25 min',summary='由 CPU proxy 提交网卡请求时，数据仍可直接在显存和网卡之间传输。各条路径的区别主要在于谁构造、提交网卡请求，谁处理完成。',summary_en='When a CPU proxy posts network requests, data can still move directly between GPU memory and the network adapter. The paths differ mainly in who posts requests and handles completion.',series='inside-cuda',series_title='Inside CUDA',series_title_en='Inside CUDA',series_order='2')
    metadata='\n'.join(f'<meta name="post:{key}" content="{escape(value,quote=True)}">' for key,value in meta.items())
    html=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{meta['title']}</title>
{metadata}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3"><link rel="stylesheet" href="{SHARED}style.css?v=gpu-stack-6"><link rel="stylesheet" href="{BASE}style.css?v=4">
<script src="../lang-toggle.js?v=post-toc-3" defer></script><script src="{SHARED}page.js?v=component-info-4" defer></script><script src="{BASE}page.js?v=1" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>{render_series_nav(meta, ROOT / 'posts')}</aside><main class="content cuda-article interconnect-article"><div class="lang-zh">{expand('zh')}</div><div class="lang-en">{expand('en')}</div></main></div></body></html>'''
    target=ROOT/'posts/gpu-interconnect-software-stack.html'
    target.write_text(html)
    print('Wrote',target)


if __name__=='__main__': main()
