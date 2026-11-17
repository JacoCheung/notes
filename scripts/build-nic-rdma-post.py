#!/usr/bin/env python3
"""Networking Fundamentals #5. Pinned source references; the diagram is a source schematic.

Reuse the CUDA Internals sequence-diagram styles and window-fit controls.
"""
from html import escape
from pathlib import Path
from post_series import render_series_nav
from abbreviations import annotate_abbreviations
import json
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/networking-basics/nic-rdma'
SHARED = '../assets/inside-cuda/linux-stack/'
DIAGRAMS = '../assets/inside-cuda/gpu-interconnect/'
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
        // The same 4 KiB as an RC RDMA Write. PD, MR, CQ and an RTS QP
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
    'modinfo': '''
        $ modinfo mlx5_ib | grep -E '^(alias|depends)'
        alias:          auxiliary:mlx5_core.rdma-rep
        alias:          auxiliary:mlx5_core.multiport
        alias:          auxiliary:mlx5_core.rdma
        depends:        mlx5_core,ib_core,mlx_compat,ib_uverbs
    ''',
}


def txt(x, y, words, size=15, anchor='middle', cls='', weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" class="{cls}" font-weight="{weight}">{escape(words)}</text>'


def svg_start(name, height, title):
    out = f'<svg class="cuda-diagram interconnect-diagram" viewBox="0 0 1160 {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{name}-title"><title id="{name}-title">{escape(title)}</title><defs>'
    for kind in ['control', 'payload']:
        out += f'<marker id="{name}-{kind}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="head-{kind}" d="M0 0L10 5L0 10Z"/></marker>'
    return out + '</defs>'


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
}


def sequence(kind,lang):
    spec = SEQUENCES[kind]
    name = f'nic-{kind}-{lang}'
    height = 104 + len(spec['rows'])*62 + 26
    actors = spec['actors_zh'] if lang == 'zh' else spec['actors']
    xs = [120,350,580,810,1040]
    out = svg_start(name,height,TITLES[kind][0 if lang == 'zh' else 1])
    for i,(title,sub) in enumerate(actors):
        x=xs[i]
        out+=f'<g class="node"><rect x="{x-104}" y="16" width="208" height="54" rx="4"/>'
        out+=txt(x,39,title,15,weight=650)+txt(x,59,sub,12,cls='muted')+'</g>'
        out+=f'<path class="lifeline" d="M{x} 72V{height-14}"/>'
    for actor,begin,end in spec['bars']:
        y=102+begin*62
        out+=f'<rect class="activation" x="{xs[actor]-6}" y="{y-5}" width="12" height="{(end-begin)*62+27}" rx="1"/>'
    for i,(a,b,label,kind_,ref) in enumerate(spec['rows']):
        if lang == 'zh':
            label = spec['labels_zh'][i]
        y=112+i*62
        x1,x2=xs[a],xs[b]
        # Keep labels inside the viewBox even for self-calls in the last lane.
        label_width = sum(14 if ord(char) > 255 else 8.5 for char in label)
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
}
CAPTIONS = {
    'rdma-write':('两端已注册 MR，QP 处于 RTS，A 已拿到 B 的地址和 rkey。蓝色为控制，紫色为 payload。①② 由 A 的 CPU 在用户态完成，B 网卡直接写入已注册内存。采用 BlueFlame 时，② 同时把 WQE 写进 UAR，省去网卡读取该描述符的步骤（第 4 节）。', 'Both MRs are registered, the QP is in RTS, and A holds B\'s address and rkey. Blue: control. Purple: payload. A\'s CPU performs ① and ② in user space; NIC B writes the registered destination directly. With BlueFlame, ② also delivers the WQE through the UAR, avoiding the descriptor fetch (section 4).'),
}


def figure(kind,lang):
    idx=0 if lang=='zh' else 1
    title=TITLES[kind][idx]
    drawing,height=sequence(kind,lang)
    fit,actual=('适应窗口','原始尺寸') if idx==0 else ('Fit window','Actual size')
    return f'''<figure class="cuda-figure" data-size="fit" data-layout="{kind}" style="--diagram-ratio:{1160/height:.10f};--diagram-width:1160px"><div class="diagram-toolbar"><strong>{title}</strong><button type="button" data-size-toggle aria-pressed="false" data-fit-label="{fit}" data-actual-label="{actual}">{actual}</button></div><div class="diagram-viewport" tabindex="0" role="region" aria-label="{title}">{drawing}</div><figcaption>{CAPTIONS[kind][idx]}</figcaption></figure>'''


def expand(lang):
    body=(ROOT/f'scripts/content/nic-rdma.{lang}.html').read_text()
    body=re.sub(r'\[\[([\w-]+)\|([^\]]+)\]\]',lambda m:link(m[1],m[2]),body)
    body=re.sub(r'\{\{code:([\w-]+)\}\}',lambda m:code(CODE[m[1]]),body)
    for kind in TITLES: body=body.replace('{{'+kind+'}}',figure(kind,lang))
    assert not re.search(r'\{\{[\w:-]+\}\}|\[\[[\w-]+\|', body)
    return annotate_abbreviations(body, lang)


def main():
    meta=dict(title='网卡与 RDMA：从 socket 到 verbs',title_en='NICs and RDMA: from sockets to verbs',slug='nic-rdma-socket-verbs',date='2026-11-10',tags='RDMA, Verbs, mlx5, 网卡驱动',tags_en='RDMA, Verbs, mlx5, NIC Drivers',reading='8 分钟',reading_en='8 min',summary='跨机器传输数据时，远程直接内存访问怎样减少处理器的工作？应用先登记缓冲区和访问权限，再提交请求，让网卡直接读写对端指定内存，并用完成通知确认传输进度。',summary_en='How can transferring data between machines require less processor work? Applications register buffers and permissions, then use remote direct memory access to let network adapters move data and report completion.',series='networking-basics',series_title='网络入门原理',series_title_en='Networking Fundamentals',series_order='5')
    metadata='\n'.join(f'<meta name="post:{key}" content="{escape(value,quote=True)}">' for key,value in meta.items())
    html=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{meta['title']}</title>
{metadata}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3"><link rel="stylesheet" href="{SHARED}style.css?v=gpu-stack-6"><link rel="stylesheet" href="{DIAGRAMS}style.css?v=4">
<link rel="stylesheet" href="../assets/abbreviations.css?v=1"><script src="../assets/abbreviations.js?v=1" defer></script>
<script src="../lang-toggle.js?v=post-toc-3" defer></script><script src="{SHARED}page.js?v=component-info-4" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>{render_series_nav(meta, ROOT / 'posts')}</aside><main class="content cuda-article interconnect-article"><div class="lang-zh">{expand('zh')}</div><div class="lang-en">{expand('en')}</div></main></div></body></html>'''
    target=ROOT/'posts/nic-rdma-socket-verbs.html'
    target.write_text(html)
    print('Wrote',target)


if __name__=='__main__': main()
