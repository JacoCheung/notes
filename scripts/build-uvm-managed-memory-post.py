#!/usr/bin/env python3
"""Build Inside CUDA #3, with pinned source links and inline SVG diagrams.

Diagrams show logical dependencies, not measured timing. Reuse the site's
reading column, intrinsic tables/code, theme, TOC and diagram size controls.
"""
from html import escape
from pathlib import Path
from post_series import render_series_nav
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
BASE = '../assets/inside-cuda/managed-memory/'
SHARED = '../assets/inside-cuda/linux-stack/'
SHA = '6f3be8c9c3fb4ed6ffc607a0d32d31ce4db7fba5'
SRC = f'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/{SHA}/'
UVM = SRC + 'kernel-open/nvidia-uvm/'
DOC = 'https://docs.nvidia.com/cuda/archive/12.4.1/'
FBGEMM = 'https://github.com/pytorch/FBGEMM/blob/294be72917f5bfc0518c8f09cb5d059fd8b7bee5/fbgemm_gpu/'
TBE = FBGEMM + 'fbgemm_gpu/split_table_batched_embeddings_ops_training.py'
LINKS = {
    'tbe-placement': TBE + '#L483-L503',
    'tbe-allocation': TBE + '#L392-L422',
    'tbe-managed': FBGEMM + 'src/memory_utils/memory_utils.cu#L161-L171',
    'tbe-advice': FBGEMM + 'src/memory_utils/memory_utils.cu#L266-L301',
    'tbe-cache': TBE + '#L4656-L4665',
    'tbe-prefetch': TBE + '#L3816-L3848',
    'residency-policy': UVM + 'uvm_va_block.c#L11283-L11434',
    'cpu-residency': UVM + 'uvm_va_block.c#L12519-L12551',
    'gpu-residency': UVM + 'uvm_gpu_replayable_faults.c#L1512-L1580',
    'host-direct': 'https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/unified-memory.html#direct-unified-memory-access-from-the-host',
    'grace-memory': 'https://developer.nvidia.com/blog/nvidia-grace-hopper-superchip-architecture-in-depth/',
    'hardware-coherence': 'https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/unified-memory.html#cpu-and-gpu-page-tables-hardware-coherency-vs-software-coherency',
    'cdmm': 'https://dam-cdn.nvd.orangelogic.com/AssetLink/77dn7clj03ib0kiritw143238xspfu4b.pdf#page=9',
    'access-counters': 'https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/unified-memory.html#access-counter-migration',
    'cpu-dispatch': UVM + 'uvm_va_space.c#L2716-L2728',
    'cpu-block': UVM + 'uvm_va_block.c#L12442-L12596',
    'cpu-return': UVM + 'uvm_va_space.c#L2771-L2779',
    'cpu-insert': UVM + 'uvm_va_block.c#L7931-L7986',
    'cpu-map-wait': UVM + 'uvm_va_block.c#L8136-L8149',
    'cpu-unmap': UVM + 'uvm_va_block.c#L5845-L5895',
    'resident-copy': UVM + 'uvm_va_block.c#L4752-L4866',
    'service-finish': UVM + 'uvm_va_block.c#L12005-L12075',
    'gpu-clear': UVM + 'uvm_va_block.c#L5930-L5962',
    'gpu-write': UVM + 'uvm_va_block.c#L5970-L6033',
    'gpu-map': UVM + 'uvm_va_block.c#L8255-L8367',
    'linux-fault': 'https://github.com/torvalds/linux/blob/v6.12/mm/memory.c#L4855-L4882',
    'linux-insert': 'https://github.com/torvalds/linux/blob/v6.12/mm/memory.c#L2219-L2237',
    'linux-tlb': 'https://docs.kernel.org/core-api/cachetlb.html',
    'release': SRC + 'README.md',
    'memory-api': DOC + 'cuda-runtime-api/group__CUDART__MEMORY.html',
    'um-guide': DOC + 'cuda-c-programming-guide/index.html#unified-memory-programming',
    'mapped': DOC + 'cuda-c-programming-guide/index.html#mapped-memory',
    'page-locked': DOC + 'cuda-c-programming-guide/index.html#page-locked-host-memory',
    'pointer': DOC + 'cuda-runtime-api/group__CUDART__UNIFIED.html',
    'ptx': DOC + 'parallel-thread-execution/index.html#data-movement-and-conversion-instructions-ld',
    'pte': UVM + 'hwref/hopper/gh100/dev_mmu.h#L489-L547',
    'pte-make': UVM + 'uvm_hopper_mmu.c#L177-L223',
    'pte-pcf': UVM + 'uvm_hopper_mmu.c#L131-L175',
    'pte-invalid': UVM + 'uvm_hopper_mmu.c#L238-L254',
    'mmu-hopper': UVM + 'uvm_hopper_mmu.c#L24-L116',
    'mmu-blackwell': UVM + 'uvm_blackwell_mmu.c#L24-L112',
    'mmu-ats': UVM + 'uvm_hopper_mmu.c#L329-L367',
    'coherent': SRC + 'src/nvidia/inc/libraries/mmu/gmmu_fmt.h#L314-L337',
    'range-create': UVM + 'uvm_va_range.c#L207-L268',
    'range-find': UVM + 'uvm_va_range.c#L1973-L1977',
    'range-type': UVM + 'uvm_va_range.h#L483-L490',
    'range-tree': UVM + 'uvm_va_space.h#L208-L209',
    'range-policy': UVM + 'uvm_va_range.h#L62-L69',
    'block': UVM + 'uvm_va_block.h#L48-L69',
    'block-state': UVM + 'uvm_va_block.h#L101-L135',
    'block-find': UVM + 'uvm_va_block.c#L12626-L12660',
    'block-service': UVM + 'uvm_va_block.c#L12104-L12156',
    'block-copy': UVM + 'uvm_va_block.c#L3964-L3995',
    'block-map': UVM + 'uvm_va_block.c#L8436-L8470',
    'mmap': UVM + 'uvm.c#L837-L858',
    'cpu-fault': UVM + 'uvm.c#L558-L574',
    'fops': UVM + 'uvm.c#L1074-L1084',
    'irq-top': UVM + 'uvm_gpu_isr.c#L194-L218',
    'irq-queue': UVM + 'uvm_gpu_isr.c#L86-L118',
    'irq-bottom': UVM + 'uvm_gpu_isr.c#L592-L627',
    'fault-batch': UVM + 'uvm_gpu_replayable_faults.c#L2900-L2948',
    'fault-space': UVM + 'uvm_gpu_replayable_faults.c#L1000-L1028',
    'fault-range': UVM + 'uvm_gpu_replayable_faults.c#L1940-L2045',
    'fault-replay': UVM + 'uvm_gpu_replayable_faults.c#L490-L518',
    'pin-linux': 'https://docs.kernel.org/core-api/pin_user_pages.html',
    'migration': 'https://developer.nvidia.com/blog/maximizing-unified-memory-performance-cuda/',
    'nsys': 'https://docs.nvidia.com/nsight-systems/UserGuide/#unified-memory-gpu-page-faults',
    'driver-post': 'cuda-linux-driver-stack.html',
    'peer-post': 'gpu-peer-to-peer-memory.html',
    'network-post': 'gpu-interconnect-software-stack.html',
    'peermem': 'https://docs.nvidia.com/cuda/gpudirect-rdma/#using-nvidia-peermem',
}

