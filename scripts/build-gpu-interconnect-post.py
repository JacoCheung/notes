#!/usr/bin/env python3
"""Inside CUDA #2. Pinned source references; diagrams are source schematics.

Design: compact editorial diagrams, variance 3 / motion 1 / density 7.
Reuse the series' accessible popovers and proportional window-fit controls.
"""
from html import escape
from pathlib import Path
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


CODE = {
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
    'nv-ibgda-env': "NVSHMEM_IB_ENABLE_IBGDA=1 ./your_nvshmem_app",
    'nv-gpunetio-env': "NVSHMEM_IB_ENABLE_IBGDA=0 \\\nNVSHMEM_REMOTE_TRANSPORT=gpunetio \\\nNVSHMEM_GPUNETIO_ENABLE_GDAKI=1 ./your_nvshmem_app",
    'gin-proxy-setup': '''
        ncclDevCommRequirements reqs = NCCL_DEV_COMM_REQUIREMENTS_INITIALIZER;
        reqs.ginType = NCCL_GIN_TYPE_PROXY;
        reqs.ginConnectionType = NCCL_GIN_CONNECTION_FULL;
        reqs.ginContextCount = 1;
        reqs.ginSignalCount = 1;
        ncclDevComm devComm;
        ncclDevCommCreate(comm, &reqs, &devComm);
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
        reqs.ginType = NCCL_GIN_TYPE_GDAKI;   // explicitly request this backend
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
    'nccl': ('libraries', 'nccl-api', 'cpu gdaki ginproxy'),
    'nvhost': ('libraries', 'nv-select', 'proxy ibgda nvgda'),
    'cuda': ('libraries', 'vmm-doc', ALL_PATHS),
    'verbs': ('libraries', 'user-verbs', NETWORK_PATHS),
    'mlx5': ('libraries', 'mlx5-send', NETWORK_PATHS),
    'gpunetio': ('gpunetio', 'gpureadme', 'nvgda gdaki'),
    'nvdevice': ('libraries', 'nv-dispatch', 'proxy ibgda nvgda'),
    'ibgda': ('ibgda', 'ibgda-db', 'ibgda'),
    'gin': ('windows', 'gin-api', 'gdaki ginproxy'),
    'nvidia': ('modules', 'gpu-core', ALL_PATHS),
    'uvm': ('modules', 'uvm', ALL_PATHS),
    'peermem': ('registration', 'gdaki-reg', NETWORK_PATHS),
    'rdma': ('modules', 'user-verbs', NETWORK_PATHS),
    'mlx5kernel': ('modules', 'user-verbs', NETWORK_PATHS),
    'gpu': ('modules', 'peer-post', ALL_PATHS),
    'nic': ('modules', 'gpureadme', NETWORK_PATHS),
}


def box(x, y, w, title, subtitle, component, lang, h=54, paths=None, node_id=None):
    paths = COMPONENTS[component][2] if paths is None else paths
    size = 13 if w < 200 else 15
    return f'<g class="node" data-node-id="{node_id or component}" data-paths="{paths}" data-component="{component}" data-component-title="{escape(title, quote=True)}" tabindex="0" role="button" aria-label="{escape(title, quote=True)}" aria-haspopup="dialog" aria-expanded="false" aria-controls="interconnect-info-{lang}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4"/>' + txt(x+w/2,y+23,title,size,weight=650) + txt(x+w/2,y+43,subtitle,11 if w < 200 else 12,cls='muted') + '</g>'


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
    out = svg_start(name, 792, 'GPU interconnect: calls, setup, submission and payload', True)
    legend = [('control','CPU 调用 / 提交' if zh else 'CPU call / submission'),
              ('setup','初始化 / 注册 / 映射' if zh else 'Setup / registration / mapping'),
              ('gpu','GPU 调用 / 请求' if zh else 'GPU call / request'),
              ('payload','Payload 数据路径' if zh else 'Payload data path')]
    for i,(kind,title) in enumerate(legend):
        x=30+i*290
        out += f'<path class="seq-edge {kind}" d="M{x} 24h34" marker-end="url(#{name}-{kind})"/>'
        out += txt(x+44,28,title,12,'start')
    for x,y,w,h,title in [(16,48,710,330,'CPU 用户态 · host libraries / proxy' if zh else 'CPU USER SPACE · host libraries / proxy'),
                          (746,48,398,330,'GPU kernel · device API' if zh else 'GPU KERNEL · device API'),
                          (16,394,1128,210,'Linux 内核 · 资源与权限' if zh else 'LINUX · resources / access'),
                          (16,642,1128,134,'硬件 · 直接数据通路' if zh else 'HARDWARE · direct payload paths')]:
        heading_x = 276 if y == 394 else x+16
        out += f'<rect class="band" x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/>' + txt(heading_x,y+23,title,14,'start',weight=600)
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
        ('verbs','rdma',[(100,334),(100,435)],'setup',NETWORK_PATHS,'user-verbs','Verbs establishes RDMA resources through uverbs',(166,407,'uverbs')),
        ('mlx5','rdma',[(350,334),(350,358),(210,358),(210,435)],'setup',NETWORK_PATHS,'user-verbs','mlx5 setup uses uverbs ioctl / mmap interfaces',(273,351,'ioctl / mmap')),
        ('cuda','nvidia',[(621,334),(621,370),(957,370),(957,435)],'setup',ALL_PATHS,'gpu-core','libcuda uses NVIDIA core device interfaces',(1026,414,'GPU ioctl')),
        ('cuda','uvm',[(684,334),(684,385),(780,385),(780,557),(802,557)],'setup',ALL_PATHS,'uvm','libcuda uses UVM device interfaces and mappings',None),
        ('rdma','mlx5kernel',[(246,462),(276,462)],'setup',NETWORK_PATHS,'user-verbs','RDMA core dispatches device resource operations to mlx5 drivers',None),
        ('mlx5kernel','peermem',[(506,462),(536,462)],'setup',NETWORK_PATHS,'gdr-doc','RDMA driver obtains GPU memory mappings via peer memory or DMA-BUF',None),
        ('peermem','nvidia',[(756,462),(802,462)],'setup',NETWORK_PATHS,'peermem','GPU memory registration cooperates with the NVIDIA GPU driver',None),
        ('uvm','nvidia',[(957,530),(957,489)],'setup',ALL_PATHS,'uvm','UVM cooperates with Kernel RM',(1024,515,'RM services'),True),
        ('mlx5kernel','nic',[(391,489),(391,598),(1075,598),(1075,690)],'setup',NETWORK_PATHS,'user-verbs','mlx5 drivers configure NIC hardware resources',(432,589,'NIC setup')),
        ('nvidia','gpu',[(957,489),(957,512),(646,512),(646,690)],'setup',ALL_PATHS,'gpu-core','GPU driver establishes GPU resources and mappings',(598,548,'GPU setup')),
        ('uvm','gpu',[(802,557),(710,557),(710,690)],'setup',ALL_PATHS,'uvm','UVM manages GPU virtual address mappings',None),
        ('mlx5','nic',[(506,307),(520,307),(520,625),(990,625),(990,690)],'control','cpu proxy ginproxy','mlx5-send','CPU fast path writes WQEs / rings doorbells after resource setup',(812,619,'CPU WQE / doorbell')),
        ('gpudevice','nic',[(850,334),(850,386),(1140,386),(1140,717),(1112,717)],'gpu','gdaki nvgda','gpu-submit','GPUNetIO device verbs submit WQEs and ring a direct GPU doorbell',(1015,367,'GPU WQE / doorbell')),
        ('ibgda','nic',[(1128,307),(1140,307),(1140,717),(1112,717)],'gpu','ibgda','ibgda-db','IBGDA device code submits WQEs and rings a direct GPU doorbell',None),
        ('gpu','nic',[(756,717),(866,717)],'payload',NETWORK_PATHS,'gdr-doc','GPUDirect RDMA payload moves directly between GPU memory and NIC',(811,705,'GDR / DMA'),True),
        ('gpu','peer',[(536,717),(276,717)],'payload','peer','peer-post','GPU peer memory traffic uses NVLink / PCIe, directly or through NVSwitch',(406,705,'NVLink / PCIe'),True),
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
        ('rdma',36,435,210,'ib_uverbs · ib_core','Linux RDMA interface','rdma'),
        ('mlx5kernel',276,435,230,'mlx5_ib · mlx5_core','NIC resources / registration','mlx5kernel'),
        ('peermem',536,435,220,'nvidia-peermem / DMA-BUF','registration alternatives','peermem'),
        ('nvidia',802,435,310,'nvidia.ko','Kernel RM · GPU resources','nvidia'),
        ('uvm',802,530,310,'nvidia-uvm.ko','GPU virtual address mappings','uvm'),
        ('peer',36,690,240,'Peer GPU / VRAM','direct or NVSwitch','gpu'),
        ('gpu',536,690,220,'GPU / VRAM','SM · MMU · payload / queues','gpu'),
        ('nic',866,690,246,'NIC','IB / RoCE → remote NIC','nic'),
    ]
    for node_id,*node in nodes:
        out += box(*node,lang,node_id=node_id,paths='peer' if node_id=='peer' else None)
    return out+'</svg>',792


# Message labels describe logical work; each arrow links to its implementation
# or, for hardware data movement, the public mechanism documentation.
SEQUENCES = {
    'setup': {
        'actors':[('CPU library','host setup'),('verbs / mlx5','userspace provider'),('Linux drivers','RDMA + GPU'),('NIC','QP / MR'),('GPU memory','registered payload')],
        'rows':[
            (0,1,'Open device; allocate PD / CQ / QP','control','user-verbs'),
            (1,2,'uverbs: configure resources; map CPU queues / registers','control','user-verbs'),
            (2,3,'Create NIC resources and access protection','control','user-verbs'),
            (0,2,'Register GPU buffer: peer memory OR DMA-BUF','control','nccl-reg'),
            (0,0,'Prepare connection information and memory access keys','control','user-verbs'),
            (1,3,'After setup: CPU provider submits a WR','control','mlx5-send'),
            (3,4,'NIC DMA accesses the registered GPU buffer','payload','gdr-doc'),
        ],
        'bars':[(0,0,4),(1,0,5),(2,1,3),(3,2,6),(4,6,6)],
    },
    'cpu': {
        'actors':[('Application','CPU thread'),('GPU 0','NCCL kernel'),('CPU proxy','NET/IB'),('Local NIC','verbs queues'),('Remote NIC / GPU','receive side')],
        'rows':[
            (0,1,'ncclAllReduce: schedule collective work on a CUDA stream','control','nccl-api'),
            (1,2,'Publish chunk readiness / FIFO progress','gpu','nccl-proxy'),
            (2,3,'isend → ncclIbIsend → ibv_post_send → mlx5','control','nccl-isend'),
            (1,3,'NIC DMA reads registered GPU payload','payload','gdr-doc'),
            (3,4,'Network transfer → remote registered GPU buffer','payload','gdr-doc'),
            (3,2,'test → ibv_poll_cq: observe completion','control','nccl-cq'),
            (2,1,'Update GPU-visible head / progress','control','nccl-proxy'),
        ],
        'bars':[(0,0,0),(1,0,6),(2,1,6),(3,2,5),(4,4,5)],
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
    'nvgda': {
        'actors':[('Host transport','NVSHMEM / GPUNetIO'),('User kernel','NVSHMEM API'),('GPUNetIO device','exported QP / CQ'),('NIC','RDMA work'),('Peer GPU','target + signal')],
        'rows':[
            (0,2,'Create resources; export GPU queue descriptors','control','gpu-export'),
            (1,2,'GPUNETIO_GDAKI: put / signal through device verbs','gpu','nv-dispatch'),
            (2,2,'doca_gpu_dev_verbs_put_signal: prepare WQEs','gpu','gpu-put'),
            (2,3,'Direct-GPU mode: publish queue and ring doorbell','gpu','gpu-submit'),
            (3,4,'NIC DMA / network transfer; ordered remote signal','payload','nv-signal'),
            (3,2,'Device-side CQ polling observes local completion','gpu','gpu-cq'),
            (2,1,'Complete the NVSHMEM quiet dependency','gpu','nv-ordering'),
            (4,4,'signal_wait_until: receiver data dependency','gpu','nv-signal'),
        ],
        'bars':[(0,0,0),(1,1,6),(2,0,6),(3,3,5),(4,4,7)],
    },
    'ginproxy': {
        'actors':[('User kernel','NCCL GIN'),('GIN device proxy','request descriptors'),('CPU progress','IB RMA backend'),('NIC','verbs / DMA'),('Peer kernel','target + signal')],
        'rows':[
            (0,1,'gin.put: use the CPU-proxy backend','gpu','gin-api'),
            (1,2,'Publish GFD; proxyGinPollGfd consumes the request','gpu','gin-proxy'),
            (2,3,'iputSignal → build WRs → ibv_post_send','control','gin-verbs'),
            (3,4,'DMA / network writes payload and associated signal','payload','gin-api'),
            (3,2,'RMA backend test observes request completion','control','gin-proxy-completion'),
            (2,1,'Update the GPU-visible completion counter','control','gin-proxy-completion'),
            (0,0,'gin.flush: local source reuse is safe','gpu','gin-api'),
            (4,4,'waitSignal: receiver data dependency','gpu','gin-api'),
        ],
        'bars':[(0,0,6),(1,0,5),(2,1,5),(3,2,4),(4,3,7)],
    },
    'gdaki': {
        'actors':[('User kernel','NCCL GIN'),('GDAKI backend','GPUNetIO device'),('Local NIC','GPU-accessible QP'),('Remote NIC','RDMA target'),('Peer kernel','signal wait')],
        'rows':[
            (0,1,'gin.put: resolve peer, window keys and offsets','gpu','gdaki-put'),
            (1,1,'doca_gpu_dev_verbs_put_signal: build / publish WQEs','gpu','gpu-put'),
            (1,2,'Direct-GPU mode: ring the NIC doorbell','gpu','gpu-submit'),
            (2,3,'NIC reads source VRAM; network carries the write','payload','gdr-doc'),
            (3,4,'Write destination VRAM; publish the associated signal','payload','gin-api'),
            (2,1,'CQE / completion: device-side wait or poll','gpu','gpu-cq'),
            (0,0,'gin.flush: local source reuse is safe','gpu','gin-api'),
            (4,4,'waitSignal: acquire the incoming data dependency','gpu','gin-api'),
        ],
        'bars':[(0,0,6),(1,0,5),(2,2,5),(3,3,4),(4,4,7)],
    },
    'fabric': {
        'actors':[('Node A','exporter / GPU'),('IMEX / driver A','compute node A'),('IMEX / driver B','compute node B'),('Node B','importer / GPU'),('NVLink fabric','GPU / NVSwitch')],
        'rows':[
            (0,1,'Create / export allocation with a FABRIC handle','control','vmm-doc'),
            (0,3,'Application exchanges the shareable handle','control','vmm-doc'),
            (3,2,'Import and map allocation with permitted IMEX access','control','imex-doc'),
            (1,2,'IMEX control coordination over TCP / gRPC','control','rack-doc'),
            (3,4,'After mapping: GPU load/store transactions over NVLink','payload','vmm-doc'),
            (4,0,'Peer GPU memory participates through the fabric','payload','peer-post'),
        ],
        'bars':[(0,0,1),(1,0,3),(2,2,3),(3,1,4),(4,4,5)],
    },
}


def sequence(kind,lang):
    spec = SEQUENCES[kind]
    name = f'interconnect-{kind}-{lang}'
    height = 104 + len(spec['rows'])*62 + 26
    xs = [120,350,580,810,1040]
    out = svg_start(name,height,kind+' communication sequence')
    for i,(title,sub) in enumerate(spec['actors']):
        x=xs[i]
        out+=f'<g class="node"><rect x="{x-104}" y="16" width="208" height="54" rx="4"/>'
        out+=txt(x,39,title,15,weight=650)+txt(x,59,sub,12,cls='muted')+'</g>'
        out+=f'<path class="lifeline" d="M{x} 72V{height-14}"/>'
    for actor,begin,end in spec['bars']:
        y=102+begin*62
        out+=f'<rect class="activation" x="{xs[actor]-6}" y="{y-5}" width="12" height="{(end-begin)*62+27}" rx="1"/>'
    for i,(a,b,label,kind_,ref) in enumerate(spec['rows']):
        y=112+i*62
        x1,x2=xs[a],xs[b]
        # Keep labels inside the viewBox even for self-calls in the last lane.
        w=min(1100,max(len(label)*7.25, len(REFS[ref]['label'])*6.1)+14)
        lx=max(26,min(min(x1,x2)+18,1138-w))
        path=f'M{x1+6} {y}H{x1+30}V{y+16}H{x1+6}' if a==b else f'M{x1+(6 if b>a else -6)} {y}H{x2+(-7 if b>a else 7)}'
        url=escape(REFS[ref]['url'],quote=True)
        out+=f'<a class="sequence-message" href="{url}" target="_blank" rel="noopener"><path class="seq-edge {kind_}" d="{path}" marker-end="url(#{name}-{kind_})"/>'
        out+=f'<rect class="message-paper" x="{lx-4}" y="{y-27}" width="{w}" height="21" rx="2"/>'
        out+=txt(lx,y-11,label,14,'start',f'msg-{kind_}',500)
        # Inline source links remain visible without overwhelming message labels.
        sy=y+23 if a!=b else y+34
        source=REFS[ref]['label'] if 'path' in REFS[ref] else 'documentation ↗'
        sw=len(source)*6.1+10
        out+=f'<rect class="message-paper" x="{lx-4}" y="{sy-12}" width="{sw}" height="17" rx="2"/>'
        out+=txt(lx,sy,source,11,'start','source-label')+'</a>'
    return out+'</svg>',height


TITLES = {
    'architecture':('GPU 互联：依赖与调用关系','GPU interconnect: dependencies and calls'),
    'setup':('资源建立 · CPU 控制路径','Resource setup · CPU control path'),
    'cpu':('NCCL NET/IB · 一个发送 chunk','NCCL NET/IB · one outgoing chunk'),
    'nvproxy':('NVSHMEM CPU proxy · IBRC','NVSHMEM CPU proxy · IBRC'),
    'ibgda-path':('NVSHMEM IBGDA · GPU 直接提交','NVSHMEM IBGDA · direct GPU submission'),
    'nvgda':('NVSHMEM GPUNetIO · GPU 直接提交','NVSHMEM GPUNetIO · direct GPU submission'),
    'ginproxy':('NCCL GIN · CPU proxy 提交','NCCL GIN · CPU proxy submission'),
    'gdaki':('NCCL GIN / GDAKI · GPU 直接 doorbell','NCCL GIN / GDAKI · direct GPU doorbell'),
    'fabric':('跨 OS 的 NVLink 内存共享','NVLink memory sharing across operating systems'),
}
CAPTIONS = {
    'architecture':('箭头表示主要调用、资源依赖或数据流，分支按所选 backend 执行。选择路径可同时高亮节点与连线；点击节点查看说明，点击连线查看源码。GPU → NIC 展示直接 doorbell 模式；CPU 辅助模式见各路径的 doorbell 说明。','Arrows show principal calls, resource dependencies or data flow; branches depend on the backend. Select a path to highlight its nodes and edges. Nodes open explanations; edges link to source. GPU → NIC shows direct doorbells; CPU assistance is described with each path.'),
    'setup':('两端都要建立资源；图示 CPU verbs 路径一侧的准备与首次提交。后续 chunk 复用连接和注册信息。','Both endpoints establish resources. Shows setup and the first CPU verbs submission; later chunks reuse connections and registrations.'),
    'cpu':('假设 GDR 已启用。紫色表示 payload；蓝色表示 CPU 控制；绿色表示 GPU 工作。接收端的 proxy 与可见性处理合并展示。','Assumes GDR. Purple: payload. Blue: CPU control. Teal: GPU work. Receiver-side proxy and visibility handling are summarized.'),
    'nvproxy':('GPU 发布请求，CPU 构造并提交网卡 WR。图示远端 IBRC 路径与 GDR payload；接收端通知遵循 NVSHMEM signal 契约。','The GPU publishes requests; the CPU constructs and submits NIC WRs. Shows the remote IBRC path with GDR payload and NVSHMEM signal ordering.'),
    'ibgda-path':('图示 GPU 直接 doorbell；CPU 辅助模式另见本章。与 NVSHMEM CPU proxy 使用相同应用 API，队列提交由 IBGDA device 实现。','Direct GPU doorbells; CPU-assisted mode is covered in this chapter. The application API is unchanged; IBGDA device code implements queue submission.'),
    'nvgda':('CPU 建立并导出资源；GPU 调用 GPUNetIO device verbs。图示直接 doorbell，CPU 辅助模式改变通知步骤。','The CPU creates and exports resources; GPU code calls GPUNetIO device verbs. Shows direct doorbells; CPU assistance changes the notification step.'),
    'ginproxy':('内置 IB RMA 后端示意。GPU 发布 GIN 描述符，CPU 生成 WR；这与 GPU 已构造 WQE 后由 CPU 辅助敲 doorbell 的分工不同。','Built-in IB RMA backend. GPU code publishes GIN descriptors and the CPU builds WRs. With CPU-assisted doorbells, the GPU has already built the WQEs.'),
    'gdaki':('图示 direct-GPU doorbell 模式。CPU-assisted 模式会增加 GPU → CPU notification → NIC doorbell；payload 路径保持直接 DMA。','Direct-GPU doorbell mode. CPU-assisted mode adds GPU → CPU notification → NIC doorbell; payload still uses direct DMA.'),
    'fabric':('逻辑依赖示意，非 IMEX RPC 时序实测。Fabric Manager / NVLSM 已按平台完成 fabric 配置；管理连接与 NVLink payload 分开。','Logical dependencies, not an IMEX RPC trace. Platform services have configured the fabric; management traffic is distinct from NVLink payload.'),
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
        labels=[('all','全部' if idx==0 else 'All'),('cpu','NCCL NET/IB'),('proxy','NVSHMEM + proxy'),('ibgda','NVSHMEM IBGDA'),('nvgda','NVSHMEM / GPUNetIO'),('gdaki','NCCL GIN / GDAKI'),('ginproxy','NCCL GIN / CPU proxy'),('peer','CUDA peer')]
        destinations={'all':'#submission','cpu':'#nccl-cpu','proxy':'#nvshmem','ibgda':'#ibgda','nvgda':'#gpunetio','gdaki':'#gin','ginproxy':'#gin-proxy','peer':'gpu-peer-to-peer-memory.html'}
        destinations={key:href+('-en' if lang=='en' and href.startswith('#') else '') for key,href in destinations.items()}
        focus='<label>'+('路径 ' if idx==0 else 'Path ')+'<select data-path-focus>'+''.join(f'<option value="{key}" data-path-href="{destinations[key]}">{value}</option>' for key,value in labels)+'</select></label>'
        focus+=f'<a class="path-reading-link" data-path-reading href="{destinations["all"]}">{"阅读路径说明" if idx==0 else "Read about this path"} →</a>'
    fit,actual=('适应窗口','原始尺寸') if idx==0 else ('Fit window','Actual size')
    return f'''<figure class="cuda-figure" data-size="fit" data-layout="{kind}" style="--diagram-ratio:{1160/height:.10f};--diagram-width:1160px"><div class="diagram-toolbar"><strong>{title}</strong>{focus}<button type="button" data-size-toggle aria-pressed="false" data-fit-label="{fit}" data-actual-label="{actual}">{actual}</button></div><div class="diagram-viewport" tabindex="0" role="region" aria-label="{title}">{drawing}</div><figcaption>{CAPTIONS[kind][idx]}</figcaption>{panel(lang) if kind=='architecture' else ''}</figure>'''


def inspection(lang):
    zh=lang=='zh'
    items=[
        ('GPU 拓扑' if zh else 'GPU topology','nvidia-smi topo -m','        GPU0  GPU1  NIC0\nGPU0     X    NV18  PIX\nGPU1    NV18   X    SYS',
         'NV# 表示一组 NVLink；PIX / SYS 描述 PCIe / 系统拓扑关系。矩阵本身不能证明应用已经启用 peer access 或 GDR。' if zh else 'NV# denotes bonded NVLinks; PIX / SYS describe PCIe / system paths. The matrix does not prove that an application enabled peer access or GDR.'),
        ('RDMA 端口' if zh else 'RDMA port','rdma link show','link mlx5_0/1 state ACTIVE physical_state LINK_UP netdev eth2',
         '确认端口和对应设备；随后用 ibv_devinfo 核对 link_layer、能力与端口状态。' if zh else 'Identify the port and device, then inspect link_layer, capabilities and port state with ibv_devinfo.'),
        ('驱动绑定' if zh else 'Driver binding',"lspci -nnk | grep -A3 -Ei 'NVIDIA|Mellanox'",'Network controller: Mellanox Technologies ...\n    Kernel driver in use: mlx5_core',
         'mlx5_core 是 PCI 设备驱动；RDMA 功能还涉及 mlx5_ib、ib_core 等模块。' if zh else 'mlx5_core binds the PCI device; RDMA also involves mlx5_ib, ib_core and related modules.'),
        ('运行时装载' if zh else 'Runtime libraries',"grep -E 'libnccl|nvshmem|libibverbs|libmlx5|gpunetio' /proc/12345/maps",'... /usr/lib/.../libnccl.so.2\n... /usr/lib/.../libibverbs.so.1\n... /usr/lib/.../libmlx5.so.1',
         '12345 替换为自己的进程 PID。dlopen 的 transport/provider 不一定出现在 ldd 中；静态链接或集成的代码也不一定表现为独立 .so。' if zh else 'Replace 12345 with your process PID. dlopen-loaded transports/providers may not appear in ldd; static or integrated code need not appear as a separate .so.'),
    ]
    out='<div class="cuda-inspection">'
    for title,cmd,output,note in items:
        out+=f'<section class="inspection-item"><div class="inspection-heading"><strong>{title}</strong><span>{"格式示例 · 非实测" if zh else "Illustrative format · not captured"}</span></div><pre class="inspection-command"><code>{escape(cmd)}</code></pre><pre class="inspection-output"><code>{escape(output)}</code></pre><p>{note}</p></section>'
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
    meta=dict(title='GPU 互联的软件与驱动',title_en='GPU interconnect software and drivers',slug='gpu-interconnect-software-stack',date='2026-11-09',tags='CUDA, NCCL, NVSHMEM, RDMA, NVLink',tags_en='CUDA, NCCL, NVSHMEM, RDMA, NVLink',reading='25 分钟',reading_en='25 min',summary='从资源建立、请求提交到数据传输，解析 NCCL CPU proxy、NVSHMEM IBGDA、GPUNetIO Verbs、NCCL GIN/GDAKI，以及 Linux 驱动与 NVLink fabric 管理。',summary_en='Follow setup, request submission and payload movement through NCCL CPU proxies, NVSHMEM IBGDA, GPUNetIO Verbs, NCCL GIN/GDAKI, Linux drivers and NVLink fabric services.',series='inside-cuda',series_title='Inside CUDA',series_title_en='Inside CUDA',series_order='2')
    metadata='\n'.join(f'<meta name="post:{key}" content="{escape(value,quote=True)}">' for key,value in meta.items())
    html=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{meta['title']}</title>
{metadata}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3"><link rel="stylesheet" href="{SHARED}style.css?v=gpu-stack-5"><link rel="stylesheet" href="{BASE}style.css?v=3">
<script src="../lang-toggle.js?v=post-toc-3" defer></script><script src="{SHARED}page.js?v=component-info-4" defer></script><script src="{BASE}page.js?v=1" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div></aside><main class="content cuda-article interconnect-article"><div class="lang-zh">{expand('zh')}</div><div class="lang-en">{expand('en')}</div></main></div></body></html>'''
    target=ROOT/'posts/gpu-interconnect-software-stack.html'
    target.write_text(html)
    print('Wrote',target)


if __name__=='__main__': main()
