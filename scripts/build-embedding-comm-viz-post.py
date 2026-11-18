#!/usr/bin/env python3
"""Build the TorchRec key-flow player and the matching worked example."""
from html import escape
from pathlib import Path
import ast
import json
import sys
import re
from post_series import render_series_nav

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/torchrec/embedding-comm-viz'
EXAMPLE = json.loads((ASSETS / 'example.json').read_text())
sys.path.insert(0, str(ASSETS))
import hier_input_dist_example as hier  # noqa: E402  the DynamicEmb layout model
HIER = hier.simulate()
META = dict(
    title='embedding comm viz', title_en='embedding comm viz',
    slug='embedding-comm-viz', date='2026-11-18',
    tags='TorchRec, Embedding, AllToAll, 数据流', tags_en='TorchRec, Embedding, AllToAll, Data Flow',
    reading='10 分钟', reading_en='10 min',
    summary='查表请求最初按特征排列，通信时却要按目标进程发送。动画配合可运行代码追踪四个进程中的四十次请求，说明分桶与接收端重排如何让数据到达正确位置。',
    summary_en='Lookup requests begin grouped by feature but must be sent by destination. An animation and runnable example trace forty requests across four ranks through both layout changes.',
    series='torchrec', series_title='TorchRec', series_title_en='TorchRec', series_order='3',
)

PIPELINE_CODE = '''from keyflow_example import (exchange, flatten, lengths_segments, make_inputs,
                             recat, segment_lengths, stable_bucketize)

inputs = make_inputs()
send = [stable_bucketize(keys) for keys in inputs]
send_lengths = [segment_lengths(segments) for segments in send]
send_splits = [[len(segment) for segment in segments] for segments in send]

# Three exchanges: segment sizes first, then lengths and values.
recv_splits = exchange(send_splits)
recv_lengths = [flatten(blocks) for blocks in
                exchange([lengths_segments(lengths) for lengths in send_lengths])]
recv_values = [flatten(segments) for segments in exchange(send)]

lookup_lengths, lookup_values, _ = recat(recv_lengths[0], recv_values[0])
print(send_lengths[0])  # [3, 1, 1, 1, 1, 0, 1, 1]
print(recv_splits[0])   # [4, 2, 1, 3]
print(recv_lengths[0])  # [3, 1, 1, 1, 0, 1, 2, 1]
print(lookup_lengths)   # [3, 1, 0, 2, 1, 1, 1, 1]
print([key.occurrence for key in lookup_values])'''