CODE = {
    'run': """
        nvcc -O2 -lineinfo managed_vs_pinned.cu -o managed_vs_pinned
        ./managed_vs_pinned managed
        ./managed_vs_pinned pinned
    """,
}


def link(key, label):
    return f'<a href="{escape(LINKS[key], quote=True)}">{label}</a>'


def text(x, y, value, size=16, anchor='middle', cls='', weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" class="{cls}" font-weight="{weight}">{escape(value)}</text>'


def svg_start(name, width, height, title, desc):
    out = f'<svg class="cuda-diagram uvm-diagram" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{name}-title {name}-desc"><title id="{name}-title">{escape(title)}</title><desc id="{name}-desc">{escape(desc)}</desc><defs>'
    for kind, cls in [('normal', 'arrow-head'), ('fault', 'fault-head'), ('host', 'host-head')]:
        out += f'<marker id="{name}-{kind}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="{cls}" d="M0 0L10 5L0 10Z"/></marker>'
    return out + '</defs>'


def node(x, y, w, h, lines, key=None, core=False):
    out = f'<g class="node{" core" if core else ""}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4"/>'
    for i, line in enumerate(lines):
        out += text(x+w/2, y+25+i*22, line, 16 if i == 0 else 13, cls='' if i == 0 else 'muted', weight=600 if i == 0 else 400)
    out += '</g>'
    return f'<a href="{LINKS[key]}" target="_blank" rel="noopener">{out}</a>' if key else out


def path(name, d, kind='normal', dashed=False):
    dash = ' stroke-dasharray="6 4"' if dashed else ''
    return f'<path class="edge {kind}-edge" d="{d}" marker-end="url(#{name}-{kind})"{dash}/>'


def architecture(lang):
    zh=lang=='zh'; name=f'uvm-architecture-{lang}'
    out=svg_start(name,1000,650,'UVM software and hardware layers',
        '用户态 CUDA 库、Linux MM、UVM 与 RM，以及执行地址翻译和数据访问的硬件。' if zh else
        'User-space CUDA libraries, Linux MM, UVM and RM, and hardware translation and data access.')
    for y,h,cls,title in [(18,174,'band','CPU 用户态' if zh else 'CPU user space'),(216,218,'band','CPU 内核态 · Linux' if zh else 'CPU kernel · Linux'),(466,148,'board','硬件' if zh else 'Hardware')]:
        out+=f'<rect class="{cls}" x="18" y="{y}" width="964" height="{h}" rx="5"/>'
        out+=text(40,y+28,title,17,'start',weight=600)
    # Paths are drawn before nodes; none crosses a node or its title.
    for d in ['M300 115H370','M620 115H690','M825 148V282','M740 148V250H495V282',
              'M170 358V518','M495 358V518']:
        out+=path(name,d)
    for d in ['M370 320H300','M620 320H690']:
        out+=f'<path class="edge normal-edge" d="{d}" marker-start="url(#{name}-normal)" marker-end="url(#{name}-normal)"/>'
    out+=node(40,82,260,66,['Application / framework','cudaMallocManaged(&p, bytes)'],'memory-api')
    out+=node(370,82,250,66,['libcudart.so','CUDA Runtime API'],'memory-api')
    out+=node(690,82,270,66,['libcuda.so.1','CUDA Driver API'],'driver-post',True)
    out+=node(40,282,260,76,['Linux MM / VMA','CPU fault callback', 'CPU page tables'],'linux-fault')
    out+=node(370,282,250,76,['nvidia-uvm.ko','ranges / residency','faults / migration'],'fops',True)
    out+=node(690,282,270,76,['nvidia.ko / RM','GPU resources / IRQ','memory infrastructure'],'irq-top')
    out+=text(606,238,'UVM ioctl / mmap',13)
    out+=text(843,220,'RM',13,'start')
    out+=text(335,304,'VMA / PTE',10)
    out+=text(655,304,'RM',12)
    out+=text(185,400,'CPU PTE / TLB',13,'start')
    out+=text(510,400,'GPU work: copy / PTE / TLB',13,'start')
    out+=node(40,518,260,66,['CPU MMU / TLB','Host RAM'],'linux-tlb')
    out+=node(370,518,590,66,['GPU SM / MMU / TLB / Copy Engine','VRAM · host-memory access via interconnect'],'gpu-write')
    out+=text(28,638,'依赖与职责分层；缺页进入 UVM 的具体方向见后文序列图。' if zh else
        'Dependencies and responsibilities; fault entry paths are detailed in the following sequences.',13,'start','muted')
    return out+'</svg>',1000,650


def page_tables(lang):
    zh=lang=='zh';name=f'uvm-page-tables-{lang}'
    out=svg_start(name,1000,570,'One virtual address, separate translations',
        '具体状态：CPU 与 GPU 的不同页表均把 p 映射到同一个主机页 H；UVM 可将数据迁到显存并更新映射。' if zh else
        'Example state: separate CPU and GPU page tables both map p to host page H. UVM can migrate the data to VRAM and update mappings.')
    for x in (70,570):
        out+=f'<rect class="band" x="{x}" y="122" width="360" height="216" rx="5"/>'
    out+=node(365,20,270,56,['同一个 managed 地址 p' if zh else 'The same managed address p'],'um-guide',True)
    out+=path(name,'M500 76V103H250V137')+path(name,'M500 103H750V137')
    for x,title,key in [(70,'CPU','cpu-insert'),(570,'GPU','pte-make')]:
        out+=node(x+25,137,310,56,[title+' MMU / TLB'],key)
        out+=path(name,f'M{x+180} 193V244')
        out+=text(x+196,224,'TLB miss',13,'start','muted')
        out+=node(x+25,244,310,74,[title+(' 页表' if zh else ' page table'),'PTE: p → host page H'],key,True)
    out+=path(name,'M250 318V362H360V412')+path(name,'M750 318V362H360V412')
    out+=text(775,390,'经主机互联' if zh else 'Via host interconnect',13,'end','muted')
    out+=node(130,412,460,70,['Managed 页当前驻留主机 H' if zh else 'Managed page resident in host RAM H','当前状态：两端映射均有效' if zh else 'Both mappings valid in this example'],'um-guide',True)
    out+=node(740,412,220,70,['GPU 显存页 D' if zh else 'VRAM page D','迁移目标' if zh else 'Migration destination'],'resident-copy')
    out+=path(name,'M590 447H740','host',True)
    out+=text(665,430,'UVM copy',13,cls='host-text')
    out+=text(28,521,'若选择迁移到 D，UVM 维护相应映射；CPU 远程访问 D 取决于平台与策略。' if zh else
        'Migration to D updates mappings; CPU remote access to D depends on platform and policy.',14,'start')
    out+=text(28,551,'独立页表示意；ATS 可借用 CPU 页表翻译。映射并不总是同时有效。' if zh else
        'Separate-table example; ATS can use CPU page-table translations. Mappings need not coexist.',13,'start','muted')
    return out+'</svg>',1000,570


def sequence(lang,kind):
    zh=lang=='zh';name=f'uvm-{kind.replace("_","-")}-{lang}'
    if kind=='cpu_fault':
        actors=[('CPU thread','faulting process'),('Linux MM','VMA / CPU PTE'),('UVM','nvidia-uvm.ko'),('GPU work','PTE / TLB / copy')]
        xs=[135,375,615,855]
        rows=[
            (0,1,'读取 p：CPU page fault' if zh else 'Read p: CPU page fault','linux-fault','fault'),
            (1,2,'VMA → uvm_vm_fault()','cpu-fault','fault'),
            (2,2,'定位 managed block，检查权限' if zh else 'Find managed block; check access','cpu-dispatch','normal'),
            (2,2,'UVM 选择主机驻留：本例迁回 H' if zh else 'UVM selects host residency: move to H','cpu-residency','normal'),
            (2,3,'清除旧 GPU PTE / 失效 TLB' if zh else 'Clear old GPU PTE / invalidate TLB','gpu-clear','normal'),
            (2,3,'准备主机页；复制 D → H' if zh else 'Prepare host page; copy D → H','resident-copy','host'),
            (2,2,'uvm_tracker_wait(): 复制与更新完成' if zh else 'uvm_tracker_wait(): copies / updates','cpu-map-wait','host'),
            (2,1,'uvm_cpu_insert_page() → vm_insert_page()','cpu-insert','normal'),
            (1,1,'CPU PTE: p → H','linux-insert','normal'),
            (2,1,'返回 fault 处理结果' if zh else 'Return fault result','cpu-return','normal'),
            (1,0,'返回用户态，重试原访存' if zh else 'Return to user space; retry access','linux-fault','host'),
        ]
        scopes=[(0,0,10),(1,0,10),(2,1,9),(3,4,6)]
        desc='显存迁回主机的一条 CPU 缺页路径，包含 GPU 映射撤销、复制等待与 Linux CPU PTE 插入。' if zh else 'A CPU fault migrating VRAM to host: revoke GPU mapping, copy and wait, then insert a Linux CPU PTE.'
    else:
        actors=[('GPU / MMU','load + fault record'),('RM / IRQ','nvidia.ko'),('UVM worker','nvidia-uvm.ko'),('Linux MM','CPU page table'),('GPU work','copy / PTE / TLB')]
        xs=[110,305,500,695,890]
        rows=[
            (0,0,'load 缺页：写入 fault buffer' if zh else 'Load faults; write fault record','fault-batch','fault'),
            (0,1,'缺页中断通知' if zh else 'Fault interrupt notification','irq-top','fault'),
            (1,2,'调度 UVM bottom half' if zh else 'Queue UVM bottom half','irq-queue','fault'),
            (2,2,'读取故障批次，定位 VA block' if zh else 'Fetch fault batch; locate VA block','fault-batch','normal'),
            (2,2,'UVM 选择驻留位置：本例迁入 D' if zh else 'UVM selects residency: move to D here','gpu-residency','normal'),
            (2,3,'撤销 CPU PTE / 失效 CPU TLB' if zh else 'Revoke CPU PTE / invalidate CPU TLB','cpu-unmap','normal'),
            (2,4,'撤销其他旧映射；复制 H → D' if zh else 'Revoke other old maps; copy H → D','resident-copy','host'),
            (2,4,'GPU PTE: p → D；GPU TLB 维护' if zh else 'GPU PTE: p → D; GPU TLB maintenance','gpu-write','normal'),
            (2,0,'依赖前置 GPU 工作，提交 replay' if zh else 'Submit replay after required GPU work','fault-replay','host'),
            (0,0,'重新翻译 p，读取显存 D' if zh else 'Translate p again; read VRAM D','fault-replay','host'),
        ]
        scopes=[(0,0,9),(1,1,2),(2,2,8),(3,5,5),(4,6,7)]
        desc='主机迁入显存的一条 GPU 缺页路径；Linux 清除 CPU 映射，GPU 工作更新设备映射，replay 依赖前置工作。' if zh else 'A GPU fault migrating host data to VRAM: Linux revokes CPU mappings, GPU work updates device mappings, and replay waits on dependencies.'
    step=94;h=142+len(rows)*step
    out=svg_start(name,1000,h,'CPU fault: migration branch' if kind=='cpu_fault' else 'GPU fault: migration branch',desc)
    out+=text(28,28,'UVM 独立页表路径 · 选取迁移分支 · activation 表示处理范围' if zh else 'UVM separate-page-table path · selected migration branch · activations show processing scopes',13,'start','muted')
    for i,(_,_,_,_,color) in enumerate(rows):
        if color in ('host','fault'):
            out+=f'<rect class="{color}-band" x="20" y="{111+i*step}" width="960" height="{step-5}" rx="3"/>'
    actor_w=210 if len(actors)==4 else 178
    for i,(title,sub) in enumerate(actors):
        out+=f'<path class="lifeline" d="M{xs[i]} 99V{h-25}"/>'
        out+=node(xs[i]-actor_w/2,45,actor_w,54,[title,sub])
    for actor,first,last in scopes:
        top=151+first*step;bottom=182+last*step
        out+=f'<rect class="activation" x="{xs[actor]-6}" y="{top}" width="12" height="{bottom-top}" rx="1"/>'
    for i,(a,b,label,key,color) in enumerate(rows):
        y=161+i*step;left=min(xs[a],xs[b])+17
        if a==b:left=xs[a]+22
        label_bg=f'var(--uvm-{color}-tint)' if color in ('host','fault') else 'var(--cuda-paper)'
        out+=f'<a href="{LINKS[key]}" target="_blank" rel="noopener" style="--uvm-label-bg:{label_bg}">'
        out+=text(28,y-15,f'{i+1:02}',12,'start','muted')
        if a==b:
            out+=path(name,f'M{xs[a]+6} {y}h34v12h-34',color)
            out+=f'<rect class="activation" x="{xs[a]+1}" y="{y+5}" width="11" height="16"/>'
        else:
            start=xs[a]+(6 if b>a else -6);end=xs[b]+(-6 if b>a else 6)
            out+=path(name,f'M{start} {y}H{end}',color,dashed=(kind=='cpu_fault' and i>=9))
        out+=text(left,y-14,label,15,'start','message')
        source=LINKS[key].split('/')[-1].replace('#L',':').replace('-L','–')
        out+=text(left,y+29,source+' ↗',12,'start','source')
        out+='</a>'
    return out+'</svg>',1000,h


def pte(lang):
    zh=lang=='zh';name=f'uvm-pte-{lang}'
    out=svg_start(name,1000,640,'Hopper / Blackwell VER3 PTE',
        'VER3 的 64 位 PTE：Peer ID 63:61、地址 51:12、Kind 11:8、PCF 7:3、Aperture 2:1、Valid 0。Blackwell UVM 复用 Hopper 构造函数。' if zh else
        'A 64-bit VER3 PTE: Peer ID 63:61, address 51:12, Kind 11:8, PCF 7:3, Aperture 2:1, Valid 0. Blackwell UVM reuses the Hopper constructor.')
    out+=text(28,34,'Hopper / Blackwell · VER3 PTE',20,'start',weight=600)
    out+=text(28,59,'system / peer 地址布局；— 表示未展开字段；方框不按位宽比例绘制' if zh else 'System / peer address layout; — denotes omitted fields; boxes are not to scale',13,'start','muted')
    for x,w,bits,label in [(28,132,'63:61','Peer ID'),(160,108,'60:52','—'),(268,456,'51:12','Page address'),(724,248,'11:0','Kind / control')]:
        out+=f'<a href="{LINKS["pte"]}" target="_blank" rel="noopener"><rect class="field" x="{x}" y="85" width="{w}" height="72"/>'
        out+=text(x+w/2,108,bits,13,cls='muted')+text(x+w/2,136,label,16)+'</a>'
    out+=text(28,190,'PTE[11:0] · 格式与控制字段' if zh else 'PTE[11:0] · format and control fields',17,'start',weight=600)
    fields=[('11:8','Kind',180),('7:3','PCF',360),('2:1','Aperture',240),('0','Valid',164)]
    x=28
    for bits,label,w in fields:
        out+=f'<a href="{LINKS["pte"]}" target="_blank" rel="noopener"><rect class="field{" field-accent" if label in ("PCF","Aperture") else ""}" x="{x}" y="209" width="{w}" height="68"/>'
        out+=text(x+w/2,232,bits,13,cls='muted')+text(x+w/2,258,label,16,weight=600)+'</a>'; x+=w
    out+=text(28,305,'PCF 编码示例 · Valid = 1 · regular' if zh else 'PCF examples · Valid = 1 · regular',16,'start',weight=600)
    for i,(value,access,cache) in enumerate([('0x00','RW · atomic','cached · access counters ON'),('0x0C','RO · no atomic','cached · access counters ON'),('0x10','RW · atomic','cached · access counters OFF')]):
        x=28+i*320
        out+=f'<a href="{LINKS["pte"]}" target="_blank" rel="noopener"><rect class="field" x="{x}" y="320" width="304" height="82" rx="3"/>'
        out+=text(x+152,343,value,18,weight=600)+text(x+152,366,access,14)+text(x+152,388,cache,12,cls='muted')+'</a>'
    out+=text(28,435,'Aperture · 当前映射的目标类别' if zh else 'Aperture · target of the current mapping',16,'start',weight=600)
    names=[('00','本地显存' if zh else 'Local VRAM'),('01','Peer aperture'),('10','Coherent system'),('11','Non-coherent system')]
    for i,(bits,label) in enumerate(names):
        x=28+i*242
        out+=f'<a href="{LINKS["pte"]}" target="_blank" rel="noopener"><rect class="field field-accent" x="{x}" y="450" width="218" height="74" rx="3"/>'
        out+=text(x+109,476,bits,19,weight=600)+text(x+109,504,label,14)+'</a>'
    out+=text(28,558,'UVM 构造：system / peer 地址 [51:12]；local VRAM 地址 [39:12]' if zh else 'UVM constructor: system / peer address [51:12]; local VRAM address [39:12]',14,'start')
    out+=text(28,587,'PCF 同时编码权限、缓存与访问计数器属性；Valid = 0 时须使用无效项解释。' if zh else 'PCF encodes permissions, caching and access-counter policy; Valid = 0 changes its meaning.',13,'start','muted')
    out+=text(28,618,'Managed 身份与 host 页锁定状态保存在软件记录中' if zh else 'Managed identity and host page pinning are tracked in software',15,'start',weight=600)
    return out+'</svg>',1000,640


TITLES={
    'architecture':('UVM 软件与硬件分层','UVM software and hardware layers'),
    'page_tables':('Managed 页：主机驻留与 GPU 远程映射','Managed page: host residency and GPU remote mapping'),
    'cpu_fault':('CPU 缺页：选择迁回主机的分支','CPU fault: branch choosing migration to host'),
    'gpu_fault':('GPU 缺页：选择迁入显存的分支','GPU fault: branch choosing migration to VRAM'),
    'pte':('Hopper／Blackwell PTE','Hopper / Blackwell PTE'),
}


def figure(kind,lang):
    zh=lang=='zh';title=TITLES[kind][0 if zh else 1]
    if kind in ('cpu_fault','gpu_fault'): svg,w,h=sequence(lang,kind)
    else: svg,w,h=globals()[kind](lang)
    fit,actual=('适宽','原始尺寸') if zh else ('Fit width','Actual size')
    caption=('点击图中消息或字段打开源码。时序表示逻辑顺序，条形长度不代表实测时间。' if kind in ('cpu_fault','gpu_fault') else '点击节点或字段查看源码与硬件格式。') if zh else ('Messages link to source. Sequence and bar lengths describe logical order, not measured time.' if kind in ('cpu_fault','gpu_fault') else 'Nodes and fields link to source or hardware documentation.')
    return f'<figure class="cuda-figure" data-size="fit" style="--diagram-width:{w}px;--diagram-ratio:{w/h:.8f}"><div class="diagram-toolbar"><strong>{title}</strong><button type="button" data-size-toggle data-fit-label="{fit}" data-actual-label="{actual}" aria-pressed="false">{actual}</button></div><div class="diagram-viewport" tabindex="0" role="region" aria-label="{title}">{svg}</div><figcaption>{caption}</figcaption></figure>'


def expand(lang):
    body=(ROOT/f'scripts/content/uvm-managed-memory.{lang}.html').read_text()
    body=re.sub(r'\[\[([\w-]+)\|([^\]]+)\]\]',lambda m:link(m[1],m[2]),body)
    body=re.sub(r'\{\{code:([\w-]+)\}\}',lambda m:'<pre><code>'+escape(textwrap.dedent(CODE[m[1]]).strip())+'</code></pre>',body)
    for kind in TITLES:body=body.replace('{{'+kind+'}}',figure(kind,lang))
    assert not re.search(r'\{\{[\w:-]+\}\}|\[\[[\w-]+\|',body)
    return body


def main():
    meta=dict(title='UVM managed memory 访存路径',title_en='UVM managed memory access paths',slug='cuda-uvm-managed-memory',date='2026-11-10',tags='CUDA, UVM, Unified Memory, MMU, Linux',tags_en='CUDA, UVM, Unified Memory, MMU, Linux',reading='15 分钟',reading_en='15 min',summary='UVM 为同一 managed 指针维护 CPU 和 GPU 的映射。页面驻留位置可随访问需求变化；缺页时，驱动选择补建映射、调整权限或迁移页面，再恢复访问。',summary_en='UVM maintains CPU and GPU mappings for the same managed pointer. When an access faults, the driver can add a mapping, adjust permissions, or migrate the page before resuming execution.',series='inside-cuda',series_title='Inside CUDA',series_title_en='Inside CUDA',series_order='3')
    metadata='\n'.join(f'<meta name="post:{k}" content="{escape(v,quote=True)}">' for k,v in meta.items())
    html=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{meta['title']}</title>
{metadata}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3"><link rel="stylesheet" href="{SHARED}style.css?v=gpu-stack-5"><link rel="stylesheet" href="{BASE}style.css?v=3">
<script src="../lang-toggle.js?v=post-toc-3" defer></script><script src="{SHARED}page.js?v=component-info-4" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>{render_series_nav(meta, ROOT / 'posts')}</aside><main class="content cuda-article uvm-article"><div class="lang-zh">{expand('zh')}</div><div class="lang-en">{expand('en')}</div></main></div></body></html>'''
    target=ROOT/'posts/cuda-uvm-managed-memory.html'
    target.write_text(html)
    print('Wrote',target)


if __name__=='__main__':main()
