#!/usr/bin/env python3
"""Build Inside CUDA #1; evidence is a curated, real H100 capture.

Design: editorial technical diagram, variance 3 / motion 1 / density 7.
Use the site's layout and theme; no additional framework or font dependency.
"""
from html import escape
from pathlib import Path
from post_series import render_series_nav
import json
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/inside-cuda/linux-stack'
BASE = '../assets/inside-cuda/linux-stack/'
SHA = '6f3be8c9c3fb4ed6ffc607a0d32d31ce4db7fba5'
SOURCE = f'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/{SHA}/'
DOC = 'https://docs.nvidia.com/cuda/archive/12.4.1/'
LINKS = {
    'repo': SOURCE + 'README.md',
    'runtime': DOC + 'cuda-runtime-api/driver-vs-runtime-api.html',
    'nvcc': DOC + 'cuda-compiler-driver-nvcc/index.html#cudart-none-shared-static-cudart',
    'cuda': DOC + 'cuda-driver-api/index.html',
    'components': 'https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/installedcomponents.html',
    'gsp-doc': 'https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/gsp.html',
    'nvml': 'https://docs.nvidia.com/deploy/nvml-api/',
    'caps': 'https://docs.nvidia.com/datacenter/tesla/mig-user-guide/device-nodes-and-capabilities.html',
    'fops': SOURCE + 'kernel-open/nvidia/nv.c#L259-L270',
    'uvm-fops': SOURCE + 'kernel-open/nvidia-uvm/uvm.c#L1074-L1086',
    'chrdev-register': SOURCE + 'kernel-open/nvidia/nv.c#L823-L851',
    'chrdev-init': SOURCE + 'kernel-open/nvidia/nv.c#L1053-L1071',
    'uvm-chrdev': SOURCE + 'kernel-open/nvidia-uvm/uvm.c#L1132-L1155',
    'device-creation': 'https://download.nvidia.com/XFree86/Linux-x86_64/580.65.06/README/faq.html',
    'linux-fops': 'https://github.com/torvalds/linux/blob/v6.8/include/linux/fs.h#L1850-L1868',
    'open': SOURCE + 'kernel-open/nvidia/nv.c#L2007-L2045',
    'ioctl': SOURCE + 'kernel-open/nvidia/nv.c#L2627-L2715',
    'mmap': SOURCE + 'kernel-open/nvidia/nv-mmap.c#L772-L818',
    'uvm': SOURCE + 'kernel-open/nvidia-uvm/uvm.c#L997-L1087',
    'uvm-init': SOURCE + 'kernel-open/nvidia-uvm/uvm_linux_ioctl.h#L32-L44',
    'uvm-map': SOURCE + 'kernel-open/nvidia-uvm/uvm_ioctl.h#L365-L378',
    'uvm-range': SOURCE + 'kernel-open/nvidia-uvm/uvm_ioctl.h#L842-L852',
    'uvm-push': SOURCE + 'kernel-open/nvidia-uvm/uvm_push.c',
    'uvm-fault': SOURCE + 'kernel-open/nvidia-uvm/uvm_gpu_replayable_faults.c',
    'rm-numbers': SOURCE + 'src/nvidia/arch/nvalloc/unix/include/nv_escape.h#L31-L45',
    'rm-control': SOURCE + 'src/nvidia/arch/nvalloc/unix/src/escape.c#L796-L855',
    'rm-escape': SOURCE + 'src/nvidia/arch/nvalloc/unix/src/escape.c',
    'gsp': SOURCE + 'src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c',
    'modeset': SOURCE + 'kernel-open/nvidia-modeset/nvidia-modeset-linux.c',
    'drm': SOURCE + 'kernel-open/nvidia-drm/nvidia-drm-drv.c',
    'drm-nodes': 'https://docs.kernel.org/gpu/drm-uapi.html#primary-nodes-drm-master-and-authentication',
    'modeset-fops': SOURCE + 'kernel-open/nvidia-modeset/nvidia-modeset-linux.c#L2090-L2116',
    'vfs': 'https://docs.kernel.org/filesystems/vfs.html',
    'open-man': 'https://man7.org/linux/man-pages/man2/open.2.html',
    'ioctl-man': 'https://man7.org/linux/man-pages/man2/ioctl.2.html',
    'mmap-man': 'https://man7.org/linux/man-pages/man2/mmap.2.html',
    'strace': 'https://strace.io/',
    'ltrace': 'https://man7.org/linux/man-pages/man1/ltrace.1.html',
    'cupti': 'https://docs.nvidia.com/cupti/main/main.html',
    'nccl-doc': 'https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/',
    'cublas-doc': 'https://docs.nvidia.com/cuda/cublas/',
    'peer-post': 'gpu-peer-to-peer-memory.html',
}
EVIDENCE = json.loads((ASSETS / 'evidence.json').read_text())
INSPECTION = json.loads((ASSETS / 'inspection.json').read_text())

# Library/module descriptions are read from the article tables at interaction
# time. Only the additional diagram nodes need their own short descriptions.
TABLE_COMPONENTS = {
    'cudart': '<code>libcudart.so</code>', 'cuda': '<code>libcuda.so.1</code>',
    'nvml': '<code>libnvidia-ml.so</code>', 'libraries': 'NCCL / cuBLAS',
    'core': '<code>nvidia.ko</code>', 'uvm': '<code>nvidia-uvm.ko</code>',
    'modeset': '<code>nvidia-modeset.ko</code>', 'drm': '<code>nvidia-drm.ko</code>',
}
COMPONENTS = {
    'app': dict(section='execution-spaces', layer='user',
        zh='运行在 CPU 用户态的 CUDA 应用或计算框架，组织数据处理与 GPU 工作，可以调用 Runtime API、Driver API，或 NCCL、cuBLAS 等上层库。',
        en='A CUDA application or framework runs in CPU user space and organizes data processing and GPU work through the Runtime API, Driver API, or libraries such as NCCL and cuBLAS.',
        links=[('runtime','CUDA Runtime / Driver API')]),
    'libraries': dict(section='user-libraries', layer='user', row_description=2, row_details=1,
        links=[('nccl-doc','NCCL'),('cublas-doc','cuBLAS')]),
    'cudart': dict(section='user-libraries', layer='user', row_description=2, row_details=1,
        links=[('runtime','CUDA Runtime API'),('nvcc','nvcc · libcudart')]),
    'cuda': dict(section='user-libraries', layer='user', row_description=2, row_details=1,
        links=[('cuda','CUDA Driver API')]),
    'smi': dict(section='user-libraries', layer='user',
        zh='GPU 监控与管理的命令行程序。它通过 NVML 查询型号、驱动版本、显存占用和功耗等状态。',
        en='A command-line tool for GPU monitoring and management. It uses NVML to query information such as the GPU model, driver version, memory usage and power.',
        links=[('nvml','NVML API')]),
    'nvml': dict(section='user-libraries', layer='user', row_description=2, row_details=1,
        links=[('nvml','NVML API')]),
    'display': dict(section='kernel-modules', layer='user',
        zh='桌面合成器和 Xorg 等图形用户态组件，经显示驱动接口使用 GPU 的显示功能；图中展示与 Linux DRM/KMS 的连接。',
        en='Graphics components such as a compositor or Xorg use GPU display services through display-driver interfaces. The diagram shows their connection to Linux DRM/KMS.',
        links=[('drm','nvidia-drm-drv.c'),('components','NVIDIA driver components')]),
    'uvm': dict(section='kernel-modules', layer='kernel', row_description=1,
        links=[('uvm','uvm.c'),('uvm-fault','uvm_gpu_replayable_faults.c'),('uvm-push','uvm_push.c')]),
    'core': dict(section='kernel-modules', layer='kernel', row_description=1,
        links=[('fops','nv.c'),('rm-escape','escape.c')]),
    'drm': dict(section='kernel-modules', layer='kernel', row_description=1,
        links=[('drm','nvidia-drm-drv.c')]),
    'modeset': dict(section='kernel-modules', layer='kernel', row_description=1,
        links=[('modeset','nvidia-modeset-linux.c')]),
    'gsp': dict(section='hardware-firmware', layer='gpu',
        zh='GPU 上的管理处理器，运行 GSP-RM 固件，承接部分设备初始化与管理工作，并通过 RPC 等机制与主机 Kernel RM 协作。CUDA 计算 kernel 由 SM 执行。',
        en='An on-GPU management processor running GSP-RM firmware. It handles part of device initialization and management, cooperating with host Kernel RM through mechanisms such as RPC. CUDA compute kernels execute on SMs.',
        links=[('gsp-doc','GSP'),('gsp','kernel_gsp.c')]),
    'engines': dict(section='hardware-firmware', layer='gpu',
        zh='GPU 的执行与地址转换硬件：SM 执行计算 kernel，MMU 转换地址，Copy Engine 执行适用的搬运任务，内存控制器连接显存。',
        en='GPU execution and address-translation hardware: SMs execute compute kernels, the MMU translates addresses, Copy Engines perform applicable transfers, and memory controllers connect VRAM.',
        links=[('cuda','CUDA Driver API'),('uvm-push','UVM GPU work · uvm_push.c')]),
    'vram': dict(section='hardware-firmware', layer='gpu',
        zh='GPU 板卡上的显存，通常采用 HBM 或 GDDR，存放设备程序使用的数据。驱动与 GPU 的地址转换硬件共同建立和使用相关映射。',
        en='Memory on the GPU board, typically HBM or GDDR, holding data used by device programs. The driver and GPU address-translation hardware establish and use the relevant mappings.',
        links=[('cuda','CUDA Driver API')]),
    'link': dict(section='hardware-firmware', layer='gpu',
        zh='GPU 与其他设备交换数据的互联接口。GPU P2P 可经 NVLink 或 PCIe；具体路径取决于拓扑与平台支持。',
        en='Interconnect interfaces for exchanging data with other devices. GPU P2P can use NVLink or PCIe, depending on topology and platform support.',
        links=[('peer-post','GPU P2P')]),
    'peer-gpu': dict(section='hardware-firmware', layer='device',
        zh='参与 peer 访问的其他 GPU，可通过直连链路或 NVSwitch 连接。能否访问以及采用哪条路径，由设备能力、映射权限和实际拓扑共同决定。',
        en='Other GPUs participating in peer access, connected directly or through NVSwitch. Device capabilities, mapping permissions and topology determine which accesses and paths are available.',
        links=[('peer-post','GPU P2P')]),
    'dev-uvm': dict(section='device-files', layer='interface',
        zh='/dev/nvidia-uvm 是 UVM 的字符设备入口。libcuda 打开它取得 fd，再通过 ioctl 配置地址空间，通过 mmap 建立相应映射。Linux 将这些操作分派到 nvidia-uvm.ko 的 uvm_fops。',
        en='/dev/nvidia-uvm is the UVM character-device interface. libcuda opens it to obtain an fd, then uses ioctl to configure address spaces and mmap to establish mappings. Linux dispatches these operations through uvm_fops in nvidia-uvm.ko.',
        links=[('uvm-fops','uvm_fops'),('uvm-chrdev','UVM character-device registration')]),
    'dev-core': dict(section='device-files', layer='interface',
        zh='/dev/nvidiactl 提供核心控制接口，/dev/nvidiaN 提供各 GPU 的设备接口，N 代表设备节点编号。libcuda 和 NVML 打开节点取得 fd；后续 ioctl、mmap 等操作由 nvidia.ko 的 nvidia_fops 处理。节点编号与应用中的 CUDA ordinal 可以不同。',
        en='/dev/nvidiactl provides core control operations; /dev/nvidiaN provides per-GPU interfaces, where N is the device-node number. libcuda and NVML open these nodes to obtain fds. nvidia_fops in nvidia.ko handles subsequent operations such as ioctl and mmap. Device-node numbers can differ from CUDA ordinals.',
        links=[('fops','nvidia_fops'),('chrdev-init','Core character-device registration')]),
    'dev-modeset': dict(section='device-files', layer='interface',
        zh='/dev/nvidia-modeset 是 NVIDIA 图形用户态组件访问显示模式管理功能的字符设备。请求经 nvkms_fops 分派到 nvidia-modeset.ko；DRM/KMS 路径则通过 nvidia-drm.ko 在内核中调用 modeset 服务。',
        en='/dev/nvidia-modeset is the character device used by NVIDIA graphics components for display-mode management. nvkms_fops dispatches requests to nvidia-modeset.ko. The DRM/KMS path calls modeset services from nvidia-drm.ko within the kernel.',
        links=[('modeset-fops','nvkms_fops'),('components','NVIDIA display components')]),
    'dev-drm': dict(section='device-files', layer='interface',
        zh='/dev/dri/cardN 是 DRM primary node，显示程序通过它提交 KMS 等 ioctl，请求进入 nvidia-drm.ko。可用的 /dev/dri/renderD* 节点用于渲染接口；KMS 显示控制使用 cardN。',
        en='/dev/dri/cardN is a DRM primary node. Display software submits KMS and other ioctls through it to nvidia-drm.ko. Available /dev/dri/renderD* nodes expose rendering interfaces; KMS display control uses cardN.',
        links=[('drm-nodes','DRM device nodes'),('drm','nvidia-drm-drv.c')]),
}


