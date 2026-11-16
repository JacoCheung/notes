"""Annotate prose abbreviations while preserving source, links and SVG markup."""
from dataclasses import dataclass, field
from html import escape, unescape
from html.parser import HTMLParser
import re


# Full names are shared by both articles; the second field is the Chinese label.
GLOSSARY = {
    'CPU': ('Central Processing Unit', '中央处理器'),
    'GPU': ('Graphics Processing Unit', '图形处理器'),
    'NIC': ('Network Interface Card', '网络接口卡'),
    'DMA': ('Direct Memory Access', '直接内存访问'),
    'RDMA': ('Remote Direct Memory Access', '远程直接内存访问'),
    'DMA-BUF': ('DMA buffer sharing framework', 'DMA 缓冲区共享框架'),
    'TCP': ('Transmission Control Protocol', '传输控制协议'),
    'IP': ('Internet Protocol', '互联网协议'),
    'IPv4': ('Internet Protocol version 4', '互联网协议第 4 版'),
    'UDP': ('User Datagram Protocol', '用户数据报协议'),
    'PCI': ('Peripheral Component Interconnect', '外设组件互连'),
    'PCIe': ('Peripheral Component Interconnect Express', '高速外设组件互连'),
    'BAR': ('Base Address Register', '基址寄存器'),
    'MMIO': ('Memory-Mapped I/O', '内存映射 I/O'),
    'I/O': ('Input/Output', '输入/输出'),
    'IOMMU': ('Input/Output Memory Management Unit', '输入/输出内存管理单元'),
    'API': ('Application Programming Interface', '应用编程接口'),
    'TLS': ('Thread-Local Storage', '线程局部存储'),
    'RAII': ('Resource Acquisition Is Initialization', '以对象生命周期管理资源'),
    'SQ': ('Send Queue', '发送队列'),
    'RQ': ('Receive Queue', '接收队列'),
    'WQE': ('Work Queue Element', '工作队列项'),
    'WR': ('Work Request', '工作请求'),
    'DBR': ('Doorbell Record', '门铃记录'),
    'UAR': ('User Access Region', '用户访问区域'),
    'CQ': ('Completion Queue', '完成队列'),
    'CQE': ('Completion Queue Entry', '完成队列项'),
    'PD': ('Protection Domain', '保护域'),
    'MR': ('Memory Region', '内存区域'),
    'QP': ('Queue Pair', '队列对'),
    'RC': ('Reliable Connection', '可靠连接'),
    'UD': ('Unreliable Datagram', '不可靠数据报'),
    'RTR': ('Ready to Receive', 'QP 准备接收状态'),
    'RTS': ('Ready to Send', 'QP 准备发送状态'),
    'NAPI': ('New API', 'Linux 网络收包轮询接口'),
    'MTU': ('Maximum Transmission Unit', '最大传输单元'),
    'IB': ('InfiniBand', 'InfiniBand 网络互连'),
    'RoCE': ('RDMA over Converged Ethernet', '融合以太网上的 RDMA'),
    'RMA': ('Remote Memory Access', '远程内存访问'),
    'CUDA': ('Compute Unified Device Architecture', '统一计算设备架构'),
    'NCCL': ('NVIDIA Collective Communication Library', 'NVIDIA 集合通信库'),
    'NVSHMEM': ('NVIDIA Shared Memory Library', 'NVIDIA 对称内存通信库'),
    'GIN': ('GPU-Initiated Networking', 'GPU 发起的网络通信'),
    'GDAKI': ('GPUDirect Async Kernel-Initiated', 'kernel 发起的 GPUDirect 异步通信'),
    'IBGDA': ('InfiniBand GPUDirect Async', 'InfiniBand GPUDirect 异步传输'),
    'IBRC': ('InfiniBand Reliable Connection', 'InfiniBand 可靠连接传输'),
    'GFD': ('GPU-Function Descriptor', 'GIN proxy 的 GPU 函数描述符'),
    'PE': ('Processing Element', '通信处理单元'),
    'LSA': ('Load/Store Accessible', '可通过 load/store 直接访问'),
    'UVM': ('Unified Virtual Memory', '统一虚拟内存'),
    'RM': ('Resource Manager', '资源管理器'),
    'SM': ('Streaming Multiprocessor', '流式多处理器'),
    'MMU': ('Memory Management Unit', '内存管理单元'),
    'VMM': ('Virtual Memory Management', '虚拟内存管理'),
    'VMA': ('Virtual Memory Area', '虚拟内存区域'),
    'PFN': ('Page Frame Number', '页帧号'),
    'PTE': ('Page Table Entry', '页表项'),
    'PCF': ('Permission Control Flags', '权限控制标志'),
    'HAL': ('Hardware Abstraction Layer', '硬件抽象层'),
    'ACD': ('Access Counters Disabled', '访问计数器关闭'),
    'ACE': ('Access Counters Enabled', '访问计数器开启'),
    'TLB': ('Translation Lookaside Buffer', '地址转换后备缓冲'),
    'PTX': ('Parallel Thread Execution', '并行线程执行虚拟指令集'),
    'NC': ('Non-Cached', '非缓存映射'),
    'BF': ('BlueFlame', 'mlx5 描述符提交寄存器机制'),
    'RW': ('Read/Write', '可读写'),
    'DOCA': ('Data Center Infrastructure-on-a-Chip Architecture', 'NVIDIA 数据中心基础设施软件架构'),
    'SDK': ('Software Development Kit', '软件开发工具包'),
    'NVTX': ('NVIDIA Tools Extension', 'NVIDIA 性能分析标注接口'),
    'GDR': ('GPUDirect RDMA', 'GPU 显存与第三方设备之间的直接 DMA'),
    'VRAM': ('Video Random Access Memory', '显存'),
    'OFED': ('OpenFabrics Enterprise Distribution', 'OpenFabrics 驱动软件发行包'),
    'KiB': ('Kibibyte (1024 bytes)', '1024 字节'),
    'KB': ('Kilobyte (1000 bytes)', '1000 字节'),
}
ALIASES = {term + 's': term for term in (
    'CPU', 'GPU', 'NIC', 'BAR', 'API', 'WQE', 'WR', 'DBR', 'UAR', 'CQ',
    'CQE', 'PD', 'MR', 'QP', 'PE', 'SM', 'PFN', 'PTE', 'VMA',
)}
TERMS = {term: term for term in GLOSSARY} | ALIASES
# ASCII boundaries leave Chinese prose eligible but protect identifiers and paths.
PATTERN = re.compile(r'(?<![A-Za-z0-9_.])(?:' + '|'.join(
    re.escape(term) for term in sorted(TERMS, key=len, reverse=True)
) + r')(?![A-Za-z0-9_])')
BLOCKS = {'p', 'td', 'th', 'li', 'figcaption', 'summary'}
SKIP = {'pre', 'script', 'style', 'svg', 'a', 'abbr', 'button', 'select',
        'textarea', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}