def table(headers, rows, caption):
    return '<div class="keyflow-table" tabindex="0" role="region" aria-label="' + escape(caption, quote=True) + '"><table><caption>' + caption + '</caption><thead><tr>' + ''.join(f'<th scope="col">{h}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{v}</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def key_label(uid, include_rank=True):
    rank, feature, index = map(int, uid.split(':'))
    return f'<span class="keyflow-key">' + (f'R{rank}:' if include_rank else '') + f'{"AB"[feature]}[{index}]</span>'


def pair(lengths, segment):
    return '<code>' + str(lengths[2*segment:2*segment+2]) + '</code>'
def chunks(values, size):
    return ' '.join('<code>' + str(values[i:i+size]) + '</code>' for i in range(0, len(values), size))
def calls(lang):
    zh = lang == 'zh'
    sent = EXAMPLE['packed_splits'][0]
    got = [n for triple in zip(EXAMPLE['lengths_splits']['recv'][0], EXAMPLE['recv_splits'][0], EXAMPLE['stride_per_rank'][0]) for n in triple]
    ids = (lambda counts: '、'.join(map(str, counts)) + ' 个 ID') if zh else (lambda counts: ', '.join(map(str, counts)) + ' IDs')
    rows = [
        ['1', 'splits', chunks(sent, 3), chunks(got, 3), '每个来源的段长与批大小' if zh else 'Segment sizes and batch size of every source'],
        ['2', '<code>lengths</code>', chunks(EXAMPLE['lengths']['send'][0], 2), chunks(EXAMPLE['lengths']['recv'][0], 2), '段内各特征的 key 数' if zh else 'Keys per feature inside each segment'],
        ['3', '<code>values</code>', ids(EXAMPLE['send_splits'][0]), ids(EXAMPLE['recv_splits'][0]), '查表用的 ID' if zh else 'The IDs to look up'],
    ]
    return table(['顺序', '张量', 'rank 0 发给 rank 0–3', 'rank 0 收自 rank 0–3', '接收端由此得知'] if zh else ['Call', 'Tensor', 'Rank 0 sends to ranks 0–3', 'Rank 0 receives from ranks 0–3', 'What the receiver learns'], rows,
                 'rank 0 参与的三次 AllToAll；splits 的每组是 [lengths 个数, values 个数, 批大小]' if zh else 'The three AllToAll calls on rank 0; each splits group is [lengths count, values count, batch size]')
def inputs(lang):
    rows = [[f'Rank {r}', '<code>'+str(row['A'])+'</code>', '<code>'+str(row['B'])+'</code>', str(len(row['A'])+len(row['B']))] for r,row in enumerate(EXAMPLE['input_owners'])]
    return table(['来源', '特征 A 的 owner', '特征 B 的 owner', '请求数'] if lang=='zh' else ['Source', 'Owners for feature A', 'Owners for feature B', 'Requests'], rows,
                 '图中的四份输入；数组值表示 owner rank' if lang=='zh' else 'The four inputs; array values identify owner ranks')


def send_rank0(lang):
    rows=[];start=0
    for dst,count in enumerate(EXAMPLE['send_splits'][0]):
        keys=EXAMPLE['send_buffers'][0][start:start+count]
        rows.append([str(dst), ', '.join(key_label(key,False) for key in keys), pair(EXAMPLE['lengths']['send'][0], dst), str(count)])
        start+=count
    return table(['目标 rank', 'rank 0 发送的请求', '<code>lengths</code>', '<code>values</code> 个数'] if lang=='zh' else ['Destination', 'Requests sent by rank 0', '<code>lengths</code>', '<code>values</code> count'], rows,
                 'rank 0 的发送缓冲区' if lang=='zh' else 'The send buffer on rank 0')


def counts(lang):
    rows=[[f'Rank {src}',*map(str,row),str(sum(row))] for src,row in enumerate(EXAMPLE['send_counts'])]
    rows.append(['接收总数' if lang=='zh' else 'Received total',*[str(sum(row[dst] for row in EXAMPLE['send_counts'])) for dst in range(4)],'40'])
    return table(['来源 → 目标','Rank 0','Rank 1','Rank 2','Rank 3','发送总数'] if lang=='zh' else ['Source → destination','Rank 0','Rank 1','Rank 2','Rank 3','Sent total'], rows,
                 'send_counts[src][dst]：每段包含多少次请求' if lang=='zh' else 'send_counts[src][dst]: requests in each segment')


def recv_rank0(lang):
    rows=[[f'Rank {src}', ', '.join(key_label(key) for key in keys),pair(EXAMPLE['lengths']['recv'][0], src),str(len(keys))] for src,keys in enumerate(EXAMPLE['rank0']['recv_segments_by_source'])]
    return table(['来源', 'rank 0 收到的请求', '<code>lengths</code>', '<code>values</code> 个数'] if lang=='zh' else ['Source', 'Requests received by rank 0', '<code>lengths</code>', '<code>values</code> count'], rows,
                 '接收缓冲区按来源 rank 拼接' if lang=='zh' else 'The receive buffer concatenates segments by source rank')


def lookup_rank0(lang):
    lengths=EXAMPLE['lengths']['lookup'][0]
    rows=[[feature,', '.join(key_label(key) for key in keys),'<code>'+str(lengths[4*i:4*i+4])+'</code>',str(len(keys))] for i,(feature,keys) in enumerate(EXAMPLE['rank0']['lookup_by_feature'].items())]
    return table(['特征', '查表请求顺序', '<code>lengths</code>', '请求数'] if lang=='zh' else ['Feature', 'Lookup request order', '<code>lengths</code>', 'Count'], rows,
                 'rank 0 重排后的查表输入' if lang=='zh' else 'The regrouped lookup input on rank 0')


def arr(values):
    return '<code>' + str(list(values)) + '</code>'
def hier_keys(keys, include_rank=True):
    return ', '.join(key_label(key.occurrence, include_rank) for key in keys) or '—'
HIER_PLAYER = '<!--hier-player-->'
def hier_figure(lang):
    """The player sits between the two language blocks, so the text is cut here."""
    return HIER_PLAYER
def hier_caption(lang):
    return ('<p>实心格是 key，格内数字标的是它的 owner rank，不是 key 的值；每个 rank 的输入已经是 unique 的。描边格是索引或计数，数字就是真实取值；方括号标签是 chunk 头。'
            '飞行中的 key 是一份拷贝，出发处的格子保留不动。图中的标题同样可以点击：点 Unique KJT、key_stage、Owner window 或 Owner KJT + row_map 跳到对应的时刻，点三个步骤标题播放这一步。</p>'
            if lang == 'zh' else
            '<p>Filled cells are keys, and their digits mark the owner rank, not the key\'s value; each rank\'s input is already unique. Outlined cells are indices or counts and show real values. Bracketed tags are chunk headers. '
            'A key in flight is a copy, and the cell it left stays in place. The titles are clickable here too: Unique KJT, key_stage, Owner window and Owner KJT + row_map jump to that moment, and the three step titles play their step.</p>')
def hier_compare(lang):
    zh = lang == 'zh'
    rows = [
        ['通信', '三次 AllToAll，由 CPU 发起；发 <code>lengths</code> 和 <code>values</code> 之前要先把 splits 读回主机', '每个 peer 两次 GIN put：count message 和 key 记录，都在 GPU kernel 里发起；一次调用只在第二次 wait 时同步一次主机'],
        ['发送端', '分桶生成一份按目标排好的 <code>values</code> 和 <code>lengths</code>', '分桶只写 <code>inv</code> 和 <code>bucket_feature_of_row</code>，每个 key 共 8 字节；push 时按 <code>inv</code> 取 key，直接写进 window'],
        ['接收端', 'recat 把 <code>lengths</code> 和 <code>values</code> 重排成新的张量', 'KJT 一次写成；行的顺序交给 <code>row_map</code>，lookup 按它落位'],
    ] if zh else [
        ['Communication', 'Three AllToAll calls issued by the CPU; the splits are read back to the host before <code>lengths</code> and <code>values</code> go out', 'Two GIN puts per peer, a count message and the key records, both issued inside GPU kernels; a call syncs with the host once, at its second wait'],
        ['Sender', 'Bucketizing builds a copy of <code>values</code> and <code>lengths</code> ordered by destination', 'Bucketizing writes only <code>inv</code> and <code>bucket_feature_of_row</code>, 8 bytes per key in all; the push reads keys through <code>inv</code> straight into the window'],
        ['Receiver', 'Recat permutes <code>lengths</code> and <code>values</code> into new tensors', 'The KJT is written once; <code>row_map</code> carries the row order and the lookup places rows by it'],
    ]
    return table(['环节', 'TorchRec', 'hierarchical'] if zh else ['Stage', 'TorchRec', 'hierarchical'], rows,
                 '同一批 key 的 input dist：两种实现的差别' if zh else 'Input dist of the same keys: how the two implementations differ')
def hier_plan(lang):
    zh = lang == 'zh'
    fwd, bwd, owner = HIER['plans'][0]['fwd'], HIER['plans'][0]['bwd'], HIER['owners'][0]
    chunks = ' '.join('<code>(' + ', '.join(str(c[k]) for k in ('owner_node', 'key_lo', 'keys', 'pulls', 'start', 'end', 'round')) + ')</code>' for c in fwd['chunks'])
    fwd_chunks = ' '.join('<code>(' + ', '.join(str(c[k]) for k in ('record_lo', 'record_hi', 'start', 'end')) + ')</code>' for c in fwd['fwd_chunks'])
    groups = lambda rows: ' '.join(f'n{node}{arr(row)}' for node, row in enumerate(rows) if node)
    R, P, O = ('requester', 'proxy', 'owner')
    both, f_only, b_only = ('两者', 'FwdPlan', 'BwdPlan') if zh else ('both', 'FwdPlan', 'BwdPlan')
    rows = [
        ['<code>offset_per_bucket</code>', both, R, arr(fwd['offset_per_bucket']), '分桶后每个 owner 的行从哪里开始' if zh else 'Where each owner\'s bucketized rows start'],
        ['<code>inv</code>', both, R, arr(fwd['inv']), '分桶后的第 row 行是 KJT 的第几个 key' if zh else 'The KJT key that bucketized row <code>row</code> is'],
        ['<code>src</code>', f_only, R, arr(fwd['src']), 'forward 从哪一行读这个 key 的 embedding' if zh else 'The row the forward reads this key\'s embedding from'],
        ['<code>dst</code>', b_only, R, arr(bwd['dst']), 'backward 把这一行的梯度写到哪里' if zh else 'Where the backward writes this row\'s gradient'],
        ['<code>push_order</code>', both, R, arr(fwd['push_order']), '发往其他节点的行，按 chunk 排好的收发顺序' if zh else 'Its rows for other nodes, in chunk order'],
        ['<code>push_order_off</code>', f_only, R, arr(fwd['push_order_off']), '每个 proxy 的行在 <code>push_order</code> 中的起点' if zh else 'Where each proxy\'s rows start in <code>push_order</code>'],
        ['<code>proxy_num_chunks</code>', f_only, R, arr(fwd['proxy_num_chunks']), '本节点每个 proxy 的 chunk 数' if zh else 'Chunks of each same-node proxy\'s stream'],
        ['<code>proxy_ends</code>', both, R, arr(fwd['proxy_ends']), '每个 chunk 的结束行，最后一项是整条 stream 的结束行' if zh else 'Each chunk\'s end row; the last entry is the stream\'s end'],
        ['<code>proxy_push_tables</code>', both, R, arr(fwd['proxy_push_tables']), '每个 chunk 的行在 <code>push_order</code> 中的起点' if zh else 'Where each chunk\'s rows start in <code>push_order</code>'],
        ['<code>remote_task_offsets</code>', both, R, arr(fwd['remote_task_offsets']), '每个 chunk 之前的任务数，每个任务 32 行' if zh else 'Tasks before each chunk, 32 rows a task'],
        ['<code>num_chunks</code>', both, P, f'<code>{fwd["num_chunks"]}</code>', 'stream 中的 chunk 数' if zh else 'Chunks of its stream'],
        ['<code>chunks</code>', both, P, chunks, '按 stream 顺序的 chunk：<code>owner_node, key_lo, keys, pulls, start, end, round</code>' if zh else 'Chunks in stream order: <code>owner_node, key_lo, keys, pulls, start, end, round</code>'],
        ['<code>chunk_offset_per_bucket</code>', both, P, arr(fwd['chunk_offset_per_bucket']), '每个 owner 节点的 chunk 在 <code>chunk_inv</code> 中的起点' if zh else 'Where each owner node\'s chunks start in <code>chunk_inv</code>'],
        ['<code>chunk_inv</code>', both, P, arr(fwd['chunk_inv']), '按 owner 节点排列的 chunk 编号' if zh else 'Chunk numbers grouped by owner node'],
        ['<code>node_offset_per_bucket</code>', both, P, arr(fwd['node_offset_per_bucket']), '每个 owner 节点的第一个 node-unique key' if zh else 'First node-unique key of each owner node'],
        ['<code>node_length_per_bucket</code>', f_only, P, arr(fwd['node_length_per_bucket']), '发往每个 owner 节点的 node-unique key 数' if zh else 'Node-unique keys for each owner node'],
        ['<code>reduce_task_offsets</code>', b_only, P, arr(bwd['reduce_task_offsets']), '每个 chunk 之前的 reducer 任务数，每个任务 32 个 key' if zh else 'Reducer tasks before each chunk, 32 keys a task'],
        ['<code>node_exp_off</code>', b_only, P, arr(bwd['node_exp_off']), '每个 node-unique key 之前的行数' if zh else 'Rows before each node-unique key'],
        ['<code>bwd_groups</code>', b_only, P, groups(bwd['bwd_groups']), '本 rank 的 key 在每个 owner 那里的 group run' if zh else 'Group runs of its keys at each owner'],
        ['<code>fwd_chunks</code>', f_only, O, fwd_chunks, 'forward 要 put 的 chunk：<code>record_lo, record_hi, start, end</code>，按来源节点排列' if zh else 'Chunks its forward puts: <code>record_lo, record_hi, start, end</code>, by source node'],
        ['<code>fwd_chunk_offsets</code>', f_only, O, arr(fwd['fwd_chunk_offsets']), '每个来源节点的 chunk 在 <code>fwd_chunks</code> 中的起点' if zh else 'Where each source node\'s chunks start in <code>fwd_chunks</code>'],
        ['<code>fwd_groups</code>', f_only, O, groups(fwd['fwd_groups']), '每个来源节点的记录的 group run：起止和 shift' if zh else 'Group runs of each source node\'s records: bounds and shift'],
        ['<code>node_length_per_source</code>', b_only, O, arr(bwd['node_length_per_source']), '来自每个来源节点的 key 数' if zh else 'Keys from each source node'],
        ['<code>num_recv</code>', b_only, O, f'<code>{bwd["num_recv"]}</code>', 'owner 的 lookup 输出行数' if zh else 'Rows of the owner\'s lookup output'],
        ['<code>row_map</code>', ('随 KJT 返回' if zh else 'returned with the KJT'), O, arr(owner['row_map']), 'KJT 第 i 个 key 在所属 group 切片中的行号' if zh else 'Row of KJT key i in its group\'s slice'],
    ]
    for row in rows:  # names and roles stay on one line
        row[0], row[1], row[2] = (f'<span class="keyflow-key">{cell}</span>' for cell in row[:3])
    return table(['字段', '所属 plan', '身份', 'rank 0 的值', '含义'] if zh else ['Field', 'Plan', 'Role', 'Value on rank 0', 'Meaning'], rows,
                 'rank 0 的 FwdPlan、BwdPlan 和 row_map；index dedup 的 fan-out 表未列出' if zh else 'FwdPlan, BwdPlan and row_map on rank 0; index dedup\'s fan-out tables are not listed')
def hier_window(lang):
    zh = lang == 'zh'
    pushed, proxy, owner, messages = (HIER[name][0] for name in ('pushed', 'proxies', 'owners', 'messages'))
    tag = lambda c: '<code>[' + f'{c["record_lo"]}, {c["record_hi"]} | {c["start"]}, {c["end"]}' + ']</code>'
    stage = '；'.join(f'→ n{node}：{tag(part["chunks"][0])} {hier_keys(part["records"], False)}' for node, part in proxy['key_stage'].items())
    rail = '；'.join(f'← n{node} @{owner["slice_in"][node]}：{tag(part["chunks"][0])} {hier_keys(part["records"])}' for node, part in owner['rail_keys'].items())
    if not zh:
        stage, rail = stage.replace('；', '; ').replace('：', ': '), rail.replace('；', '; ').replace('：', ': ')
    first = messages[1]
    rows = [
        ['<code>node_keys</code> own part', hier_keys(pushed['own_part'], False), '自己拥有的 key，按特征排列' if zh else 'Keys it owns, feature by feature'],
        ['<code>node_keys</code> remote part', hier_keys([key for *_, key in pushed['remote_part']], False), '发往其他节点的 key，按 owner 节点、特征排列' if zh else 'Keys for other nodes, by owner node and feature'],
        ['<code>node_bucket_feature_of_row</code>', arr(pushed['node_bucket_feature_of_row']), 'remote part 每个 key 的 owner 节点 × 特征数 + 特征' if zh else 'Owner node × feature count + feature of each remote key'],
        ['<code>remote_map</code>', ' '.join(f'{name} {arr(values)}' for name, values in proxy['remote_map'].items()), '每个 remote key 在 <code>proxy_rows</code> 的行、自己的槽位、在推送顺序中的位置' if zh else 'Each remote key\'s row in <code>proxy_rows</code>, its own slot, and its place in the push order'],
        ['<code>proxy_header</code>', arr(proxy['proxy_header']), 'chunk 数、stream 结束行、各 chunk 的结束行、requester 的 push table' if zh else 'Chunk count, stream end, each chunk\'s end, the requester\'s push table'],
        ['<code>key_stage</code>', stage, '每个 owner 节点一段：chunk 头加 key 记录' if zh else 'A slice per owner node: chunk header, then key records'],
        ['count message', ('头部 ' if zh else 'header ') + arr(first['header']) + ('；尾部 ' if zh else '; parts ') + ' '.join(f'n{peer}{arr(message["part"])}' for peer, message in messages.items()),
         '头部：两个 need、own part 的 key 数、每个 owner 节点的 chunk 数、每个 owner 节点的 key 数；尾部：该 peer 每个特征的 key 数' if zh else 'Header: two needs, keys of its own part, chunks per owner node, keys per owner node. Part: the peer\'s keys per feature'],
        ['<code>rail_keys</code>', rail, '其他节点 put 进来的段，按来源节点排列，@ 后是字节偏移' if zh else 'Slices put by the other nodes, in source node order; the byte offset follows @'],
    ]
    return table(['buffer', 'rank 0 的内容', '说明'] if zh else ['Buffer', 'Contents on rank 0', 'Notes'], rows,
                 'rank 0 的 window：前七行由 rank 0 写，最后一行由其他节点写入' if zh else 'Rank 0\'s window: rank 0 writes the first seven rows, the other nodes write the last')
def code(text):
    return '<pre><code class="language-python">'+escape(text)+'</code></pre>'


def bucketize_code(lang):
    source=(ASSETS/'keyflow_example.py').read_text();lines=source.splitlines()
    fn=next(node for node in ast.parse(source).body if isinstance(node,ast.FunctionDef) and node.name=='stable_bucketize')
    return code('\n'.join(lines[fn.lineno-1:fn.end_lineno]))


def expand(lang):
    body=(ROOT/f'scripts/content/embedding-comm-viz.{lang}.html').read_text()
    blocks={'hier-figure':hier_figure,'hier-compare':hier_compare,'hier-plan':hier_plan,'hier-window':hier_window,'calls':calls,'inputs':inputs,'send-rank0':send_rank0,'counts':counts,'recv-rank0':recv_rank0,'lookup-rank0':lookup_rank0,'bucketize-code':bucketize_code,'pipeline-code':lambda _:code(PIPELINE_CODE)}
    body=re.sub(r'\{\{([\w-]+)\}\}',lambda m:blocks[m[1]](lang),body)
    assert not re.search(r'\{\{[\w-]+\}\}',body)
    return body


ICONS = {
    'previous': '<path d="M18 6v12l-9-6z" fill="currentColor"/><path d="M6.5 6v12"/>',
    'play': '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/>',
    'pause': '<path d="M9 6v12M15 6v12" stroke-width="2.6"/>',
    'next': '<path d="M6 6v12l9-6z" fill="currentColor"/><path d="M17.5 6v12"/>',
    'stop': '<rect x="6.5" y="6.5" width="11" height="11" rx="1.5" fill="currentColor"/>',
    'reverse': '<path d="M8 4 4 8l4 4"/><path d="M4 8h16"/><path d="m16 12 4 4-4 4"/><path d="M20 16H4"/>',
    'loop': '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
    'zoom': '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/><path d="M11 8.5v5M8.5 11h5"/>',
    'expand': '<path d="M8 3.5H5.5a2 2 0 0 0-2 2V8"/><path d="M16 3.5h2.5a2 2 0 0 1 2 2V8"/><path d="M8 20.5H5.5a2 2 0 0 1-2-2V16"/><path d="M16 20.5h2.5a2 2 0 0 0 2-2V16"/>',
    'shrink': '<path d="M3.5 8H6a2 2 0 0 0 2-2V3.5"/><path d="M20.5 8H18a2 2 0 0 1-2-2V3.5"/><path d="M3.5 16H6a2 2 0 0 1 2 2v2.5"/><path d="M20.5 16H18a2 2 0 0 0-2 2v2.5"/>',
    'download': '<path d="M12 4v11"/><path d="m7.5 10.5 4.5 4.5 4.5-4.5"/><path d="M5 20h14"/>',
    'close': '<path d="m6 6 12 12M18 6 6 18"/>',
}


def icon(*names):
    return ''.join(f'<svg class="keyflow-i keyflow-i-{name}" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>' for name in names)


def button(hook, label, icons, extra=''):
    """Icon-only control; player.js fills in the localized name and tooltip."""
    name = f' data-label="{label}"' if label else ''
    return f'<button type="button" class="keyflow-button" data-{hook} data-needs-svg{name}{extra} disabled>{icon(*icons)}</button>'


KEYFLOW = dict(svg='rowwise-keyflow-animated.svg', version=9, name='embedding-keyflow', aspect='2070 / 1010', duration='19.2',
               title_zh='Embedding key 数据流', title_en='Embedding key data flow',
               phases_zh='分桶|AllToAll|按特征重排|完成', phases_en='Bucketize|AllToAll|Recat|Complete')
HIER_INPUT = dict(svg='hier-input-dist.svg', version=4, name='hier-input-dist', aspect='2150 / 1164', duration='20',
                  title_zh='DynamicEmb hierarchical input dist 的数据流', title_en='Data flow of the DynamicEmb hierarchical input dist',
                  phases_zh='分桶与 push|GIN put|owner 建表|完成', phases_en='Bucketize and push|GIN put|Owner tables|Complete')
def player(figure):
    attrs = ' '.join(f'data-{key.replace("_", "-")}="{escape(str(figure[key]), quote=True)}"' for key in ('name', 'title_zh', 'title_en', 'phases_zh', 'phases_en'))
    clock = f'0.00 / {float(figure["duration"]):.2f} s'
    width, height = map(int, figure['aspect'].split(' / '))
    ratio = int(width / height * 1000) / 1000  # rounded down, so the fitted height never passes the cap
    speeds = ''.join(f'<option value="{value}"{" selected" if value == "1" else ""}>{value}×</option>' for value in ('0.25', '0.5', '1', '1.5', '2', '4'))
    return f"""<section class="keyflow-player" data-keyflow-player data-src="./{figure['svg']}?v={figure['version']}" {attrs} data-ready="false" data-exporting="false" aria-label="{figure['title_en']}" style="--keyflow-aspect: {figure['aspect']}; --keyflow-ratio: {ratio}">
<div class="keyflow-viewport" data-viewport tabindex="0" role="region" aria-label="{figure['title_zh']}">
<div class="keyflow-loading" data-loading role="status">正在加载动画…</div><div class="keyflow-svg-host" data-svg-host></div></div>
<div class="keyflow-bar" data-controls role="group" aria-label="动画播放控制">
<div class="keyflow-group">{button('previous', 'previous', ['previous'])}{button('play', '', ['play', 'pause'], ' aria-pressed="false"')}{button('next', 'next', ['next'])}{button('stop', 'stop', ['stop'])}</div>
<div class="keyflow-track"><div class="keyflow-scrubber"><span class="keyflow-ticks" data-ticks aria-hidden="true"></span><input type="range" data-scrubber data-needs-svg data-label="timeline" min="0" max="{figure['duration']}" step="0.001" value="0" disabled></div><output class="keyflow-time" data-time>{clock}</output></div>
<div class="keyflow-group keyflow-options"><select class="keyflow-speed" data-speed data-needs-svg data-label="speed" disabled>{speeds}</select>{button('reverse', 'reverse', ['reverse'], ' aria-pressed="false"')}{button('loop', 'loop', ['loop'], ' aria-pressed="false"')}<span class="keyflow-gap" aria-hidden="true"></span>{button('zoom', 'zoom', ['zoom'], ' aria-pressed="false"')}{button('fullscreen', '', ['expand', 'shrink'])}
<div class="keyflow-menu" data-menu>{button('export', 'export', ['download'], ' aria-haspopup="menu" aria-expanded="false"')}
<div class="keyflow-menu-list" data-menu-list role="menu" hidden>
<button type="button" role="menuitem" data-png>PNG<small data-i18n="frame">当前帧</small></button>
<button type="button" role="menuitem" data-gif="1035">GIF<small>1035 px</small></button>
<button type="button" role="menuitem" data-gif="1440">GIF<small>1440 px</small></button>
<a role="menuitem" href="../assets/torchrec/embedding-comm-viz/{figure['svg']}" download>SVG<small data-i18n="original">原图</small></a>
</div></div></div>
</div>
<div class="keyflow-notice" data-notice hidden><progress data-progress max="1" value="0" aria-label="GIF export progress" hidden></progress><span data-export-status role="status" aria-live="polite"></span><button type="button" class="keyflow-button" data-cancel data-label="cancel" hidden>{icon('close')}</button></div>
<span class="keyflow-sr" data-stage role="status" aria-live="polite"></span>
<noscript><p>启用 JavaScript 可播放及导出；下方文字与表格完整展示本例数据。Enable JavaScript for playback and export; the tables below contain the complete example.</p></noscript>
</section>"""


def chapters():
    """Sections 2 to 6. The second player is one element between the language blocks."""
    zh, en = (expand(lang).split(HIER_PLAYER) for lang in ('zh', 'en'))
    assert len(zh) == len(en) == 2
    block = lambda lang, html: f'<div class="lang-{lang}">{html}</div>'
    return (block('zh', zh[0]) + block('en', en[0]) + player(HIER_INPUT)
            + block('zh', hier_caption('zh') + zh[1]) + block('en', hier_caption('en') + en[1]))
def main():
    zh_length=sum(.5 if ord(c)<128 else 1 for c in META['summary']);en_length=len(META['summary_en'].split())
    assert 50<=zh_length<=80 and 20<=en_length<=30,(zh_length,en_length)
    for key in ('summary','summary_en'):assert not any(c in META[key] for c in '&<>"\'')
    metadata='\n'.join(f'<meta name="post:{key}" content="{escape(value,quote=True)}">' for key,value in META.items())
    html='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>embedding comm viz</title>
'''+metadata+'''
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3"><link rel="stylesheet" href="../assets/torchrec/embedding-comm-viz/style.css?v=7">
<script src="../lang-toggle.js?v=post-toc-3" defer></script><script type="module" src="../assets/torchrec/embedding-comm-viz/player.js?v=11"></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>'''+render_series_nav(META,ROOT/'posts')+'''</aside><main class="content embedding-comm-article">
<h1>embedding comm viz</h1>
<div class="lang-zh"><p class="lead">同一批 embedding 查表请求，在输入、发送和接收缓冲区中有不同的排列顺序。这个四 rank、两特征的例子逐个追踪 40 次请求，展示按目标分桶、AllToAll 交付和按特征重排的全过程。</p><h2 id="zh-player">1. 动画播放器</h2></div>
<div class="lang-en"><p class="lead">The same embedding lookup requests appear in different orders across input, send, and receive buffers. This four-rank, two-feature example tracks all 40 occurrences through destination bucketing, AllToAll delivery, and feature regrouping.</p><h2 id="en-player">1. Animation player</h2></div>
'''+player(KEYFLOW)+'''<div class="lang-zh"><div class="keyflow-legend"><span>表 A / 特征 A</span><span class="keyflow-b">表 B / 特征 B</span></div><p>实心格是一次查表请求，数字表示 owner rank；描边小格是 <code>lengths</code>。分桶时，Send buffer 旁的 <code>lengths</code> 随 key 落位计数，全部落位后出现 <code>splits</code>。AllToAll 分三步播放：先是 <code>splits</code> 逐项沿路由线传到对端，接收端据此分配 Recv buffer，灰色空槽这时才出现；然后是 <code>lengths</code>，最后才是 key。Recat 时 <code>lengths</code> 和 key 一起重排。图中的标题可以点击：点 Input keys、Send buffer、Recv buffer 或 Lookup keys，跳到对应的布局；点 1. Bucketize、2. AllToAll 或 3. Recat，播放这一步并停在它产生的布局上。动画结束时四列格子同时填满，可以对照同一次请求在四种布局中的位置。也可以拖动时间条查看任意时刻；小屏幕可切换到原图尺寸并滚动查看。</p></div>
<div class="lang-en"><div class="keyflow-legend"><span>Table A / Feature A</span><span class="keyflow-b">Table B / Feature B</span></div><p>A filled cell is one lookup request, and its digit identifies the owner rank. Outlined cells are <code>lengths</code> entries. During bucketizing, the <code>lengths</code> beside the send buffer count up as keys land, and the <code>splits</code> row appears once every key is in place. AllToAll plays as three calls: every <code>splits</code> entry travels along its route to the peer, and the receiver allocates its buffers from them, which is when the grey slots appear. The <code>lengths</code> cells follow, and the keys go last. Recat moves <code>lengths</code> together with the keys. The titles in the figure are clickable: Input keys, Send buffer, Recv buffer and Lookup keys jump to that layout, while 1. Bucketize, 2. AllToAll and 3. Recat play the step and stop on the layout it produces. The animation ends with all four layouts filled, so one request can be compared across them. You can also scrub to any time. On small screens, switch to the original size and scroll to inspect the diagram.</p></div>
'''+chapters()+'</main></div></body></html>\n'
    path=ROOT/'posts/embedding-comm-viz.html';path.write_text(html)
    print(f'Built {path.relative_to(ROOT)}; summary lengths: {zh_length:g}, {en_length}')


if __name__=='__main__':main()