def link(key, title):
    return f'<a href="{escape(LINKS[key], quote=True)}" target="_blank" rel="noopener">{title}</a>'


def code(text, trace=False):
    css = ' class="trace-block"' if trace else ''
    return f'<pre{css}><code>{escape(textwrap.dedent(text).strip())}</code></pre>'


def text(x, y, value, size=16, anchor='middle', cls='', weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" class="{cls}" font-weight="{weight}">{escape(value)}</text>'


def start_svg(name, height, title, description, interactive=False, width=1440):
    role = 'group' if interactive else 'img'
    return f'''<svg class="cuda-diagram" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="{role}" aria-labelledby="{name}-title {name}-desc">
<title id="{name}-title">{escape(title)}</title><desc id="{name}-desc">{escape(description)}</desc>
<defs><marker id="{name}-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path class="arrow-head" d="M0 0L10 5L0 10Z"/></marker>
<marker id="{name}-data" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path class="arrow-data" d="M0 0L10 5L0 10Z"/></marker></defs>'''


def node(x, y, w, h, title, subtitle, paths, key=None, core=False, component=None, panel=None):
    attrs = f'class="node{" core" if core else ""}{" device-node" if component and component.startswith("dev-") else ""}" data-paths="{paths}"'
    tag = 'a' if key else 'g'
    href = f' href="{LINKS[key]}" target="_blank" rel="noopener"' if key else ''
    if component:
        tag, href = 'g', ''
        attrs += f' role="button" tabindex="0" data-component="{component}" data-component-title="{escape(title, quote=True)}" aria-label="{escape(title, quote=True)}" aria-haspopup="dialog" aria-expanded="false" aria-controls="{panel}"'
    out = f'<{tag} {attrs}{href}><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/>'
    size = 14 if h <= 44 else (16 if w < 230 and len(title) > 15 else 17)
    compact = h <= 54
    out += text(x + w / 2, y + (17 if h <= 44 else 26 if compact else 28), title, size, weight=600)
    out += text(x + w / 2, y + (34 if h <= 44 else 45 if compact else 52), subtitle, 11 if h <= 44 else 13 if compact else 14, cls='muted')
    return out + f'</{tag}>'


def edge(name, d, paths, both=False, data=False, label=None, key=None):
    marker = name + ('-data' if data else '-arrow')
    start = f' marker-start="url(#{marker})"' if both else ''
    out = f'<g data-paths="{paths}"><path class="edge{" data-edge" if data else ""}" d="{d}" marker-end="url(#{marker})"{start}/>'
    if label:
        x, y, words, width = label
        out += '<g class="edge-label">'
        out += f'<rect x="{x-width/2}" y="{y-17}" width="{width}" height="23" rx="3"/>'
        out += text(x, y, words, 13) + '</g>'
    out += '</g>'
    return f'<a href="{LINKS[key]}" target="_blank" rel="noopener">{out}</a>' if key else out


def architecture(lang):
    zh = lang == 'zh'
    name = f'cuda-stack-{lang}'
    out = start_svg(name, 850, 'CUDA / Linux / GPU',
        '用户态库经字符设备文件访问 Linux 驱动，驱动建立 GPU 资源。绿色虚线表示 GPU P2P 数据路径。' if zh else
        'User libraries access Linux drivers through character-device files; drivers establish GPU resources. Teal dashed lines show GPU P2P data paths.', interactive=True, width=1180)
    for y, h, title in [(16, 262, 'CPU 用户态 · 每个应用进程' if zh else 'CPU USER SPACE · application processes'),
                         (386, 214, 'CPU 内核态 · Linux' if zh else 'CPU KERNEL · Linux')]:
        out += f'<rect class="band" x="16" y="{y}" width="1148" height="{h}" rx="6"/>'
        out += text(300 if y == 386 else 50, y+28, title, 17, 'start', weight=600)
    out += '<rect class="device-band" x="16" y="290" width="1148" height="82" rx="6"/>'
    out += text(40, 307, '设备文件' if zh else 'Device files', 13, 'start', weight=600)
    out += '<rect class="board" x="16" y="640" width="910" height="172" rx="6"/>'
    out += text(50, 662, 'GPU 板卡' if zh else 'GPU BOARD', 17, 'start', weight=600)
    # Route edges first so node borders remain continuous and legible.
    for d, paths, both, data, label, key in [
        ('M190 116V138', 'cuda', False, False, None, None),
        ('M460 116V138', 'cuda', False, False, None, None),
        ('M70 89H44V245H70', 'cuda', False, False, None, None),
        ('M190 192V218', 'cuda', False, False, None, None),
        ('M460 192V218', 'cuda', False, False, None, 'runtime'),
        ('M740 116V218', 'monitor', False, False, None, None),
        ('M202 272V318', 'cuda', False, False, None, 'uvm'),
        ('M510 272V318', 'cuda', False, False, None, 'fops'),
        ('M740 272V284H650V318', 'monitor', False, False, None, 'fops'),
        ('M990 192V284H850V318', 'graphics', False, False, None, 'modeset-fops'),
        ('M1055 192V318', 'graphics', False, False, None, 'drm-nodes'),
        ('M202 360V422', 'cuda', False, False, None, 'uvm-fops'),
        ('M545 360V380H600V520H580', 'cuda monitor', False, False, None, 'fops'),
        ('M850 360V494H930V510', 'graphics', False, False, None, 'modeset-fops'),
        ('M1055 360V422', 'graphics', False, False, None, 'drm'),
        ('M325 476V510', 'cuda', True, False, (400, 499, 'RM services', 105), None),
        ('M1010 476V510', 'graphics', False, False, None, None),
        ('M900 537H580', 'graphics', False, False, (740, 527, 'display services', 130), None),
        ('M195 564V670', 'cuda monitor graphics', True, False, (195, 626, 'GSP-RM RPC', 120), 'gsp'),
        ('M500 564V670', 'cuda monitor graphics', False, False, (500, 626, 'host MMIO', 105), None),
        ('M580 449H620V652H655V670', 'cuda', False, False, (758, 626, 'UVM GPU work: copy / page tables', 270), 'uvm-push'),
        ('M320 697H390', 'cuda monitor graphics', False, False, None, None),
        ('M480 724V746', 'cuda', True, False, None, None),
        ('M750 724V746', 'cuda', True, False, None, None),
        ('M890 773H955', 'cuda', True, True, (923, 763, 'P2P', 38), None),
    ]:
        # References live in the component descriptions; the overview itself
        # only opens local explanations, never an external page on first click.
        out += edge(name, d, paths, both, data, label)
    nodes = [
        (70,62,510,54,'CUDA application / framework', '直接调用 Driver API，或经 Runtime / libraries' if zh else 'Driver API, Runtime API, or higher-level libraries','cuda', 'runtime',False),
        (70,138,240,54,'NCCL / cuBLAS', '通信与计算库' if zh else 'Communication / compute','cuda','runtime',False),
        (340,138,240,54,'libcudart.so', 'CUDA Runtime API','cuda','runtime',False),
        (70,218,510,54,'libcuda.so.1', 'CUDA Driver API · 用户态驱动' if zh else 'CUDA Driver API · user-mode driver','cuda','cuda',True),
        (640,62,200,54,'nvidia-smi', '监控与管理' if zh else 'Monitoring / control','monitor','nvml',False),
        (640,218,200,54,'libnvidia-ml.so', 'NVML','monitor','nvml',False),
        (900,138,220,54,'Compositor / Xorg', '图形用户态组件' if zh else 'Graphics user space','graphics','drm',False),
        (70,422,510,54,'nvidia-uvm.ko', 'UVM · VA spaces / faults / migration','cuda','uvm',True),
        (70,510,510,54,'nvidia.ko', 'Kernel RM · GPU resources / memory / mappings','cuda monitor graphics','fops',True),
        (900,422,220,54,'nvidia-drm.ko', 'Linux DRM / KMS','graphics','drm',False),
        (900,510,220,54,'nvidia-modeset.ko', '显示模式与引擎' if zh else 'Display modes / engines','graphics','modeset',False),
        (70,670,250,54,'GSP processor', 'GSP-RM firmware','cuda monitor graphics','gsp-doc',False),
        (390,670,500,54,'GPU engines / MMU', 'SM · Copy Engine · memory / display engines','cuda monitor graphics','cuda',False),
        (390,746,180,54,'VRAM', 'HBM / GDDR','cuda',None,False),
        (610,746,280,54,'NVLink / PCIe interfaces', 'GPU P2P 数据通路' if zh else 'GPU P2P data paths','cuda','peer-post',False),
        (955,746,200,54,'Other GPUs', 'direct / NVSwitch','cuda',None,False),
        (70,318,265,42,'/dev/nvidia-uvm', 'open · ioctl · mmap','cuda',None,False),
        (355,318,380,42,'/dev/nvidiactl · /dev/nvidiaN', 'open · ioctl · mmap','cuda monitor',None,False),
        (755,318,190,42,'/dev/nvidia-modeset', 'open · ioctl · mmap','graphics',None,False),
        (965,318,180,42,'/dev/dri/cardN', 'open · DRM / KMS ioctl','graphics',None,False),
    ]
    assert len(nodes) == len(COMPONENTS)
    for component, args in zip(COMPONENTS, nodes):
        out += node(*args, component=component, panel=f'cuda-component-{lang}')
    out += text(40, 838, '实线：调用、管理或配置依赖    绿色虚线：设备间数据路径    点击模块查看简介与链接' if zh else
        'Solid: calls / management    Teal dashed: GPU P2P data    Click a module for its description and links', 15, 'start', 'muted')
    return out + '</svg>'


def sequence(lang):
    zh = lang == 'zh'
    name = f'cuda-calls-{lang}'
    out = start_svg(name, 670, 'Linux device interface dispatch',
        'open、ioctl、mmap 经 Linux 分派到驱动回调；下方示意已建立提交资源后的 GPU 工作。条形表示逻辑调用范围。' if zh else
        'Linux dispatches open, ioctl and mmap to driver callbacks. Bars show logical call scopes, not measured durations.')
    for x, title, subtitle, key in [(170,'Application / libcuda','CPU user space','cuda'),(550,'Linux VFS / mm','CPU kernel space','vfs'),(970,'NVIDIA callbacks','nvidia.ko / nvidia-uvm.ko','fops'),(1280,'GPU','command processing','cuda')]:
        out += node(x-125,16,250,54,title,subtitle,'',key)
    for y,h,label in [(90,115,'openat'),(215,155,'ioctl'),(380,115,'mmap'),(505,127,'GPU work')]:
        out += f'<rect class="band" x="26" y="{y}" width="1388" height="{h}" rx="4"/>'
        out += text(42,y+24,label,15,'start',weight=600)
    # Lifelines stay visible over phase backgrounds; activation bars over lifelines.
    for x in [170,550,970,1280]:
        out += f'<path class="lifeline" d="M{x} 70V640"/>'
    for x,y,h in [(170,112,85),(550,112,83),(970,152,43),(170,237,120),(550,237,120),(970,277,80),(170,402,85),(550,402,83),(970,442,43),(170,527,88),(1280,527,88)]:
        out += f'<rect class="activation" x="{x-7}" y="{y}" width="14" height="{h}" rx="2"/>'
    messages = [
        (177,543,120,'openat("/dev/nvidiactl", O_RDWR)','open-man',False),
        (557,963,160,'file_operations.open → nvidia_open','open',False),
        (963,177,195,'file descriptor → process fd table','vfs',False),
        (177,543,245,'ioctl(fd, request, user_args)','ioctl-man',False),
        (557,963,285,'unlocked_ioctl → nvidia_ioctl / uvm_ioctl','ioctl',False),
        (963,177,355,'syscall result + driver status in payload','rm-control',False),
        (177,543,410,'mmap(..., MAP_SHARED, fd, offset)','mmap-man',False),
        (557,963,450,'file_operations.mmap → driver VMA setup','mmap',False),
        (963,177,485,'CPU virtual address for an allowed mapping','mmap',False),
        (177,1273,535,'Work submission through resources established during initialization','cuda',True),
        (1273,177,610,'Completion observation / synchronization','cuda',True),
    ]
    for x1,x2,y,label,key,data in messages:
        out += edge(name,f'M{x1} {y}H{x2}','',data=data)
        tx = min(x1,x2) + 12
        out += f'<a href="{LINKS[key]}" target="_blank" rel="noopener">'
        out += text(tx,y-10,label,15,'start',weight=500) + '</a>'
    out += text(992,309,'validate + copy arguments',13,'start','muted')
    out += text(992,327,'RM / UVM command dispatch',13,'start','muted')
    out += text(189,572,'该阶段可能无需再次进入内核；具体提交机制不能仅由 strace 确定。' if zh else
        'This phase may need no new syscall; strace alone does not identify the submission mechanism.',14,'start','muted')
    out += text(42,658,'源码路径示意，非实测函数栈。activation bar 表示逻辑范围，不表示耗时。' if zh else
        'Source-level schematic, not a captured call stack. Activation bars represent scopes, not durations.',14,'start','muted')
    return out + '</svg>'


def component_panel(lang):
    zh = lang == 'zh'
    sections = {
        'execution-spaces': '1.1 执行空间' if zh else '1.1 Execution spaces',
        'user-libraries': '1.2 用户态库' if zh else '1.2 User-space libraries',
        'kernel-modules': '1.3 Linux 模块' if zh else '1.3 Linux modules',
        'hardware-firmware': '1.4 固件与硬件' if zh else '1.4 Firmware and hardware',
        'device-files': '2.1 设备文件' if zh else '2.1 Device files',
    }
    layers = dict(user='CPU 用户态' if zh else 'CPU user space',
                  kernel='CPU 内核态' if zh else 'CPU kernel space',
                  gpu='GPU 板卡' if zh else 'GPU board', device='互联设备' if zh else 'Peer device',
                  interface='Linux 字符设备接口' if zh else 'Linux character-device interface')
    catalog = {}
    for component, data in COMPONENTS.items():
        catalog[component] = {
            'layer': layers[data['layer']], 'description': data.get(lang, ''),
            'section': '#' + data['section'] + ('' if zh else '-en'),
            'section_label': sections[data['section']],
            'links': [{'url': LINKS[key], 'label': label} for key, label in data['links']],
        }
        for field in ('row_description', 'row_details'):
            if field in data:
                catalog[component][field] = data[field]
    encoded = json.dumps(catalog, ensure_ascii=False).replace('<', '\\u003c')
    panel = f'cuda-component-{lang}'
    return f'''<script type="application/json" data-component-catalog>{encoded}</script>
<div id="{panel}" class="component-popover" popover="auto" role="dialog" aria-modal="false" aria-labelledby="{panel}-title" aria-describedby="{panel}-body" hidden>
<div class="component-layer" data-component-layer></div>
<div class="component-heading"><div id="{panel}-title" class="component-title" data-component-title></div><button type="button" data-component-close>{'关闭' if zh else 'Close'}</button></div>
<div id="{panel}-body" class="component-description" data-component-description></div>
<div class="component-meta" data-component-meta hidden><span>{'来源与接口' if zh else 'Distribution / interface'}</span><div data-component-meta-value></div></div>
<div class="component-references"><span>{'源码 / 文档' if zh else 'Source / documentation'}</span><div data-component-links></div></div>
<a class="component-section" data-component-section>{'文中说明' if zh else 'In this article'}: <span></span></a>
</div>'''


def figure(lang, kind):
    zh = lang == 'zh'
    title = ('CUDA 软件与硬件层级' if zh else 'CUDA software and hardware layers') if kind == 'architecture' else ('Linux 设备接口分派' if zh else 'Linux device interface dispatch')
    focus = ''
    if kind == 'architecture':
        options = [('all','全部' if zh else 'All'),('cuda','CUDA'),('monitor','监控' if zh else 'Monitoring'),('graphics','显示' if zh else 'Display')]
        focus = '<label>' + ('路径' if zh else 'Path') + '<select data-path-focus>'
        focus += ''.join(f'<option value="{value}">{label}</option>' for value,label in options) + '</select></label>'
    fit, actual = ('适应窗口','原始尺寸') if zh else ('Fit window','Actual size')
    width = 1180 if kind == 'architecture' else 1440
    ratio = width / (850 if kind == 'architecture' else 670)
    caption = {
        ('zh','architecture'): '设备文件一行标出用户态访问驱动的入口；打开后，进程通过 fd 发出 ioctl 等请求。N 表示设备节点编号。绿色虚线表示 GPU 间的 P2P 数据通路。',
        ('en','architecture'): 'The device-file row identifies user-space entry points into the drivers. After opening a node, the process issues requests such as ioctl through its fd. N denotes a device-node number. Teal dashed lines show GPU P2P data paths.',
        ('zh','sequence'): '上半部分对应公开源码中的 Linux 回调；最后一组说明已建立映射后的提交路径。实测日志在下文单独给出。',
        ('en','sequence'): 'The first three groups map to Linux callbacks in public source. The last group illustrates submission after resource setup. Measured logs appear separately below.',
    }[lang,kind]
    return f'''<figure class="cuda-figure" data-size="fit" data-layout="{kind}" style="--diagram-ratio:{ratio:.10f};--diagram-width:{width}px"><div class="diagram-toolbar"><strong>{title}</strong>{focus}
<button type="button" data-size-toggle data-fit-label="{fit}" data-actual-label="{actual}" aria-pressed="false">{actual}</button></div>
<div class="diagram-viewport" tabindex="0" role="region" aria-label="{title}">{architecture(lang) if kind == 'architecture' else sequence(lang)}</div><figcaption>{caption}</figcaption>{component_panel(lang) if kind == 'architecture' else ''}</figure>'''


COMMANDS = {
    'build': '''
        # Run in the directory containing the three downloaded files.
        # CUDA 12.4 + H100; use your GPU's supported target if different.
        nvcc -std=c++17 -O0 -lineinfo -arch=sm_90 --cudart shared \\
          hello.cu -o hello
        ldd ./hello
        ./hello
        # Hello from CUDA: 42 (expected 42)
    ''',
    'trace': '''
        # Separate runs: API-call capture and full syscall capture
        strace -f -ttt -T -yy -s 160 -o syscalls.txt ./hello \\
          >hello.stdout.txt 2>hello.stderr.txt
        ltrace -F ./cuda.ltrace.conf -f -tt -e 'cuda*' \\
          -o api.txt ./hello >api.stdout.txt 2>api.stderr.txt

        # Filter after capture, preserving the complete original log
        grep -nE '/dev/nvidia|BEGIN |END |ioctl\\(|mmap\\(' syscalls.txt
        grep 'cuda' api.txt
    ''',
    'script': '''
        # trace.sh also sets a runtime search path for the local CUDA toolkit.
        # Keep output outside your Git worktree.
        CUDA_SM=sm_90 bash trace.sh /path/to/trace-output
    ''',
    'proc': '''
        # For a live, owned process; this tiny example may finish too quickly.
        trace_pid=12345  # replace with the actual PID
        ls -l /proc/$trace_pid/fd
        grep -E 'libcuda|libcudart|/dev/nvidia' /proc/$trace_pid/maps
        cat /proc/$trace_pid/status
    ''',
}


def inspection(lang):
    out = '<div class="cuda-inspection">'
    for item in INSPECTION['items']:
        kind = item['kind']
        label = ('源码格式示例 · 非实测' if lang == 'zh' else 'Source format · not captured') if kind == 'source_format' else ('实测摘录' if lang == 'zh' else 'Captured excerpt')
        out += f'<section class="inspection-item" data-kind="{kind}">'
        out += f'<div class="inspection-heading"><strong>{escape(item["title_"+lang])}</strong><span>{label}</span></div>'
        out += f'<pre class="inspection-command"><code>{escape(item["command"])}</code></pre>'
        out += f'<pre class="inspection-output"><code>{escape(item["output"])}</code></pre>'
        out += '<p>' + escape(item['note_'+lang])
        if item.get('source'):
            out += f' <a href="{item["source"]}" target="_blank" rel="noopener">{escape(item["source_label"])}</a>'
        out += '</p></section>'
    return out + '</div>'


def phase_table(lang):
    zh = lang == 'zh'
    rows = [
        ('cudaSetDevice(0)', '133 / 69 / 548', '库加载、驱动初始化、上下文与线程等' if zh else 'Library loading, initialization, context and threads'),
        ('cudaMalloc', '0 / 0 / 4', '2 个 RM + 2 个 UVM ioctl' if zh else '2 RM and 2 UVM ioctls'),
        ('cudaMemcpy H2D · 4 B', '0 / 0 / 0', '本窗口没有系统调用' if zh else 'No syscalls in this window'),
        ('kernel launch 1 / 2', '0 / 0 / 0', '两次 launch 窗口均无系统调用' if zh else 'Neither launch window contains a syscall'),
        ('cudaDeviceSynchronize × 2', '0 / 0 / 0', '两次同步窗口均无系统调用' if zh else 'Neither synchronization window contains a syscall'),
        ('cudaMemcpy D2H · 4 B', '0 / 0 / 0', '本窗口没有系统调用' if zh else 'No syscalls in this window'),
        ('cudaFree', '0 / 0 / 3', '本窗口有 3 个 ioctl' if zh else '3 ioctls in this window'),
    ]
    out = '<table><thead><tr><th>' + ('主线程阶段' if zh else 'Main-thread phase') + '</th><th>openat / mmap / ioctl</th><th>' + ('观察' if zh else 'Observation') + '</th></tr></thead><tbody>'
    return out + ''.join(f'<tr><td><code>{a}</code></td><td>{b}</td><td>{c}</td></tr>' for a,b,c in rows) + '</tbody></table>'


ZH = r'''
<h1>CUDA 分层与 Linux 驱动</h1>
<p>CUDA 程序把 CPU 上的资源管理与 GPU 上的并行计算连接起来。一次内存分配或 kernel launch，会涉及用户态运行库、驱动建立的地址空间与提交资源，以及 GPU 的执行引擎。Linux 的设备文件和系统调用构成了其中一条可观察的边界。</p>
<p>本文从 CUDA 软件栈的层级展开，定位各组件的公开源码，再用一个计算 <code>40 + 1 + 1</code> 的 H100 程序，将 API 调用、设备文件与驱动入口对应起来。它也是 <strong>Inside CUDA</strong> 系列的起点：沿着程序的执行路径理解 GPU driver 和 Linux 模块。</p>

<h2 id="architecture">1. 基础架构</h2>
<h3 id="execution-spaces">1.1 执行空间</h3>
<p>CUDA 栈横跨三个执行空间：应用进程中的 CPU 用户态代码、Linux 内核中的驱动代码，以及 GPU 上的固件和计算程序。<code>libcuda.so.1</code> 是用户态驱动，仍然运行在 CPU 上；<code>nvidia.ko</code> 是 Linux 内核模块；CUDA 的 <code>__global__</code> kernel 则由 GPU 执行。“驱动”“内核模块”和“GPU kernel”在这里分别指不同对象。</p>
{{architecture}}
<p>计算应用可以直接使用 Driver API，也可以通过 Runtime API 或 NCCL、cuBLAS 等库使用 GPU。计算库内部如何组合 Runtime 与 Driver API 取决于实现；图中画出的是主要依赖。监控和显示各有用户态入口，共用部分底层资源管理能力。</p>

<h3 id="user-libraries">1.2 用户态库</h3>
<table><thead><tr><th>组件</th><th>来源与接口</th><th>主要职责</th></tr></thead><tbody>
<tr><td><code>libcudart.so</code><br><code>libcudart_static.a</code></td><td>CUDA Toolkit<br><code>cudaMalloc</code>、<code>cudaMemcpy</code>、kernel launch</td><td>Runtime API、隐式初始化与上下文管理、与 CUDA 编译器生成的 host 代码协作。</td></tr>
<tr><td><code>libcuda.so.1</code></td><td>NVIDIA 驱动<br><code>cuMemAlloc</code>、<code>cuLaunchKernel</code> 等 Driver API</td><td>用户态驱动，管理上下文、模块、内存与提交资源，并通过设备接口请求内核驱动服务。</td></tr>
<tr><td><code>libnvidia-ml.so</code></td><td>NVIDIA 驱动<br>NVML</td><td>设备状态、显存占用、功耗等监控与管理；<code>nvidia-smi</code> 是它的使用者。</td></tr>
<tr><td>NCCL / cuBLAS</td><td>通信与计算库</td><td>提供集合通信或数值运算，把工作组织为 CUDA 操作与 GPU 程序。</td></tr>
</tbody></table>
<p><code>libcudart</code> 随应用使用的 Toolkit 版本而变化，<code>libcuda</code> 随驱动安装。Runtime 可以静态链接，因此 <code>ldd</code> 中没有 <code>libcudart.so</code> 不代表程序没有使用 CUDA Runtime。<code>nvcc</code> 默认选择静态 Runtime；本文显式使用 <code>--cudart shared</code>，便于观察库函数调用。[[runtime|Runtime 与 Driver API]] · [[nvcc|nvcc 链接选项]]</p>
<p><code>cudaMalloc()</code> 首先是一次用户态函数调用。它是否触发系统调用、触发几个，以及是否需要初始化，取决于当前状态和实现。API 名称与 Linux syscall 之间没有一对一的映射。</p>

<h3 id="kernel-modules">1.3 Linux 模块</h3>
<table><thead><tr><th>模块</th><th>职责与边界</th><th>公开源码入口</th></tr></thead><tbody>
<tr><td><code>nvidia.ko</code></td><td>核心驱动与 Kernel Resource Manager（RM），管理 GPU 资源、对象、内存及地址空间，与 GSP-RM 协作。</td><td>[[fops|nv.c]]<br>[[rm-escape|escape.c]]</td></tr>
<tr><td><code>nvidia-uvm.ko</code></td><td>Unified Virtual Memory：进程的 UVM VA space、映射、缺页处理与迁移，并调用核心 RM 服务。</td><td>[[uvm|uvm.c]]<br>[[uvm-fault|replayable faults]]</td></tr>
<tr><td><code>nvidia-modeset.ko</code></td><td>显示模式和显示引擎管理。</td><td>[[modeset|nvidia-modeset-linux.c]]</td></tr>
<tr><td><code>nvidia-drm.ko</code></td><td>把 NVIDIA 显示驱动接入 Linux DRM/KMS；与 modeset 协作。</td><td>[[drm|nvidia-drm-drv.c]]</td></tr>
</tbody></table>
<p>RM 负责核心 GPU 资源，UVM 在这些能力之上处理进程地址空间与内存映射、迁移等工作。UVM 也会参与普通设备内存的映射；后面的实测中，<code>cudaMalloc</code> 就调用了 UVM 接口。把 UVM 仅理解为 <code>cudaMallocManaged</code> 的实现，会漏掉这部分路径。</p>
<p>模块文件名使用连字符，例如 <code>nvidia-uvm.ko</code>；<code>lsmod</code> 通常显示 <code>nvidia_uvm</code>。显示模块服务于图形路径，纯计算程序不需要经过 DRM/KMS。[[components|驱动组件说明]]</p>

<h3 id="hardware-firmware">1.4 固件与硬件</h3>
<p><strong>GSP 是 GPU 上的管理处理器。</strong>GSP-RM 固件承接一部分设备初始化和管理工作；主机上的 Kernel RM 通过 RPC 等机制与它协作。CUDA kernel 的计算主体仍由 SM 执行。GPU 的 MMU 完成地址转换，Copy Engine 承担适用的搬运任务，显存控制器连接 HBM 或 GDDR。[[gsp-doc|GSP 说明]] · [[gsp|主机侧 GSP 管理源码]]</p>
<p>初始化时，CPU 软件为设备建立资源、页表、映射与提交通道；设备执行时，命令处理器、SM、Copy Engine 和互联硬件完成相应工作。UVM 自身也会提交迁移或页表更新所需的 GPU 工作。[[uvm-push|UVM push 提交代码]]</p>
<p>图中的绿色虚线表示 GPU 之间的 P2P 数据路径，可经 NVLink 或 PCIe。驱动建立访问所需的映射和权限，设备执行数据传输；具体路径取决于拓扑与平台支持。<a href="gpu-peer-to-peer-memory.html">GPU P2P 显存访问</a>一文介绍 peer 映射与远端显存访问。</p>

<h3 id="source-map">1.5 源码地图</h3>
<p>本文源码固定在 <strong>615.71.10</strong>，commit <code>6f3be8c9c3fb</code>，与实测内核驱动一致。仓库中的 <code>kernel-open/</code> 主要包含 Linux 接口层，<code>src/</code> 包含 OS-agnostic 的 RM 等实现；两者都可以编入内核模块。目录名中的 <code>src</code> 不表示用户态。[[repo|该版本 README]]</p>
<table><thead><tr><th>问题</th><th>阅读入口</th></tr></thead><tbody>
<tr><td>设备的 open / ioctl / mmap 如何接入 Linux？</td><td>[[fops|kernel-open/nvidia/nv.c → nvidia_fops]]</td></tr>
<tr><td>RM ioctl 如何分派？</td><td>[[rm-escape|src/nvidia/arch/nvalloc/unix/src/escape.c]]</td></tr>
<tr><td>UVM 命令如何分派？</td><td>[[uvm|kernel-open/nvidia-uvm/uvm.c → uvm_ioctl]]</td></tr>
<tr><td>CPU 的设备映射如何建立？</td><td>[[mmap|kernel-open/nvidia/nv-mmap.c]]</td></tr>
<tr><td>GSP 的主机侧管理在哪里？</td><td>[[gsp|src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c]]</td></tr>
</tbody></table>
<div class="cuda-note"><p><strong>开放源码的范围：</strong>此仓库发布的是 GPU 内核模块。<code>libcuda</code>、<code>libcudart</code>、NVML 和 GSP-RM 固件内部的完整实现源码，不在此次开源范围内。仓库中的固件镜像数据和主机侧 RPC 代码也应与固件实现源码区分。内核模块、用户态驱动和 GSP 固件应按驱动发行版匹配；CUDA Toolkit 有自己的兼容关系。</p></div>

<h2 id="linux-tracing">2. Linux 接口与实测</h2>
<p><strong>内核模块提供驱动实现，设备文件提供用户态访问入口。</strong><code>.ko</code> 加载后运行在内核态；<code>/dev/nvidia*</code> 是字符设备节点，记录 major/minor 设备号及访问权限。一个模块可以提供多个节点：例如 <code>nvidia.ko</code> 同时服务于 <code>/dev/nvidiactl</code> 和各 GPU 的 <code>/dev/nvidia0</code>、<code>nvidia1</code> 等接口。Linux 根据节点的设备号找到已注册的字符设备及其操作表。[[vfs|Linux VFS]]</p>
<p>本文版本的 <code>nvidia.ko</code> 在初始化时调用 <code>nv_register_chrdev()</code>：先用 <code>register_chrdev_region()</code> 注册设备号范围，再通过 <code>cdev_init()</code> 关联 <code>nvidia_fops</code>，最后用 <code>cdev_add()</code> 将字符设备加入内核。GPU 接口与控制接口分别注册，共用这张操作表。<code>nvidia-uvm.ko</code> 则通过 <code>alloc_chrdev_region()</code> 动态分配设备号，并注册关联 <code>uvm_fops</code> 的字符设备。[[chrdev-register|核心驱动注册函数]] · [[chrdev-init|初始化调用点]] · [[uvm-chrdev|UVM 注册]]</p>
<p><strong>内核中的注册与 <code>/dev</code> 中的节点创建是两个步骤。</strong>节点可由发行版的设备管理机制或 NVIDIA 工具按对应设备号创建、设置权限；NVIDIA 用户态驱动在需要时也可调用 <code>nvidia-modprobe</code> 加载模块并创建节点。<code>cdev_add()</code> 本身不创建 <code>/dev/nvidia0</code> 这个路径；节点存在也不保证对应驱动已成功加载。[[device-creation|NVIDIA 设备节点创建机制]]</p>

<h3 id="device-files">2.1 设备文件</h3>
<table><thead><tr><th>设备文件</th><th>典型作用</th></tr></thead><tbody>
<tr><td><code>/dev/nvidiactl</code></td><td>核心驱动控制接口，承载 RM 对象与控制请求。</td></tr>
<tr><td><code>/dev/nvidia0</code>、<code>/dev/nvidia1</code> …</td><td>各 GPU 的设备接口；编号与进程可见的 CUDA ordinal 不一定相同。</td></tr>
<tr><td><code>/dev/nvidia-uvm</code></td><td>UVM 地址空间、映射等接口；部分安装还提供 <code>nvidia-uvm-tools</code>。</td></tr>
<tr><td><code>/dev/nvidia-modeset</code></td><td>NVIDIA 显示模式管理接口。</td></tr>
<tr><td><code>/dev/dri/card*</code>、<code>renderD*</code></td><td>DRM 设备节点；实际节点取决于驱动与显示配置。</td></tr>
<tr><td><code>/dev/nvidia-caps/*</code></td><td>能力与权限相关设备节点，例如 MIG 管理场景。</td></tr>
<tr><td><code>/dev/nvidia-nvswitch*</code>、<code>nvidia-nvlink</code></td><td>特定 NVSwitch / NVLink 系统上的管理接口。</td></tr>
</tbody></table>
<p>以下命令分别观察 PCI 设备、已加载模块、驱动版本与字符设备。<code>/proc/driver/nvidia/</code> 是驱动提供的状态视图，不是显存内容。容器、设备权限和调度器的隔离会影响能看到、能打开的节点。[[caps|设备节点与 capability 接口]]</p>
<p>下面每条命令都配有参考输出与字段说明。实测摘录来自本文的 H100 节点，保留关键行；<code>gpus/*/information</code> 未在该次运行中采集，单独标为源码格式示例。设备号、模块大小和引用计数会随机器与运行状态变化。</p>
{{inspection}}
<p>模块已加载只能说明它可用；一次 CUDA 程序实际经过哪些接口，仍要看该进程的调用。</p>

<h3 id="syscall-dispatch">2.2 open、ioctl 与 mmap</h3>
<p><strong><code>nvidia_fops</code> 和 <code>uvm_fops</code> 都是 Linux 内核 <code>struct file_operations</code> 类型的结构体实例。</strong>这个类型定义在 <code>include/linux/fs.h</code> 中，<code>.open</code>、<code>.unlocked_ioctl</code>、<code>.mmap</code> 等成员是函数指针。Linux 定义操作接口，驱动填入自己的回调函数；例如 <code>nvidia_fops</code> 的 <code>.open</code> 指向 <code>nvidia_open</code>。[[linux-fops|Linux 类型定义]] · [[fops|nvidia_fops]] · [[uvm-fops|uvm_fops]]</p>
<p><code>/dev/nvidiactl</code> 和 <code>/dev/nvidia0</code> 等核心驱动设备使用 <code>nvidia_fops</code>，<code>/dev/nvidia-uvm</code> 使用 <code>uvm_fops</code>。设备打开后，对应的内核 <code>struct file</code> 对象通过 <code>f_op</code> 指向这张操作表。进程持有的 fd 是文件描述符表中的索引；后续系统调用通过 fd 找到该对象，再调用操作表中的回调。因此，相同的文件操作接口可以进入不同驱动的实现。[[vfs|Linux VFS 的文件对象与操作表]]</p>
{{sequence}}
<table><thead><tr><th>接口</th><th>Linux 与驱动如何协作</th></tr></thead><tbody>
<tr><td><code>open / openat</code></td><td>按路径定位设备，进入驱动的 open 回调，建立每次打开所需的状态；成功后返回 fd。用户代码中的 open 也可能在日志中表现为 openat。</td></tr>
<tr><td><code>ioctl(fd, request, arg)</code></td><td>将命令号和参数交给驱动。驱动检查命令、复制或验证用户态参数，再进入 RM / UVM 命令处理。</td></tr>
<tr><td><code>mmap(..., fd, offset)</code></td><td>通过驱动的 mmap 回调，在进程 CPU 虚拟地址空间建立获准的映射；可能涉及驱动管理的内存或设备资源。</td></tr>
</tbody></table>
<p><code>ioctl</code> 的第三个参数常常是 CPU 用户态结构体的地址，里面还可以包含对象 handle、标志和其他参数。<code>mmap</code> 返回的是 CPU 虚拟地址；<code>cudaMalloc</code> 返回的 GPU 可用地址及其物理显存分配，不能直接按某一条 Linux <code>mmap</code> 的长度与返回值解释。[[ioctl|NVIDIA ioctl 参数处理]] · [[mmap|设备 mmap 实现]]</p>

<h3 id="hello-cuda">2.3 Hello CUDA</h3>
<p>程序在 GPU 上对一个整数执行两次加一，然后将结果复制回 CPU。每个阶段的 <code>BEGIN / END</code> 都是主机写入 stderr 的标记，用来界定 syscall 日志中的区间。</p>
{{downloads}}
{{hello}}
{{cmd:build}}
<p><code>-arch=sm_90</code> 对应本次 H100，其他 GPU 需要选择其支持的架构。<code>--cudart shared</code> 让 Runtime 调用保留可跟踪的动态链接边界。若动态加载器找不到 <code>libcudart.so.12</code>，应配置所用 Toolkit 的库路径；下载的 <code>trace.sh</code> 会在编译时加入该路径。</p>
<p><code>ldd</code> 用于检查程序的动态链接依赖。运行时才加载的库不一定出现在其中；本例的 <code>libcuda.so.1</code> 加载过程会在后面的 <code>strace</code> 中出现。</p>
<table><thead><tr><th>实测项</th><th>版本 / 结果</th></tr></thead><tbody>
<tr><td>GPU</td><td>NVIDIA H100 80GB HBM3</td></tr>
<tr><td>驱动</td><td>615.71.10，Open Kernel Module</td></tr>
<tr><td>Linux</td><td>6.8.0-139-generic</td></tr>
<tr><td>编译器 / Runtime</td><td>nvcc 12.4.131 / libcudart 12.4.127，共享链接</td></tr>
<tr><td>工具</td><td>strace 6.8 / ltrace 0.7.91</td></tr>
<tr><td>输出</td><td><code>Hello from CUDA: 42 (expected 42)</code></td></tr>
</tbody></table>

<h3 id="capture">2.4 采集调用</h3>
<p><strong>ltrace 观察动态库函数调用，strace 观察进程进入 Linux 内核的系统调用。</strong>下面分别运行两次程序，避免两个 ptrace 工具争用同一个目标。两份日志的地址与时间戳属于各自运行，不能按时间直接拼成一棵调用树。</p>
{{cmd:trace}}
<p><code>strace -f</code> 包含创建的线程和子进程；<code>-ttt</code> 输出绝对时间，<code>-T</code> 记录 syscall 耗时，<code>-yy</code> 展开 fd 对应的路径及设备信息。这里先采集完整 syscall，再筛选阅读，才能检查某个区间是否真的没有系统调用。ptrace 会扰动执行耗时，这些数据用于分析路径。[[strace|strace]]</p>
<p><code>ltrace -e 'cuda*'</code> 在本程序中捕获到以下 Runtime 调用。配置文件提供了常用函数原型；<code>cudaLaunchKernel</code> 的按值 <code>dim3</code> 参数涉及 ABI 解码，摘录省略其参数，只保留真实的调用名称和返回值。[[ltrace|ltrace 的原型与跟踪范围]]</p>
{{trace:api}}
<p><code>cudaMemcpy</code> 最后一个参数的 <code>1</code> 和 <code>2</code> 分别是 H2D 与 D2H。返回 <code>0</code> 表示本次 API 成功。<code>ltrace</code> 的观测受动态链接方式影响；Runtime 通过内部函数表等机制调用 Driver API 时，<code>cu*</code> 不一定会出现在 PLT 跟踪结果中。更系统的 CUDA API 与 GPU activity 关联可以使用 [[cupti|CUPTI]]，见 <a href="cupti-pytorch-memory-tracing.html">CUPTI 追踪 PyTorch 内存事务</a>。</p>
<details><summary>一键复现与进程检查</summary>
{{cmd:script}}
<p><code>hello.cu</code>、<code>cuda.ltrace.conf</code>、<code>trace.sh</code> 放在同一目录。机器需有可用 NVIDIA GPU、匹配的驱动、CUDA Toolkit、strace 和 ltrace。脚本的输出目录由调用者指定。</p>
{{cmd:proc}}
<p><code>/proc/PID/fd</code> 查看已打开设备，<code>maps</code> 查看 CPU 地址空间。它们属于瞬时视图；这个程序很短，实测以完整 trace 为准。</p></details>

<h3 id="initialization">2.5 初始化与分配</h3>
<p>下面是实际 <code>strace</code> 摘录。<code>L125</code> 等标记为原日志行号；工作目录统一替换为 <code>&lt;workdir&gt;</code>，调用参数、返回值和时间戳保留。</p>
{{trace:loader}}
{{trace:open}}
<p>用户态驱动加载为 <code>libcuda.so.615.71.10</code>，随后打开核心控制节点和 UVM 节点。这个任务中的 CUDA ordinal <code>0</code> 对应 <code>/dev/nvidia1</code>；可见设备集合会被调度环境重新组织，不能把 <code>cudaSetDevice(0)</code> 固定解释为打开 <code>/dev/nvidia0</code>。</p>
{{trace:mmap}}
<p>这条 <code>mmap</code> 的 fd 指向 <code>/dev/nvidiactl</code>，建立了一个 4096 字节的只读共享映射。它与加载 <code>.so</code> 时的普通文件映射有不同的后端。仅凭这行无法给该映射贴上“显存”或“提交队列”的标签。</p>
{{trace:uvm_init}}
<p>UVM 初始化命令实际为 <code>0x30000001</code>。strace 将其按通用位域格式显示成 <code>_IOC(_IOC_NONE, 0, 0x1, 0x3000)</code>；UVM 使用自己的命令编号约定，不能把这里的 <code>0x3000</code> 当作参数结构体长度。[[uvm-init|UVM_INITIALIZE 定义]]</p>
<p><code>cudaMalloc</code> 区间包含四条 ioctl：</p>
{{trace:malloc}}
<table><thead><tr><th>设备 / 编号</th><th>源码名称</th><th>含义</th></tr></thead><tbody>
<tr><td>nvidiactl / <code>0x2b</code></td><td>[[rm-numbers|NV_ESC_RM_ALLOC]]</td><td>RM 资源对象分配入口。</td></tr>
<tr><td>nvidiactl / <code>0x2a</code></td><td>[[rm-control|NV_ESC_RM_CONTROL]]</td><td>RM 控制请求；payload 内还有具体 command 与参数。</td></tr>
<tr><td>nvidia-uvm / <code>0x49</code> = 73</td><td>[[uvm-range|UVM_CREATE_EXTERNAL_RANGE]]</td><td>为外部内存映射建立 UVM 地址范围。</td></tr>
<tr><td>nvidia-uvm / <code>0x21</code> = 33</td><td>[[uvm-map|UVM_MAP_EXTERNAL_ALLOCATION]]</td><td>映射外部 allocation 到该地址空间。</td></tr>
</tbody></table>
<p>这组调用把普通 <code>cudaMalloc</code> 与 RM、UVM 两部分联系起来。日志给出了 ioctl 的外层请求号与参数地址；RM_CONTROL 的内部命令要进一步读取结构体才能确定。Linux syscall 的返回值与驱动在参数结构中写回的 status 也应分别检查。</p>

<h3 id="submission">2.6 提交与完成</h3>
<p>按主线程的 <code>BEGIN / END</code> 标记统计，可以看到初始化与后续执行的差别。表中仅统计两个标记之间的调用，不计标记自身的 <code>write</code>；初始化区间还包含表外的 read、futex、clone3 等系统调用。</p>
{{phases}}
{{trace:launch}}
<p>两次 launch 和两次 <code>cudaDeviceSynchronize</code> 的标记之间都没有新增 syscall。程序仍完成了 GPU 计算并返回 <code>42</code>。这个结果说明，<strong>本次执行的 kernel 提交和完成等待，不需要在这些主线程区间再次进入 Linux 内核。</strong></p>
<p>驱动可以在初始化时建立映射和提交资源，后续利用它们提交工作、观察完成状态。这里的 trace 支持“已有资源可以支撑后续执行”这一解释，但没有记录用户态的内存写入，不能据此还原具体队列格式或 doorbell 协议。同步区间没有 syscall，也不能独自证明使用了哪一种轮询或完成机制。</p>
<div class="cuda-note"><p><strong>这些计数属于一次运行。</strong>不同驱动、首次模块加载、内存池、流状态和工作量都可能改变路径。表中的 4 次 ioctl 不是 <code>cudaMalloc</code> 的接口保证，launch 没有 syscall 也不表示驱动初始化没有参与。</p></div>

<h3 id="observation-boundaries">2.7 观测边界</h3>
<table><thead><tr><th>工具 / 证据</th><th>能回答的问题</th><th>需要补充的证据</th></tr></thead><tbody>
<tr><td>lsmod / lspci / /proc</td><td>设备、模块、CPU 映射和打开的文件。</td><td>某次 CUDA 操作的动态调用路径。</td></tr>
<tr><td>ltrace</td><td>可拦截的动态库调用及其参数、返回值。</td><td>内部函数表调用、内联代码与完整 Driver API 路径。</td></tr>
<tr><td>strace</td><td>进入 Linux 内核的系统调用、设备 fd 和请求号。</td><td>用户态提交内存写入、GPU 指令、完整 ioctl payload。</td></tr>
<tr><td>公开内核源码</td><td>设备回调、命令分派和内核侧资源管理逻辑。</td><td>闭源用户态驱动与 GSP 固件内部实现。</td></tr>
<tr><td>CUPTI / Nsight Systems</td><td>CUDA API 与 GPU activity 的时间和关联关系。</td><td>特定内核函数的执行证据，可结合受控的 ftrace / perf / eBPF 探针。</td></tr>
</tbody></table>
<p>本例建立了两组可以核对的对应关系：<code>cudaMalloc → RM / UVM ioctl → 公开命令定义</code>，以及 <code>kernel launch → GPU 结果</code>。前者穿过 Linux 系统调用边界，后者在已完成初始化的状态下没有新增主线程 syscall。把这两种执行路径分开，才能准确理解驱动在 GPU 程序中的位置。</p>
'''


EN = r'''
<h1>CUDA layers and the Linux driver</h1>
<p>A CUDA program connects resource management on the CPU with parallel execution on the GPU. Allocating memory or launching a kernel involves user-space libraries, driver-established address spaces and submission resources, and GPU execution engines. Linux device files and system calls expose one observable boundary in that path.</p>
<p>This first article in <strong>Inside CUDA</strong> maps the software layers to public source, then traces an H100 program that computes <code>40 + 1 + 1</code>. The example connects CUDA API calls, device files and Linux driver entry points.</p>

<h2 id="architecture-en">1. Architecture</h2>
<h3 id="execution-spaces-en">1.1 Execution spaces</h3>
<p>The stack spans CPU user space, the Linux kernel, and firmware and compute programs running on the GPU. <code>libcuda.so.1</code> is a user-mode driver executing on the CPU. <code>nvidia.ko</code> is a Linux kernel module. A CUDA <code>__global__</code> kernel executes on the GPU. Each use of “driver” or “kernel” refers to a specific execution environment.</p>
{{architecture}}
<p>Applications may use the Driver API directly, the Runtime API, or libraries such as NCCL and cuBLAS. The exact combination of Runtime and Driver APIs inside a library is implementation-dependent; the diagram shows principal dependencies. Monitoring and display have separate entry points and share some underlying resource-management services.</p>

<h3 id="user-libraries-en">1.2 User-space libraries</h3>
<table><thead><tr><th>Component</th><th>Distribution / interface</th><th>Role</th></tr></thead><tbody>
<tr><td><code>libcudart.so</code><br><code>libcudart_static.a</code></td><td>CUDA Toolkit<br>Runtime API</td><td>Runtime services, implicit initialization and context management, and integration with compiler-generated host code.</td></tr>
<tr><td><code>libcuda.so.1</code></td><td>NVIDIA driver<br>Driver API</td><td>User-mode driver: contexts, modules, memory and submission resources; requests kernel-driver services through device interfaces.</td></tr>
<tr><td><code>libnvidia-ml.so</code></td><td>NVIDIA driver<br>NVML</td><td>Monitoring and management, including memory usage and power; used by nvidia-smi.</td></tr>
<tr><td>NCCL / cuBLAS</td><td>Communication / compute libraries</td><td>Organize collective communication or numerical work into CUDA operations and GPU programs.</td></tr>
</tbody></table>
<p>The application’s Toolkit supplies libcudart; the driver installation supplies libcuda. Runtime linking can be static, so the absence of libcudart.so from <code>ldd</code> does not establish that a program avoids the Runtime API. nvcc defaults to static cudart. This example uses <code>--cudart shared</code> to expose a dynamic-library boundary for tracing. [[runtime|Runtime versus Driver API]] · [[nvcc|nvcc linking options]]</p>
<p><code>cudaMalloc()</code> starts as a user-space function call. Whether it enters the kernel, how often, and whether it triggers initialization depend on the implementation and current state. CUDA APIs do not map one to one to Linux syscalls.</p>

<h3 id="kernel-modules-en">1.3 Linux modules</h3>
<table><thead><tr><th>Module</th><th>Responsibility</th><th>Source entry</th></tr></thead><tbody>
<tr><td><code>nvidia.ko</code></td><td>Core driver and Kernel Resource Manager (RM): GPU resources, objects, memory and address spaces, working with GSP-RM.</td><td>[[fops|nv.c]] · [[rm-escape|escape.c]]</td></tr>
<tr><td><code>nvidia-uvm.ko</code></td><td>UVM process address spaces, mappings, faults and migration, using core RM services.</td><td>[[uvm|uvm.c]] · [[uvm-fault|fault handling]]</td></tr>
<tr><td><code>nvidia-modeset.ko</code></td><td>Display modes and display-engine management.</td><td>[[modeset|modeset interface]]</td></tr>
<tr><td><code>nvidia-drm.ko</code></td><td>Linux DRM/KMS integration, working with modeset.</td><td>[[drm|DRM driver]]</td></tr>
</tbody></table>
<p>RM manages core GPU resources. UVM builds process address-space, mapping and migration services on those capabilities. UVM also participates in mappings of ordinary device allocations: the measured cudaMalloc below invokes UVM interfaces. Its role extends beyond cudaMallocManaged.</p>
<p>Module filenames use hyphens, while lsmod usually prints names such as <code>nvidia_uvm</code>. Display modules serve the graphics path; a compute application need not pass through DRM/KMS. [[components|Driver components]]</p>

<h3 id="hardware-firmware-en">1.4 Firmware and hardware</h3>
<p><strong>GSP is a management processor on the GPU.</strong> GSP-RM firmware handles part of device initialization and management, cooperating with host Kernel RM through mechanisms including RPC. CUDA compute kernels execute on SMs. The MMU translates addresses, Copy Engines perform applicable transfers, and memory controllers connect HBM or GDDR. [[gsp-doc|GSP overview]] · [[gsp|Host-side GSP source]]</p>
<p>CPU software establishes resources, page tables, mappings and submission channels. Command processors, SMs, Copy Engines and interconnect hardware then perform the requested device work. UVM also submits GPU work for operations such as migration and page-table updates. [[uvm-push|UVM push submission]]</p>
<p>Teal dashed lines mark GPU P2P data paths over NVLink or PCIe. The driver establishes mappings and access rights, and devices perform the transfers. Available paths depend on topology and platform support. <a href="gpu-peer-to-peer-memory.html">GPU peer-to-peer memory access</a> covers peer mappings and remote GPU-memory access.</p>

<h3 id="source-map-en">1.5 Source map</h3>
<p>Source links are pinned to driver <strong>615.71.10</strong>, commit <code>6f3be8c9c3fb</code>, matching the measured kernel driver. <code>kernel-open/</code> primarily contains Linux interfaces; <code>src/</code> includes OS-agnostic RM implementation. Both can contribute to kernel modules. The directory name src does not imply user-space execution. [[repo|Pinned README]]</p>
<table><thead><tr><th>Question</th><th>Source entry</th></tr></thead><tbody>
<tr><td>Where do device operations enter the driver?</td><td>[[fops|kernel-open/nvidia/nv.c → nvidia_fops]]</td></tr>
<tr><td>How are RM requests dispatched?</td><td>[[rm-escape|src/nvidia/arch/nvalloc/unix/src/escape.c]]</td></tr>
<tr><td>How are UVM requests dispatched?</td><td>[[uvm|kernel-open/nvidia-uvm/uvm.c → uvm_ioctl]]</td></tr>
<tr><td>How are device mappings installed in CPU VA?</td><td>[[mmap|kernel-open/nvidia/nv-mmap.c]]</td></tr>
<tr><td>Where is host-side GSP management?</td><td>[[gsp|src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c]]</td></tr>
</tbody></table>
<div class="cuda-note"><p><strong>Source scope:</strong> this repository publishes GPU kernel modules. Complete implementation source for libcuda, libcudart, NVML and GSP-RM firmware is outside that scope. Firmware image data and host-side RPC code are distinct from firmware implementation source. Kernel modules, user-mode driver components and GSP firmware should match their driver release; Toolkit compatibility follows separate rules.</p></div>

<h2 id="linux-tracing-en">2. Linux interfaces and tracing</h2>
<p><strong>Kernel modules implement drivers; device files expose interfaces to user space.</strong> A loaded <code>.ko</code> runs in kernel space. A <code>/dev/nvidia*</code> character-device node records major/minor device numbers and access permissions. One module can serve several nodes: <code>nvidia.ko</code> handles both <code>/dev/nvidiactl</code> and per-GPU interfaces such as <code>/dev/nvidia0</code> and <code>nvidia1</code>. Linux uses a node's device numbers to locate the registered character device and its operations table. [[vfs|Linux VFS]]</p>
<p>In the pinned driver, initialization calls <code>nv_register_chrdev()</code>: <code>register_chrdev_region()</code> reserves device numbers, <code>cdev_init()</code> associates the character device with <code>nvidia_fops</code>, and <code>cdev_add()</code> adds it to the kernel. GPU and control interfaces are registered separately with the same operations table. <code>nvidia-uvm.ko</code> uses <code>alloc_chrdev_region()</code> to allocate device numbers dynamically, then registers a character device associated with <code>uvm_fops</code>. [[chrdev-register|Core registration]] · [[chrdev-init|Initialization calls]] · [[uvm-chrdev|UVM registration]]</p>
<p><strong>Kernel registration and node creation in <code>/dev</code> are separate steps.</strong> Distribution device-management mechanisms or NVIDIA tools create nodes with the corresponding device numbers and permissions. NVIDIA user-space drivers can also invoke <code>nvidia-modprobe</code> to load modules and create nodes when needed. <code>cdev_add()</code> does not itself create the path <code>/dev/nvidia0</code>; an existing node does not establish that the driver loaded successfully. [[device-creation|NVIDIA device-node creation]]</p>

<h3 id="device-files-en">2.1 Device files</h3>
<table><thead><tr><th>Device</th><th>Typical role</th></tr></thead><tbody>
<tr><td><code>/dev/nvidiactl</code></td><td>Core control interface, including RM object and control requests.</td></tr>
<tr><td><code>/dev/nvidia0</code>, <code>nvidia1</code> …</td><td>Per-GPU interfaces. Suffixes need not match an application's CUDA ordinal.</td></tr>
<tr><td><code>/dev/nvidia-uvm</code></td><td>UVM address-space and mapping interfaces; some installations also expose nvidia-uvm-tools.</td></tr>
<tr><td><code>/dev/nvidia-modeset</code></td><td>NVIDIA display-mode management interface.</td></tr>
<tr><td><code>/dev/dri/card*</code>, <code>renderD*</code></td><td>DRM nodes, depending on driver and display configuration.</td></tr>
<tr><td><code>/dev/nvidia-caps/*</code></td><td>Capability and permission interfaces, including MIG management cases.</td></tr>
<tr><td><code>/dev/nvidia-nvswitch*</code>, <code>nvidia-nvlink</code></td><td>Management interfaces on applicable NVSwitch / NVLink systems.</td></tr>
</tbody></table>
<p>These commands inspect PCI devices, loaded modules, driver version and character devices. <code>/proc/driver/nvidia/</code> exposes driver state, not VRAM contents. Containers, device permissions and scheduler isolation affect visibility and access. [[caps|Device nodes and capabilities]]</p>
<p>Each command below has reference output and a field guide. Captured excerpts retain key lines from this article's H100 host. The gpus/*/information file was not captured and is explicitly labeled as a source-format example. Device numbers, module sizes and reference counts depend on the host and current state.</p>
{{inspection}}
<p>A loaded module is available; per-process tracing determines which interfaces an application actually uses.</p>

<h3 id="syscall-dispatch-en">2.2 open, ioctl and mmap</h3>
<p><strong><code>nvidia_fops</code> and <code>uvm_fops</code> are both instances of the Linux kernel's <code>struct file_operations</code>.</strong> Defined in <code>include/linux/fs.h</code>, this type contains function pointers such as <code>.open</code>, <code>.unlocked_ioctl</code> and <code>.mmap</code>. Linux defines the operation interface; each driver supplies its callbacks. For example, <code>nvidia_fops.open</code> points to <code>nvidia_open</code>. [[linux-fops|Linux type definition]] · [[fops|nvidia_fops]] · [[uvm-fops|uvm_fops]]</p>
<p>Core-driver devices such as <code>/dev/nvidiactl</code> and <code>/dev/nvidia0</code> use <code>nvidia_fops</code>; <code>/dev/nvidia-uvm</code> uses <code>uvm_fops</code>. After a device is opened, the kernel's <code>struct file</code> object points to its operations table through <code>f_op</code>. The process holds an fd, an index into its file-descriptor table. Subsequent syscalls use that fd to find the file object and invoke the appropriate callback. The same file-operation interface can therefore reach different driver implementations. [[vfs|Linux VFS file objects and operations]]</p>
{{sequence}}
<table><thead><tr><th>Interface</th><th>Linux / driver interaction</th></tr></thead><tbody>
<tr><td><code>open / openat</code></td><td>Locate the node, invoke the driver's open callback, initialize per-open state and return an fd. A library open call may appear as openat in a syscall trace.</td></tr>
<tr><td><code>ioctl(fd, request, arg)</code></td><td>Pass a request and arguments to the driver, which validates or copies parameters and dispatches an RM / UVM command.</td></tr>
<tr><td><code>mmap(..., fd, offset)</code></td><td>Use the driver's mmap callback to establish an allowed CPU virtual mapping of driver-managed memory or device resources.</td></tr>
</tbody></table>
<p>An ioctl argument is often the CPU address of a parameter structure containing handles, flags and additional arguments. mmap returns a CPU virtual address. A cudaMalloc result and its physical GPU allocation cannot be inferred from the size and result of one Linux mmap call. [[ioctl|NVIDIA ioctl argument handling]] · [[mmap|Device mmap implementation]]</p>

<h3 id="hello-cuda-en">2.3 Hello CUDA</h3>
<p>The program increments one integer twice on the GPU and copies the result back. BEGIN / END markers are host writes to stderr, delimiting phases in the syscall log.</p>
{{downloads}}
{{hello}}
{{cmd:build}}
<p>The sm_90 target matches the measured H100; select a supported target for another GPU. Shared cudart provides a traceable dynamic-library boundary. If the loader cannot find libcudart.so.12, configure the selected Toolkit's library path. The downloadable script embeds that path at build time.</p>
<p>ldd inspects dynamic-link dependencies. Libraries loaded later at runtime may not appear there; this program's libcuda.so.1 load appears in the strace capture below.</p>
<table><thead><tr><th>Measured item</th><th>Version / result</th></tr></thead><tbody>
<tr><td>GPU</td><td>NVIDIA H100 80GB HBM3</td></tr>
<tr><td>Driver</td><td>615.71.10, Open Kernel Module</td></tr>
<tr><td>Linux</td><td>6.8.0-139-generic</td></tr>
<tr><td>Compiler / Runtime</td><td>nvcc 12.4.131 / shared libcudart 12.4.127</td></tr>
<tr><td>Tools</td><td>strace 6.8 / ltrace 0.7.91</td></tr>
<tr><td>Output</td><td><code>Hello from CUDA: 42 (expected 42)</code></td></tr>
</tbody></table>

<h3 id="capture-en">2.4 Capturing calls</h3>
<p><strong>ltrace observes dynamic-library calls; strace observes syscalls entering Linux.</strong> Run the program separately for each ptrace tool. Addresses and timestamps belong to separate executions and cannot be joined into one call tree by time.</p>
{{cmd:trace}}
<p>strace -f follows created threads and child processes; -ttt prints absolute timestamps, -T reports syscall duration, and -yy resolves file descriptors and device information. Capture all syscalls before filtering so an empty phase really means no syscall was recorded there. ptrace perturbs timing; these logs establish paths, not GPU performance. [[strace|strace]]</p>
<p>The ltrace configuration supplies prototypes for common Runtime functions. The captured cudaLaunchKernel call passes dim3 structures by value, requiring ABI-aware decoding. Its argument fields are omitted below; call names and return values are retained. [[ltrace|ltrace prototypes and scope]]</p>
{{trace:api}}
<p>The final cudaMemcpy arguments 1 and 2 mean H2D and D2H; return value 0 indicates API success. ltrace coverage depends on dynamic-linking mechanisms. Driver API calls made through internal function tables may not appear in PLT tracing. For CUDA API and GPU-activity correlation, use [[cupti|CUPTI]]; see <a href="cupti-pytorch-memory-tracing.html">Tracing PyTorch memory transactions with CUPTI</a>.</p>
<details><summary>Reproduction script and process inspection</summary>
{{cmd:script}}
<p>Keep hello.cu, cuda.ltrace.conf and trace.sh together. The host needs a usable NVIDIA GPU and driver, CUDA Toolkit, strace and ltrace. Supply an output directory outside the source worktree.</p>
{{cmd:proc}}
<p>/proc/PID/fd lists open files; maps shows CPU virtual mappings. These are snapshots. The example is short, so the recorded traces provide the authoritative observations here.</p></details>

<h3 id="initialization-en">2.5 Initialization and allocation</h3>
<p>The excerpts below are real strace output. L125 and similar prefixes refer to original log lines. Only the working directory is replaced with &lt;workdir&gt;; arguments, return values and timestamps are preserved.</p>
{{trace:loader}}
{{trace:open}}
<p>The process loads libcuda.so.615.71.10 and opens core-control and UVM nodes. CUDA ordinal 0 in this scheduled task corresponds to /dev/nvidia1. The visible device set can be remapped; cudaSetDevice(0) does not universally identify /dev/nvidia0.</p>
{{trace:mmap}}
<p>This mmap uses a /dev/nvidiactl fd to create a 4096-byte read-only shared mapping. Its backend differs from a regular shared-library file mapping. This line alone does not identify the mapping as VRAM or a submission queue.</p>
{{trace:uvm_init}}
<p>The UVM initialization request is 0x30000001. strace renders it using generic _IOC fields as _IOC(_IOC_NONE, 0, 0x1, 0x3000). UVM has its own request-number convention; 0x3000 here is not the parameter-structure length. [[uvm-init|UVM_INITIALIZE definition]]</p>
<p>The cudaMalloc interval contains four ioctls:</p>
{{trace:malloc}}
<table><thead><tr><th>Device / number</th><th>Source name</th><th>Meaning</th></tr></thead><tbody>
<tr><td>nvidiactl / 0x2b</td><td>[[rm-numbers|NV_ESC_RM_ALLOC]]</td><td>RM resource-object allocation entry.</td></tr>
<tr><td>nvidiactl / 0x2a</td><td>[[rm-control|NV_ESC_RM_CONTROL]]</td><td>RM control request; the payload contains a further command and parameters.</td></tr>
<tr><td>nvidia-uvm / 0x49 = 73</td><td>[[uvm-range|UVM_CREATE_EXTERNAL_RANGE]]</td><td>Create a UVM VA range for external memory mappings.</td></tr>
<tr><td>nvidia-uvm / 0x21 = 33</td><td>[[uvm-map|UVM_MAP_EXTERNAL_ALLOCATION]]</td><td>Map an external allocation into that address space.</td></tr>
</tbody></table>
<p>These calls connect ordinary cudaMalloc with both RM and UVM. The log exposes outer request numbers and argument addresses; decoding RM_CONTROL's inner command requires reading the structure. The Linux syscall return and the status written by the driver into its payload are separate results.</p>

<h3 id="submission-en">2.6 Submission and completion</h3>
<p>Main-thread BEGIN / END intervals show the difference between setup and execution. The table excludes the marker writes. Initialization also contains syscall types not listed here, including read, futex and clone3.</p>
{{phases}}
{{trace:launch}}
<p>Neither launch interval nor either cudaDeviceSynchronize interval contains a new syscall. GPU work still completes and the program returns 42. <strong>In this execution, submission and completion waiting required no new Linux entry within these main-thread intervals.</strong></p>
<p>A driver can establish mappings and submission resources during initialization, then use them to submit work and observe completion. The trace is consistent with that explanation, but does not record user-space memory writes, queue formats or a doorbell protocol. Absence of a syscall also does not identify the exact polling or completion mechanism.</p>
<div class="cuda-note"><p><strong>The counts describe one execution.</strong> Driver version, first module loading, memory pools, stream state and workload can change the path. Four ioctls are not a cudaMalloc contract. A launch with no new syscall still relies on prior driver setup.</p></div>

<h3 id="observation-boundaries-en">2.7 Observation boundaries</h3>
<table><thead><tr><th>Evidence</th><th>What it reveals</th><th>What needs more evidence</th></tr></thead><tbody>
<tr><td>lsmod / lspci / /proc</td><td>Devices, modules, CPU mappings and open files.</td><td>A particular CUDA operation's dynamic path.</td></tr>
<tr><td>ltrace</td><td>Interceptable library calls, arguments and returns.</td><td>Internal function-table calls, inlined code and complete Driver API coverage.</td></tr>
<tr><td>strace</td><td>Syscalls, device fds and request numbers.</td><td>Submission-buffer writes, GPU instructions and full ioctl payloads.</td></tr>
<tr><td>Public kernel source</td><td>Device callbacks, command dispatch and kernel resource logic.</td><td>Closed user-mode driver and GSP firmware internals.</td></tr>
<tr><td>CUPTI / Nsight Systems</td><td>CUDA API and GPU-activity timing and correlation.</td><td>Specific kernel-function execution; controlled ftrace, perf or eBPF probes can add evidence.</td></tr>
</tbody></table>
<p>The example establishes two checkable paths: cudaMalloc through RM / UVM ioctls to public command definitions, and kernel launches to a computed GPU result. The first crosses the Linux syscall boundary. The second, after initialization, needs no new main-thread syscall in this capture. Distinguishing those paths makes the driver's role easier to locate.</p>
'''


def expand(body, lang):
    for component, prefix in TABLE_COMPONENTS.items():
        original = f'<tr><td>{prefix}'
        assert body.count(original) == 1, (lang, component)
        body = body.replace(original, f'<tr data-component-row="{component}"><td>{prefix}')
    body = re.sub(r'\[\[([\w-]+)\|([^\]]+)\]\]', lambda m: link(m[1], m[2]), body)
    body = re.sub(r'\{\{cmd:(\w+)\}\}', lambda m: code(COMMANDS[m[1]]), body)
    body = re.sub(r'\{\{trace:(\w+)\}\}', lambda m: code(EVIDENCE['snippets'][m[1]], True), body)
    downloads = '<p class="download-links">' + ' '.join(
        f'<a href="{BASE}{filename}" download>{label}</a>' for filename,label in [
            ('hello.cu','hello.cu'),('cuda.ltrace.conf','cuda.ltrace.conf'),('trace.sh','trace.sh'),
            ('evidence.json','实测摘录 JSON' if lang == 'zh' else 'Measured evidence JSON')]) + '</p>'
    return body.replace('{{architecture}}',figure(lang,'architecture')).replace('{{sequence}}',figure(lang,'sequence')).replace('{{hello}}',code((ASSETS/'hello.cu').read_text())).replace('{{downloads}}',downloads).replace('{{phases}}',phase_table(lang)).replace('{{inspection}}',inspection(lang))


def main():
    meta = {
        'title':'CUDA 分层与 Linux 驱动', 'title_en':'CUDA layers and the Linux driver',
        'slug':'cuda-linux-driver-stack', 'date':'2026-11-09',
        'tags':'CUDA, Linux, GPU, 驱动, 系统调用', 'tags_en':'CUDA, Linux, GPU, Driver, Syscalls',
        'reading':'20 分钟', 'reading_en':'20 min',
        'summary':'调用一次 CUDA API，底下发生了哪些 ioctl？文章用 H100 上的 strace/ltrace 实测日志，把 API 调用对到设备文件和驱动入口。',
        'summary_en':'Which ioctls run beneath a single CUDA API call? Measured strace and ltrace logs from an H100 map API calls to device files and driver entry points.',
        'series':'inside-cuda', 'series_title':'Inside CUDA', 'series_title_en':'Inside CUDA', 'series_order':'1',
    }
    metadata = '\n'.join(f'<meta name="post:{k}" content="{escape(v,quote=True)}">' for k,v in meta.items())
    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{meta['title']}</title>
{metadata}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="{BASE}style.css?v=gpu-stack-6">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="{BASE}page.js?v=component-info-4" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>{render_series_nav(meta, ROOT / 'posts')}</aside><main class="content cuda-article">
<div class="lang-zh">{expand(ZH,'zh')}</div><div class="lang-en">{expand(EN,'en')}</div>
</main></div></body></html>
'''
    target = ROOT / 'posts/cuda-linux-driver-stack.html'
    target.write_text(html)
    print('Wrote',target)


if __name__ == '__main__':
    main()