@dataclass
class Token:
    raw: str
    value: str = ''
    block: int | None = None
    offset: int = 0
    eligible: bool = False
    definitions: set[str] = field(default_factory=set)


@dataclass
class Frame:
    tag: str
    block: int | None
    skip: bool
    definitions: set[str] = field(default_factory=set)
    component_row: bool = False
    cells: int = 0


class ProseParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tokens = []
        self.stack = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        self.tokens.append(Token(self.get_starttag_text()))
        parent = self.stack[-1] if self.stack else None
        data = dict(attrs)
        block = parent.block if parent else None
        if tag in BLOCKS:
            block = len(self.blocks)
            self.blocks.append('')
        skip = bool(parent and parent.skip) or tag in SKIP or 'data-abbr-skip' in data
        definitions = (parent.definitions.copy() if parent else set()) | set(
            data.get('data-abbr-definition', '').split())
        # The first cell of a component definition names the component itself.
        if tag == 'td' and parent and parent.tag == 'tr':
            parent.cells += 1
            if parent.component_row and parent.cells == 1:
                skip = True
        if tag in VOID:
            if tag == 'br' and block is not None:
                self.blocks[block] += '\n'
        else:
            self.stack.append(Frame(tag, block, skip, definitions, 'data-component-row' in data))

    def handle_startendtag(self, tag, attrs):
        self.tokens.append(Token(self.get_starttag_text()))

    def handle_endtag(self, tag):
        self.tokens.append(Token(f'</{tag}>'))
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, value):
        parent = self.stack[-1] if self.stack else None
        block = parent.block if parent else None
        offset = len(self.blocks[block]) if block is not None else 0
        if block is not None:
            self.blocks[block] += value
        eligible = block is not None and not parent.skip
        token = Token(value, value, block, offset, eligible)
        token.definitions = parent.definitions if parent else set()
        self.tokens.append(token)

    def entity(self, raw):
        parent = self.stack[-1] if self.stack else None
        if parent and parent.block is not None:
            self.blocks[parent.block] += unescape(raw)
        self.tokens.append(Token(raw))

    def handle_entityref(self, name):
        self.entity(f'&{name};')

    def handle_charref(self, name):
        self.entity(f'&#{name};')

    def handle_comment(self, data):
        self.tokens.append(Token(f'<!--{data}-->'))


def phrase_pattern(phrase):
    pattern = re.escape(phrase).replace(r'\ ', r'\s+')
    # English plurals such as Completion Queue Entries change the final spelling.
    if re.search(r'[A-Za-z]y$', phrase):
        pattern = pattern[:-1] + '(?:y|ies)'
    return pattern


def is_definition(text, start, end, canonical):
    """Recognize both WQE (Work Queue Element) and send queue (SQ)."""
    before, after = text[max(0, start - 100):start], text[end:end + 140]
    for phrase in GLOSSARY[canonical]:
        words = phrase_pattern(phrase)
        # Parenthetical/full-name definitions, including definitions split by <code>.
        if re.match(r'\s*[（(·,:：]?\s*' + words, after, re.I):
            return True
        if re.search(words + r'\s*[（(]\s*$', before, re.I):
            return True
        if re.match(r'\s*(?:is\s+(?:a|an|the)\s+|means\s+|stands\s+for\s+|是|即|指|表示)[^。;；]{0,24}?' + words, after, re.I):
            return True
    return False


def annotate_abbreviations(body, lang):
    parser = ProseParser()
    parser.feed(body)
    parser.close()
    expansion_ranges = []
    for block in parser.blocks:
        ranges = []
        for match in PATTERN.finditer(block):
            canonical = TERMS[match.group()]
            if not is_definition(block, match.start(), match.end(), canonical):
                continue
            lo, hi = max(0, match.start() - 100), match.end() + 140
            for phrase in GLOSSARY[canonical]:
                pattern = phrase_pattern(phrase)
                for full in re.finditer(pattern, block[lo:hi], re.I):
                    ranges.append((lo + full.start(), lo + full.end()))
        expansion_ranges.append(ranges)
    output = []
    for token in parser.tokens:
        if not token.eligible:
            output.append(token.raw)
            continue
        def replace(match):
            term = match.group()
            canonical = TERMS[term]
            begin, end = token.offset + match.start(), token.offset + match.end()
            if any(lo <= begin and end <= hi for lo, hi in expansion_ranges[token.block]):
                return term
            if canonical in token.definitions or is_definition(
                parser.blocks[token.block], begin, end, canonical,
            ):
                return term
            english, chinese = GLOSSARY[canonical]
            expansion = english + (' · ' + chinese if lang == 'zh' else '')
            return (f'<abbr class="term-abbr" data-term="{canonical}" '
                    f'title="{escape(expansion, quote=True)}" tabindex="0">{term}</abbr>')
        output.append(PATTERN.sub(replace, token.raw))
    return ''.join(output)
