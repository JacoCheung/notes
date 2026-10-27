#!/usr/bin/env python3
"""Build the bilingual map-style DataLoader article and inline SVG figures."""
import ast
from html import escape
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
REV = 'ba56102387ef21a3b04b357e5b183d48f0afefc7'
BASE = f'https://github.com/pytorch/pytorch/blob/{REV}/torch/utils/data/'
SOURCES = {
    'dataset': ('dataset.py', 'L39-L62', 'Dataset'),
    'construct': ('dataloader.py', 'L355-L408', 'Sampler / BatchSampler / collate_fn'),
    'iterator': ('dataloader.py', 'L481-L495', 'DataLoader.__iter__'),
    'batch': ('sampler.py', 'L285-L348', 'BatchSampler'),
    'random': ('sampler.py', 'L104-L195', 'SequentialSampler / RandomSampler'),
    'single': ('dataloader.py', 'L766-L794', '_SingleProcessDataLoaderIter'),
    'fetch': ('_utils/fetch.py', 'L46-L55', '_MapDatasetFetcher.fetch'),
    'collate': ('_utils/collate.py', 'L118-L272', 'collate / torch.stack'),
    'default': ('_utils/collate.py', 'L337-L398', 'default_collate'),
    'spawn': ('dataloader.py', 'L1130-L1212', 'Workers / pin-memory thread'),
    'prefetch': ('dataloader.py', 'L1230-L1270', 'Prefetch initialization'),
    'dispatch': ('dataloader.py', 'L1518-L1556', 'Task dispatch / replenishment'),
    'order': ('dataloader.py', 'L1458-L1516', 'Ordered result delivery'),
    'worker': ('_utils/worker.py', 'L313-L369', 'Worker task loop'),
    'seed': ('_utils/worker.py', 'L255-L290', 'Worker RNG initialization'),
    'info': ('_utils/worker.py', 'L101-L130', 'get_worker_info'),
    'pin': ('_utils/pin_memory.py', 'L18-L63', 'Pin-memory thread'),
    'dist': ('distributed.py', 'L66-L150', 'DistributedSampler'),
}

def source(key, label=None):
    path, lines, title = SOURCES[key]
    return f'<a href="{BASE}{path}#{lines}">{escape(label or title)}</a>'

DEMO = (ROOT / 'assets/pytorch-internals/dataloader-demo.py').read_text()
NODES = {node.name: ast.get_source_segment(DEMO, node) for node in ast.parse(DEMO).body
         if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
SNIPPETS = {
    'base': 'import torch\nfrom torch.utils.data import Dataset, Sampler, BatchSampler, DataLoader, get_worker_info\n\nORDER = [3, 0, 4, 1, 2]\n\n' + NODES['FiveSamples'] + '\n\n' + NODES['FixedOrder'] + '''

if __name__ == "__main__":
    loader = DataLoader(
        FiveSamples(),
        batch_sampler=BatchSampler(FixedOrder(), batch_size=2, drop_last=False),
        num_workers=0,
    )
    for batch in loader:
        print(batch["index"].tolist(), batch["x"].tolist())''',
    'concept': '''# Conceptual execution with automatic batching, num_workers=0,
# and a Dataset without __getitems__.
for indices in batch_sampler:
    samples = [dataset[index] for index in indices]
    batch = collate_fn(samples)
    yield batch''',
    'workers': '''# Use the same FiveSamples / FixedOrder definitions.
if __name__ == "__main__":
    loader = DataLoader(
        FiveSamples(),
        batch_sampler=BatchSampler(FixedOrder(), batch_size=2, drop_last=False),
        num_workers=2,             # Change to 1 for one subprocess.
        multiprocessing_context="spawn",
        prefetch_factor=2,
        in_order=True,
    )
    for batch in loader:
        print(batch["index"].tolist(), batch["worker"].tolist())''',
    'ragged': 'from torch.nn.utils.rnn import pad_sequence\nfrom torch.utils.data import default_collate\n\n' + NODES['RaggedSamples'] + '\n\n' + NODES['pad_collate'],
    'bulk': NODES['BulkSamples'],
    'ddp': NODES['run_ddp'],
    'cuda': '''# The training/rank process performs H2D, not a DataLoader worker.
for batch in loader:  # loader has pin_memory=True on a CUDA system
    x = batch["x"].to(device, non_blocking=True)
    y = batch["y"].to(device, non_blocking=True)
    prediction = model(x)''',
}

def sequence(name, lang, actors, steps, spans):
    width=1000; top=140; gap=80; height=top+len(steps)*gap+32
    xs=[100+i*800/(len(actors)-1) for i in range(len(actors))]
    marker=f'{lang}-{name}-arrow'
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{lang}-{name}-title">',
           f'<title id="{lang}-{name}-title">{escape(name)}: process and call sequence</title>',
           f'<defs><marker id="{marker}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="var(--diagram-rule)"/></marker></defs>',
           f'<rect width="1000" height="{height}" fill="var(--diagram-bg)"/>']
    for x, actor in zip(xs,actors):
        parts.append(f'<path d="M{x} 96 V{height-20}" stroke="var(--diagram-rule)" stroke-width="1.5" stroke-dasharray="5 5" opacity=".8"/>')
        parts.append(f'<rect x="{x-88}" y="25" width="176" height="70" rx="4" fill="var(--diagram-fill)" stroke="var(--diagram-rule)" stroke-width="1.7"/>')
        for i,line in enumerate(actor.split('|')):
            parts.append(f'<text x="{x}" y="{53+i*22}" font-size="15" font-weight="600" text-anchor="middle">{escape(line)}</text>')
    for actor,start,end in spans:
        parts.append(f'<rect x="{xs[actor]-7}" y="{top+start*gap-8}" width="14" height="{(end-start)*gap+20}" fill="var(--diagram-fill)" stroke="var(--diagram-rule)" stroke-width="1.8"/>')
    for i,(a,b,label,key,returned) in enumerate(steps):
        y=top+i*gap; x1=xs[a]; x2=xs[b]
        path, lines, title=SOURCES[key]
        parts.append(f'<a href="{BASE}{path}#{lines}" target="_blank" rel="noopener"><title>{escape(title)}: {escape(path)} {lines}</title>')
        dash=' stroke-dasharray="6 4"' if returned else ''
        if a==b:
            direction=-1 if x1>750 else 1
            parts.append(f'<path d="M{x1+7*direction} {y-12} h{42*direction} v24 h{-42*direction}" fill="none" stroke="var(--diagram-rule)" stroke-width="1.7" marker-end="url(#{marker})"/>')
            neighbor=xs[a+direction]
            distance=abs(neighbor-x1)
            mid=(x1+neighbor)/2
        else:
            direction=1 if x2>x1 else -1
            parts.append(f'<path d="M{x1+7*direction} {y} H{x2-9*direction}" stroke="var(--diagram-rule)" stroke-width="1.7"{dash} marker-end="url(#{marker})"/>')
            neighbor=xs[a+direction]
            mid=(x1+neighbor)/2
            distance=abs(neighbor-x1)
        lines=textwrap.wrap(label,min(38,max(12,int((distance-48)/7.7))))
        boxwidth=max(len(line) for line in lines)*7.7+16
        mid=max(boxwidth/2+15,min(985-boxwidth/2,mid))
        parts.append(f'<rect x="{mid-boxwidth/2}" y="{y-19*len(lines)-13}" width="{boxwidth}" height="{19*len(lines)+6}" fill="var(--diagram-bg)"/>')
        for j,line in enumerate(lines):
            parts.append(f'<text x="{mid}" y="{y-19*(len(lines)-j)-1}" font-size="14" text-anchor="middle">{escape(line)}</text>')
        parts.append('</a>')
    parts.append('</svg>')
    return ''.join(parts)

def ddp_diagram(lang):
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 510" role="img" aria-labelledby="{lang}-ddp-title"><title id="{lang}-ddp-title">DistributedSampler and rank-local workers</title><rect width="1000" height="510" fill="var(--diagram-bg)"/>']
    parts.append('<text x="500" y="32" text-anchor="middle" font-size="17" font-weight="600">Same seed + epoch: each rank computes the same index order</text>')
    parts.append('<text x="500" y="62" text-anchor="middle" font-size="17">[3, 0, 4, 1, 2] → pad → [3, 0, 4, 1, 2, 3*]</text>')
    for rank,x,indices,batches in [(0,30,'[3, 4, 2]','[3, 4]     [2]'),(1,520,'[0, 1, 3*]','[0, 1]     [3*]')]:
        parts.append(f'<rect x="{x}" y="95" width="450" height="365" rx="5" fill="var(--diagram-fill)" stroke="var(--diagram-rule)" stroke-width="1.8"/><text x="{x+225}" y="125" text-anchor="middle" font-size="18" font-weight="600">Rank {rank}: its own DataLoader</text>')
        rows=[('DistributedSampler: '+indices,'dist'),('BatchSampler: '+batches,'batch'),('W0: first batch  |  W1: second batch','dispatch'),('Dataset → collate_fn → rank process','fetch')]
        for i,(label,key) in enumerate(rows):
            path,lines,title=SOURCES[key];y=145+i*72
            parts.append(f'<a href="{BASE}{path}#{lines}" target="_blank" rel="noopener"><rect x="{x+18}" y="{y}" width="414" height="48" rx="3" fill="var(--diagram-bg)" stroke="var(--diagram-rule)"/><text x="{x+225}" y="{y+29}" text-anchor="middle" font-size="15">{escape(label)}</text></a>')
            if i<3:parts.append(f'<text x="{x+225}" y="{y+66}" text-anchor="middle" font-size="20">↓</text>')
    parts.append('<text x="500" y="490" text-anchor="middle" font-size="14">* padded duplicate · two workers per rank · data loading stays rank-local</text></svg>')
    return ''.join(parts)

def figure(key,lang):
    if key=='single':
        svg=sequence(key,lang,['Training loop|main process','Loader iterator|main process','BatchSampler|main process','Dataset / Fetcher|main process','collate_fn|main process'],[
            (0,1,'next(iterator)','single',False),(1,2,'next(batch_sampler)','batch',False),
            (2,1,'indices = [3, 0]','batch',True),(1,3,'fetch([3, 0])','fetch',False),
            (3,3,'dataset[3]; dataset[0]','fetch',False),(3,4,'collate_fn(samples)','fetch',False),
            (4,3,'batch: x.shape = [2, 2]','collate',True),(3,1,'return batch','single',True),
            (1,0,'yield batch 0','single',True)],[(0,0,8),(1,0,8),(2,1,2),(3,3,7),(4,5,6)])
        caption=('单进程调用序列：所有生命线都在同一个训练进程内。实心条表示调用区间；长度不是实测耗时。','Single-process calls: every lifeline belongs to the training process. Bars mark call scopes, not measured durations.')
    elif key=='workers':
        svg=sequence(key,lang,['Training loop|main process','Loader iterator|main process','Worker 0|Dataset + collate','Worker 1|Dataset + collate'],[
            (0,1,'iter(loader): start prefetch','iterator',False),
            (1,2,'queue task 0: [3, 0]','dispatch',False),(1,3,'queue task 1: [4, 1]','dispatch',False),
            (1,2,'queue task 2: [2], pending','dispatch',False),(0,1,'next(iterator)','order',False),
            (3,1,'result (1, batch1) arrives first','worker',True),(1,1,'buffer task 1; expect task 0','order',False),
            (2,1,'result (0, batch0)','worker',True),(1,0,'yield batch0: [3, 0]','order',True),
            (0,1,'next(iterator)','order',False),(1,0,'yield buffered batch1: [4, 1]','order',True),
            (0,1,'next(iterator)','order',False),(2,1,'result (2, batch2)','worker',True),(1,0,'yield batch2: [2]','order',True)
        ],[(0,0,13),(1,0,13),(2,1,7),(2,8,12),(3,2,5)])
        caption=('两个 worker，prefetch_factor=2，in_order=True。只剩三批，所以初始发出三个任务。任务 2 排在 worker 0 的队列中；图示的一次完成顺序不代表固定调度或实测耗时。','Two workers, prefetch_factor=2, in_order=True. Only three batches exist, so three tasks are initially dispatched. Task 2 queues behind task 0; the illustrated completion order is not a timing guarantee.')
    else:
        svg=ddp_diagram(lang)
        caption=('DDP 的索引分片与进程归属。上方是各 rank 独立算出的相同顺序，不是一个中央分发进程。每个 rank 的 worker ID 都从 0 开始。','DDP sharding and process ownership. The shared order is computed independently on each rank, not broadcast by a central dispatcher. Worker IDs start at zero within each rank.')
    text=caption[lang=='en'];fit='Fit width' if lang=='en' else '适应宽度'
    return f'<figure class="loader-figure"><div class="loader-toolbar"><span>{"Source-linked diagram" if lang=="en" else "图中消息可点击查看源码"}</span><span><button type="button" data-fit="fit" aria-pressed="true">{fit}</button> <button type="button" data-fit="actual" aria-pressed="false">100%</button></span></div><div class="loader-viewport" tabindex="0" role="region" aria-label="{escape(text)}">{svg}</div><figcaption>{text}</figcaption></figure>'

def lab(lang):
    en=lang=='en'
    return f'''<section class="loader-lab" data-lang="{lang}" aria-label="{'Distributed sampling experiment' if en else '分布式索引实验'}">
<p><strong>{'Experiment: two independent drop_last settings' if en else '交互实验：两层 drop_last'}</strong></p>
<p>{'Fixed teaching order: [3, 0, 4, 1, 2]. Change ranks and local batch size; this simulates index arithmetic, not live workers.' if en else '固定教学顺序为 [3, 0, 4, 1, 2]。调整 rank 数和本地 batch size，观察补齐、分片和丢弃；这里模拟索引计算，不启动真实 worker。'}</p>
<div class="loader-controls"><label>World size <select data-ranks><option>1</option><option selected>2</option><option>3</option><option>4</option></select></label><label>Batch / rank <select data-batch><option>1</option><option selected>2</option><option>3</option><option>4</option></select></label><label><input type="checkbox" data-sampler-drop>Sampler drop_last</label><label><input type="checkbox" data-batch-drop>Loader drop_last</label></div>
<p>{'Global index slots' if en else '全局索引位置'}：<code data-global>[3, 0, 4, 1, 2, 3*]</code></p>
<div class="loader-table"><table><thead><tr><th>Rank</th><th>{'Local indices' if en else '本地索引'}</th><th>{'Output batches' if en else '输出 batch'}</th><th>{'Loader drops' if en else 'Loader 丢弃'}</th></tr></thead><tbody><tr><td>0</td><td>[3, 4, 2]</td><td>[3, 4] · [2]</td><td>[]</td></tr><tr><td>1</td><td>[0, 1, 3*]</td><td>[0, 1] · [3*]</td><td>[]</td></tr></tbody></table></div><p data-summary aria-live="polite"></p><noscript><p>{'JavaScript enables the controls; the table shows the default case.' if en else '启用 JavaScript 可操作控件；上表保留默认例子。'}</p></noscript></section>'''

ZH = r'''
<h1>PyTorch DataLoader 工作原理</h1>
<p class="lead">PyTorch DataLoader 把数据集中的样本组织成训练批次。对于按索引访问的 map-style Dataset，Sampler 决定读取哪些样本，BatchSampler 决定如何分批，Dataset 完成读取与处理，collate_fn 将样本组装成模型输入。本文以五个样本为例，说明这条路径在主进程、单个 worker、多个 worker 和 DDP 训练中的执行方式，以及预取、返回顺序和分布式分片如何配合。</p>
<aside class="loader-note"><p>本文固定分析 <a href="https://github.com/pytorch/pytorch/tree/ba56102387ef21a3b04b357e5b183d48f0afefc7">PyTorch 2.8.0</a> 的普通 map-style Dataset。序列图中的消息链接到该版本源码。<code>num_workers=0</code> 表示没有子进程，<code>num_workers=1</code> 才表示一个独立的数据加载 worker；worker 通常是进程，不是线程。</p></aside>

<h2 id="zh-components">1. 索引与批次</h2>
<h3 id="zh-contract">五个组件</h3>
<p>Map-style Dataset 建立索引到样本的映射，典型接口是 <code>dataset[index]</code>。索引不一定是整数；本文使用 <code>0…4</code>，并固定采样顺序为 <code>[3, 0, 4, 1, 2]</code>。Dataset 可以从文件解码图片、查询数据库或处理内存数据；它不负责决定本轮采样顺序。{source:dataset}</p>
<div class="loader-table"><table><thead><tr><th>组件</th><th>职责</th><th>本例</th></tr></thead><tbody>
<tr><td>Sampler</td><td>产生样本索引</td><td><code>3, 0, 4, 1, 2</code></td></tr>
<tr><td>BatchSampler</td><td>将索引分组</td><td><code>[3,0], [4,1], [2]</code></td></tr>
<tr><td>Dataset</td><td>按索引读取并处理样本</td><td><code>dataset[3]</code> 得到 x=<code>[3,30]</code>、y=1</td></tr>
<tr><td>collate_fn</td><td>将样本列表合成 batch</td><td>两个 x 堆成 shape 为 <code>[2,2]</code> 的 tensor</td></tr>
<tr><td>DataLoader / iterator</td><td>协调采样、读取、预取与交付</td><td>每次 <code>next(iterator)</code> 返回一批</td></tr>
</tbody></table></div>
<p>BatchSampler 处理的是<strong>索引列表</strong>，collate_fn 接收的是<strong>已经读出的样本列表</strong>。两者之间发生实际的数据访问。默认配置下，<code>shuffle=False</code> 对应 SequentialSampler，<code>shuffle=True</code> 对应 RandomSampler；提供 batch_size 时，DataLoader 通常再包一层 BatchSampler。{source:construct}；{source:random}</p>
<h3 id="zh-fixed-example">五个样本</h3>
<p>样本 i 的特征为 <code>[i, 10i]</code>，标签为 <code>i % 2</code>。这个 Dataset 返回确定性的内存数据，便于检查索引流向。附带的 worker 字段只用于观察执行位置：-1 表示训练进程，0、1 表示该 DataLoader 的子进程。</p>
{code:base}
<pre class="code">[3, 0] [[3.0, 30.0], [0.0, 0.0]]
[4, 1] [[4.0, 40.0], [1.0, 10.0]]
[2]    [[2.0, 20.0]]</pre>
<p>这里显式传入 batch_sampler，以便看清分组过程。使用自定义 batch_sampler 时，不再同时配置 batch_size、sampler、shuffle 或 drop_last；这些职责已由它接管。最后的 <code>[2]</code> 被保留，因为 BatchSampler 的 drop_last=False。{source:batch}</p>

<h2 id="zh-single">2. 单进程与单 worker</h2>
<h3 id="zh-main-process">主进程读取</h3>
<p>创建 DataLoader 对象主要保存配置；<code>iter(loader)</code> 创建迭代器。num_workers=0 时，<code>next(iterator)</code> 在训练进程内取出下一批索引，读取样本并执行 collate_fn。模型计算期间没有 DataLoader 子进程在后台读取下一批。{source:iterator}；{source:single}</p>
{code:concept}
<p>这是默认逐样本访问路径的等价示意。内部的 <code>_MapDatasetFetcher</code> 负责连接 Dataset 与 collate_fn；支持批量读取的 <code>__getitems__</code> 会替换列表中的逐次读取，后文单独说明。{source:fetch}</p>
{figure:single}
<h3 id="zh-one-worker">一个独立 worker</h3>
<p>num_workers=1 会创建一个子进程。主进程仍运行 Sampler 和 BatchSampler，将 <code>(任务编号, 索引列表)</code> 放进该 worker 的 index queue。Worker 对整批索引执行读取、变换和 collate_fn，再把 <code>(任务编号, batch)</code> 放入 result queue；主进程取出 batch 交给训练循环。{source:spawn}；{source:dispatch}；{source:worker}</p>
<p>这已经允许 CPU 数据准备与训练进程的工作重叠，但同一个 worker 仍按顺序处理它收到的任务。单 worker 并不会把一批中的两条样本变成两个并行读取任务。普通 map-style Dataset 的副本可以访问完整索引空间，实际读取哪些索引由主进程派发。</p>

<h2 id="zh-workers">3. 多 worker 与预取</h2>
<h3 id="zh-task-unit">整批任务分发</h3>
<p>保持前面的 Dataset、Sampler 和 batch size 不变，只把 worker 数改成 2：</p>
{code:workers}
<p>在本文版本、默认 in_order=True 的普通 map-style 路径中，初始任务轮流发给活跃 worker。这个例子中 worker 0 收到 task 0=<code>[3,0]</code> 与 task 2=<code>[2]</code>，worker 1 收到 task 1=<code>[4,1]</code>。一个任务对应一批索引，<strong>同一批通常由一个 worker 完整读取并组装</strong>。增加 worker 数是在不同批次之间并行，而不是自动把一批拆给所有 worker。{source:dispatch}</p>
<h3 id="zh-prefetch">预取窗口</h3>
<p>启用自动 batching 时，prefetch_factor 的单位是每个 worker 的批任务。两个 worker、prefetch_factor=2，初始化会尝试派发最多四个任务；本例只有三批，所以只能发出三个。较大的数据集会在交付结果后继续补充任务。这个窗口涵盖排队、执行和已完成待交付的任务，不表示内存里始终有四个已经完成的 batch。{source:prefetch}；{source:dispatch}</p>
<p>预取只提前准备未来需要的数据。若稳定状态下读取速度持续低于训练消耗速度，单纯增大窗口不能弥补吞吐差距，还会增加数据、队列和乱序结果的内存占用。Dataset 的 Python 对象、解码缓存与每个 worker 的进程开销也要另计。</p>
<h3 id="zh-order">完成顺序与交付顺序</h3>
<p>假设 dataset[3] 比其他样本慢，worker 1 的 task 1 可能先完成。默认 in_order=True 时，主进程根据<strong>任务编号</strong>缓存这个结果，等 task 0 到达后再按 0、1、2 交付。因此“按序”是按 Sampler / BatchSampler 的任务顺序，不是把样本 ID 排成 0、1、2、3、4。{source:order}</p>
{figure:workers}
<p>in_order=False 允许先交付先到达的结果，能减少慢批次造成的等待，但会改变训练看到的数据顺序。如果某类样本总是解码更快，训练前缀也可能偏向这类样本。它不保证某一种乱序；启动时间、系统调度和存储延迟都会影响结果。对顺序和可复现性有要求时，应明确保留默认设置。{source:order}</p>
<h3 id="zh-worker-state">进程状态与生命周期</h3>
<p>本文显式使用 spawn。Dataset 类、collate_fn 和 worker_init_fn 应定义在模块顶层，创建迭代器的代码放进 <code>if __name__ == "__main__":</code>，使子进程能够导入并重建这些对象。不要用不可序列化的 lambda 充当 spawn worker 的初始化函数。文件句柄和数据库连接通常应在各 worker 内按需创建。</p>
<p>默认每次创建新迭代器都会启动 worker，遍历结束后关闭。persistent_workers=True 则跨轮保留 worker 及其 Dataset 实例，减少重启开销；主进程里修改 <code>dataset.epoch</code> 并不会自动更新这些副本，worker_init_fn 也不会每轮重新执行。需要随 epoch 改变的状态必须显式传递。{source:iterator}；{source:worker}</p>
<p>采样随机性与 worker 内的数据增强随机性是两层状态。此版本在 worker 启动时初始化 PyTorch、Python random，以及可用时的 NumPy RNG；自行创建的随机生成器或其他库仍需明确管理。<code>get_worker_info()</code> 提供 worker ID、seed 和本进程 Dataset。固定采样顺序并不自动保证随机增强在不同 worker 数下完全一致。{source:seed}；{source:info}</p>

<h2 id="zh-batch">4. Batch 的组织与搬运</h2>
<h3 id="zh-collate">默认堆叠与变长补齐</h3>
<p>default_collate 会递归处理字典等结构，将同一字段的 tensor 堆叠，给结果增加 batch 维度；本例第一批的 x 为 <code>[2,2]</code>，y 为 <code>[2]</code>。它不会自动为变长 tensor 补齐。若样本 i 改为长度 i+1 的序列，第一批两条序列的长度就是 4 和 1，需要自定义 collate_fn。{source:default}；{source:collate}</p>
{code:ragged}
<p>第一批得到 <code>x=[[1,2,3,4],[1,0,0,0]]</code>、<code>lengths=[4,1]</code>。Mask 区分有效位置与 padding，避免把补入的 0 当作真实输入。使用 <code>DataLoader(RaggedSamples(), …, collate_fn=pad_collate)</code> 时，num_workers=0 在主进程执行补齐；num_workers&gt;0 在收到该批任务的 worker 内执行。</p>
<h3 id="zh-bulk">批量读取接口</h3>
<p>实现可选的 <code>Dataset.__getitems__(indices)</code> 后，fetcher 会把整批索引交给它，而不是逐次调用 __getitem__。数据库批查询、连续文件读取可以利用这个接口；返回结果仍应是按请求顺序排列的<strong>样本列表</strong>，之后依然调用 collate_fn。下面只是接口示意，列表循环本身没有带来 I/O 加速。{source:fetch}</p>
{code:bulk}
<p>若显式设置 batch_size=None 且没有 batch_sampler，则关闭自动 batching：Sampler 每次给一个 key，fetcher 取一个样本，默认使用 default_convert。此时用户提供的 collate_fn 接收单个样本，而非样本列表，不能套用本文的整批任务示意。{source:construct}；{source:fetch}</p>
<h3 id="zh-device">Pin memory 与 H2D</h3>
<p>通常让 Dataset 和 collate_fn 返回 CPU tensor。CUDA 可用且启用 <code>pin_memory=True</code> 时，DataLoader 将 batch 中的 CPU tensor 放入页锁定（page-locked）主机内存，便于高效地传到 GPU。自动 pinning 位于 <strong>collate_fn 之后、batch 返回给训练循环之前</strong>；具体执行位置取决于 num_workers。{source:single}；{source:spawn}；{source:pin}</p>
<div class="loader-table"><table><thead><tr><th>配置</th><th>读取数据、执行 collate_fn</th><th>执行自动 pin_memory</th></tr></thead><tbody>
<tr><td><code>num_workers=0</code></td><td>训练进程中调用 next 的线程，通常是主线程</td><td>同一线程，在 next 调用内同步执行</td></tr>
<tr><td><code>num_workers&gt;0</code></td><td>worker 子进程</td><td><strong>训练进程中的专用 pin-memory 线程</strong></td></tr>
</tbody></table></div>
<p>多 worker 路径中，pin-memory 线程从 worker result queue 取出已组装的 batch，完成 pinning 后放入训练进程内的 data queue。训练线程再按迭代器的交付规则取出 batch。DDP 下，每个 rank 都有自己的这条路径；pin-memory 线程不属于读取数据的 worker。{source:pin}；{source:spawn}</p>
<pre class="code">num_workers=0：
训练线程：读取 → collate_fn → pin_memory → 返回 batch

num_workers&gt;0：
worker：读取 → collate_fn → result queue
训练进程 / pin-memory 线程：result queue → pin_memory → data queue
训练进程 / 训练线程：data queue → 按交付规则返回 batch</pre>
<p>前面的两张序列图采用默认的 pin_memory=False，因此没有画出这个可选阶段。<strong>Pinned memory 仍是 CPU 内存，DataLoader 不会因此自动把 batch 送到 GPU。</strong>真正的 H2D 由训练代码中的 <code>.to(device)</code> 发起：</p>
{code:cuda}
<p><code>non_blocking=True</code> 允许异步提交搬运；H2D 与计算是否实际重叠还取决于 stream、数据依赖和硬件。同一 CUDA stream 上紧接着使用 x 的计算仍要等搬运完成。自定义 batch 类型需要实现相应的 pin_memory 支持；普通 tensor 字典可由默认逻辑递归处理。</p>

<h2 id="zh-ddp">5. DDP 中的数据读取</h2>
<h3 id="zh-ranks">Rank 与 worker</h3>
<p>DDP 通常由每张 GPU 对应一个训练进程，每个 rank 都有自己的 Dataset、DataLoader 和 worker 池。DDP 负责模型副本之间的梯度同步，<strong>不会自动切分 DataLoader 的输入</strong>；map-style 数据通常用 DistributedSampler 进行分片。<a href="https://docs.pytorch.org/docs/2.8/generated/torch.nn.parallel.DistributedDataParallel.html">DDP 官方说明</a>。</p>
<p>分片先于本地分批：各 rank 用相同 seed 和 epoch 产生同一份全局索引排列，再按 <code>indices[rank:total_size:world_size]</code> 取属于自己的位置，最后由各自的 BatchSampler 分批。DistributedSampler 在各 rank 本地计算这些索引，通常不需要每轮做一次索引广播。{source:dist}</p>
<pre class="code">全局排列： [3, 0, 4, 1, 2]
补齐到 6： [3, 0, 4, 1, 2, 3*]
rank 0：   [3,    4,    2]  → [3,4], [2]
rank 1：      [0,    1,    3*] → [0,1], [3*]</pre>
<p>N=5、world_size=2，DistributedSampler(drop_last=False) 会把开头的索引补到末尾，使两个 rank 各拿到三个位置。星号表示补入的样本 3；它是重复采样，不是第六个新样本。这里 PyTorch 2.8 的 seed=193、epoch=0 恰好生成前文的排列。实际训练依靠一致的 seed 与 set_epoch，而不应依赖跨版本完全相同的随机排列。</p>
{figure:ddp}
<p>两个 rank、每个 num_workers=2，意味着两个训练进程加四个 DataLoader 子进程。各 rank 的 worker 0 彼此独立，worker ID 不是 global rank。对普通 map-style Dataset，不要再按 worker ID 手工过滤一遍索引，否则可能把主进程已经分好的任务错误丢弃；IterableDataset 的分片责任不同，不属于本文路径。</p>
<h3 id="zh-drop-last">两层 drop_last</h3>
<div class="loader-table"><table><thead><tr><th>Sampler drop_last</th><th>Loader drop_last</th><th>rank 0 的 batch</th><th>rank 1 的 batch</th><th>合计</th></tr></thead><tbody>
<tr><td>False</td><td>False</td><td>[3,4]、[2]</td><td>[0,1]、[3*]</td><td>6 个位置，5 个不同样本</td></tr>
<tr><td>False</td><td>True</td><td>[3,4]</td><td>[0,1]</td><td>4 个位置；本例尾部的 2 和补入的 3 被丢弃</td></tr>
<tr><td>True</td><td>False</td><td>[3,4]</td><td>[0,1]</td><td>先将全局排列裁为 4 项</td></tr>
<tr><td>True</td><td>True</td><td>[3,4]</td><td>[0,1]</td><td>本地已整批，第二层不再丢弃</td></tr>
</tbody></table></div>
<p>DistributedSampler 的 drop_last 处理<strong>能否均分给各 rank</strong>，DataLoader / BatchSampler 的 drop_last 处理<strong>各 rank 的尾批是否够大</strong>。Loader 丢尾批并不普遍保证消除所有补齐重复项；它只是在这个小例子中恰好丢掉了补入的位置。评估时若要求每条样本只计一次，应使用明确的评估分片或按样本 ID 去重统计。{source:dist}；{source:batch}</p>
{lab}
<h3 id="zh-epoch">每轮重排与训练步数</h3>
<p>训练每个 epoch 前调用 <code>sampler.set_epoch(epoch)</code>，再创建 DataLoader 迭代器。DistributedSampler 使用 seed+epoch 生成排列；不调用 set_epoch 会重复相同的采样顺序。所有 rank 必须共享 sampler seed、数据集长度和稳定的索引含义；worker 的随机增强 seed 则可以按 rank 区分。{source:dist}</p>
<p>若每个 rank 都有 W 个 worker、预取系数为 P，自动 batching 下全局最多尝试派发约 <code>world_size × W × P</code> 个预取任务，受剩余数据限制。batch_size 是<strong>每个 rank</strong> 的大小；完整批次、无梯度累积时，一个训练 step 的样本位置数为 <code>world_size × batch_size</code>。尾批和补齐可能改变实际大小或不同样本数。</p>
<p>标准 DDP 训练要求各 rank 按兼容顺序参与梯度 collective。DistributedSampler 的均分使每个 rank 的迭代长度一致；使用过滤样本、自定义分片或不等长数据集时，需要重新检查步数。只给 DataLoader 设置 shuffle=True 而不做 rank 分片，通常会让每个 rank 都遍历完整数据集。</p>
<h3 id="zh-ddp-code">可运行的 DDP 例子</h3>
<p><a href="../assets/pytorch-internals/dataloader-demo.py" download>完整示例脚本</a>包含前面的 Dataset、collate_fn 和命令行入口。以下是其中的 DDP 训练函数：同一数据路径既能用 CPU/Gloo 验证，也能用 CUDA/NCCL 运行。代码中的 worker_options 在 workers&gt;0 时设置 spawn 与 prefetch_factor=2，在 workers=0 时省略这些参数。</p>
{code:ddp}
<pre class="code"># 保存完整脚本为 dataloader-demo.py；在安装 PyTorch 的环境中运行
python dataloader-demo.py --workers 0
python dataloader-demo.py --workers 1
python dataloader-demo.py --workers 2 --slow
python dataloader-demo.py --workers 2 --ragged
python dataloader-demo.py --workers 2 --bulk

# 两个 CPU rank，每个 rank 一个读取 worker
torchrun --standalone --nproc-per-node=2 dataloader-demo.py --ddp --workers 1

# 两张可见 GPU，每个 rank 两个读取 worker
torchrun --standalone --nproc-per-node=2 dataloader-demo.py --ddp --device cuda --workers 2</pre>
<p>Epoch 0 在 rank 0 输出 <code>[3,4]</code>、<code>[2]</code>，rank 1 输出 <code>[0,1]</code>、<code>[3]</code>；不同进程的打印行可能交错。Epoch 1 会换一份排列。使用 <code>--drop-sampler</code> 和 <code>--drop-batch</code> 可以分别观察上面两种丢弃策略。</p>

<h2 id="zh-reading">6. 源码与排查</h2>
<div class="loader-table"><table><thead><tr><th>现象</th><th>优先检查</th></tr></thead><tbody>
<tr><td>样本错误、异常难定位</td><td>先用 num_workers=0 查看 Dataset / collate 的直接调用栈，再恢复多进程。</td></tr>
<tr><td>Worker 已完成一批，训练仍等待</td><td>检查是否被更早的慢任务阻塞；区分完成顺序和 in_order 交付顺序。</td></tr>
<tr><td>Worker 越多反而越慢</td><td>检查存储争用、进程启动、序列化、CPU 线程竞争和 batch 过小；测量稳定态，而非只测首批。</td></tr>
<tr><td>改变 epoch 后 worker 状态没变</td><td>检查 persistent_workers 与 Dataset 副本；set_epoch 只改变 sampler 的索引排列。</td></tr>
<tr><td>DDP 样本重复或步数不符</td><td>检查 rank 分片、两层 drop_last、补齐项和各 rank 的 Dataset 长度。</td></tr>
</tbody></table></div>
<p>源码入口：{source:construct} → {source:single} / {source:dispatch} → {source:fetch} → {source:worker} → {source:order}。分布式索引规则见 {source:dist}，参数语义可查阅 <a href="https://docs.pytorch.org/docs/2.8/data.html">PyTorch 数据加载文档</a>。本文的进程边界、队列与版本相关参数都以固定版本为准。</p>
'''

EN = r'''
<h1>PyTorch DataLoader internals</h1>
<p class="lead">PyTorch DataLoader organizes dataset samples into training batches. For a map-style Dataset, a Sampler chooses indices, a BatchSampler groups them, the Dataset reads and transforms samples, and collate_fn assembles model inputs. A five-sample example connects these responsibilities to loading in the training process, one worker, multiple workers, and DDP, including prefetching, delivery order, and rank sharding.</p>
<aside class="loader-note"><p>This article follows ordinary map-style datasets in <a href="https://github.com/pytorch/pytorch/tree/ba56102387ef21a3b04b357e5b183d48f0afefc7">PyTorch 2.8.0</a>. Diagram messages link to that source revision. <code>num_workers=0</code> means no subprocess; <code>num_workers=1</code> means one separate loading worker. Workers are processes, not loading threads.</p></aside>

<h2 id="en-components">1. Indices and batches</h2>
<h3 id="en-contract">Five components</h3>
<p>A map-style Dataset maps a key to a sample through <code>dataset[index]</code>. Keys need not be integers; this example uses 0 through 4 and the fixed order <code>[3, 0, 4, 1, 2]</code>. Reading a sample may involve image decoding, database access, or an in-memory transformation. The Dataset does not choose the epoch's sampling order. {source:dataset}</p>
<div class="loader-table"><table><thead><tr><th>Component</th><th>Responsibility</th><th>Example</th></tr></thead><tbody>
<tr><td>Sampler</td><td>Produce sample indices</td><td><code>3, 0, 4, 1, 2</code></td></tr>
<tr><td>BatchSampler</td><td>Group indices</td><td><code>[3,0], [4,1], [2]</code></td></tr>
<tr><td>Dataset</td><td>Read and transform a sample</td><td><code>dataset[3]</code>: x=<code>[3,30]</code>, y=1</td></tr>
<tr><td>collate_fn</td><td>Assemble samples into a batch</td><td>Stack two x tensors into shape <code>[2,2]</code></td></tr>
<tr><td>DataLoader / iterator</td><td>Coordinate sampling, fetching, prefetching, and delivery</td><td>One batch per <code>next(iterator)</code></td></tr>
</tbody></table></div>
<p>BatchSampler handles <strong>indices</strong>; collate_fn receives <strong>samples already fetched</strong>. Actual data access happens between them. Without a custom sampler, shuffle=False selects SequentialSampler and shuffle=True selects RandomSampler. With batch_size enabled, DataLoader normally wraps the sampler in BatchSampler. {source:construct}; {source:random}</p>
<h3 id="en-fixed-example">Five samples</h3>
<p>Sample i has features <code>[i, 10i]</code> and label <code>i % 2</code>. Removing I/O and random augmentation makes index flow easy to inspect. The worker field records where retrieval runs: -1 for the training process, or a worker ID local to this loader.</p>
{code:base}
<pre class="code">[3, 0] [[3.0, 30.0], [0.0, 0.0]]
[4, 1] [[4.0, 40.0], [1.0, 10.0]]
[2]    [[2.0, 20.0]]</pre>
<p>An explicit batch_sampler exposes the grouping step. When supplying it, leave batch_size, sampler, shuffle, and drop_last unset on DataLoader: the batch sampler owns those decisions. Its drop_last=False retains the final <code>[2]</code>. {source:batch}</p>

<h2 id="en-single">2. Main process and one worker</h2>
<h3 id="en-main-process">Loading in the main process</h3>
<p>DataLoader construction primarily stores configuration; <code>iter(loader)</code> creates the iterator. With num_workers=0, each next call gets indices, fetches samples, and runs collation inside the training process. No DataLoader subprocess prepares a future batch while the model runs. {source:iterator}; {source:single}</p>
{code:concept}
<p>This is a conceptual equivalent of the default per-sample path. Internally, _MapDatasetFetcher connects the Dataset to collate_fn. The optional __getitems__ batch-fetch interface replaces the individual fetches, as discussed below. {source:fetch}</p>
{figure:single}
<h3 id="en-one-worker">One separate worker</h3>
<p>num_workers=1 creates one subprocess. Sampler and BatchSampler still run in the main process, which queues <code>(task ID, index list)</code>. The worker fetches, transforms, and collates that entire task, then places <code>(task ID, batch)</code> into a result queue for the training process. {source:spawn}; {source:dispatch}; {source:worker}</p>
<p>This already permits data preparation to overlap work in the training process. The worker itself processes its tasks sequentially; it does not automatically turn two samples within a batch into parallel reads. Its ordinary map-style Dataset replica can address the full dataset, but only fetches the indices dispatched to it.</p>

<h2 id="en-workers">3. Multiple workers and prefetch</h2>
<h3 id="en-task-unit">Whole-batch tasks</h3>
<p>Keep the same Dataset, Sampler, and batch size, then set the worker count to two:</p>
{code:workers}
<p>In this version's ordinary map-style path with in_order=True, initial tasks cycle through active workers. Worker 0 receives task 0=<code>[3,0]</code> and task 2=<code>[2]</code>; worker 1 receives task 1=<code>[4,1]</code>. <strong>One worker normally fetches and collates an entire batch.</strong> More workers parallelize different batches, rather than automatically dividing one batch among workers. {source:dispatch}</p>
<h3 id="en-prefetch">The prefetch window</h3>
<p>With automatic batching, prefetch_factor counts batch tasks per worker. Two workers with a factor of two attempt to dispatch up to four tasks initially. Only three batches exist here, so only three tasks are sent. For longer datasets, delivering results triggers replenishment. The window spans queued, executing, and completed tasks awaiting delivery; it does not mean four completed batches are always ready in memory. {source:prefetch}; {source:dispatch}</p>
<p>Prefetch moves future work earlier. Increasing the window cannot close a sustained throughput gap when loading remains slower than consumption. It also increases memory used by tasks, batches, and buffered results; Dataset objects, decoding caches, and process overhead add further costs.</p>
<h3 id="en-order">Completion versus delivery</h3>
<p>If dataset[3] is slow, worker 1 may finish task 1 first. With the default in_order=True, the main process buffers that result by <strong>task ID</strong> and delivers tasks 0, 1, and 2 in order. Ordered delivery follows Sampler / BatchSampler order; it does not sort sample IDs numerically. {source:order}</p>
{figure:workers}
<p>in_order=False can deliver an available later result without waiting for an earlier task. This reduces blocking by slow batches but changes training order. If one class consistently decodes faster, the training prefix may also become skewed. No particular out-of-order sequence is guaranteed: startup, scheduling, and storage latency all matter. Preserve the default when order and reproducibility are requirements. {source:order}</p>
<h3 id="en-worker-state">Process state and lifetime</h3>
<p>The examples explicitly use spawn. Define Dataset classes, collate_fn, and worker_init_fn at module scope, and guard iterator creation with <code>if __name__ == "__main__":</code>. Subprocesses must be able to import and reconstruct those objects; an unpicklable lambda is unsuitable for worker initialization. Open file handles and database connections generally belong inside each worker.</p>
<p>Normally a new iterator starts workers and exhaustion shuts them down. persistent_workers=True retains processes and their Dataset instances across epochs. Mutating dataset.epoch in the parent does not automatically update those replicas, and worker_init_fn does not rerun every epoch. Epoch-dependent state needs explicit communication. {source:iterator}; {source:worker}</p>
<p>Sampling randomness and augmentation randomness are separate. This version seeds PyTorch, Python random, and, when available, NumPy as workers start. Custom generators and other libraries still need explicit management. get_worker_info exposes the local worker ID, seed, and Dataset. A fixed sampling order alone does not guarantee identical augmentation when the worker count changes. {source:seed}; {source:info}</p>

<h2 id="en-batch">4. Batch structure and transfer</h2>
<h3 id="en-collate">Stacking and padding</h3>
<p>default_collate recursively handles structures such as dictionaries and stacks matching tensor fields, adding a batch dimension. The first batch has x shape <code>[2,2]</code> and y shape <code>[2]</code>. It does not automatically pad unequal tensor lengths. If sample i instead contains a sequence of length i+1, the first batch contains lengths four and one and needs custom collation. {source:default}; {source:collate}</p>
{code:ragged}
<p>The first batch becomes <code>x=[[1,2,3,4],[1,0,0,0]]</code>, with <code>lengths=[4,1]</code>. A mask distinguishes valid positions from padding. Pass pad_collate to DataLoader with RaggedSamples: padding runs in the main process for num_workers=0, or inside the worker assigned that batch for num_workers&gt;0.</p>
<h3 id="en-bulk">Batched fetching</h3>
<p>The optional Dataset.__getitems__(indices) receives an entire index list instead of repeated __getitem__ calls. A backend could use one database query or combine file reads. It should return a <strong>list of samples in requested order</strong>; collate_fn still runs afterward. This example demonstrates the interface only: its Python loop does not itself accelerate I/O. {source:fetch}</p>
{code:bulk}
<p>Setting batch_size=None without batch_sampler disables automatic batching. The sampler supplies one key, the fetcher obtains one sample, and default_convert is the default conversion. A custom collate_fn then receives a single sample, not a sample list; the whole-batch task diagrams do not apply to that mode. {source:construct}; {source:fetch}</p>
<h3 id="en-device">Pin memory and H2D</h3>
<p>Dataset and collate_fn normally return CPU tensors. With CUDA available and <code>pin_memory=True</code>, DataLoader places the batch's CPU tensors in page-locked host memory for efficient GPU transfer. Automatic pinning runs <strong>after collate_fn and before the batch reaches the training loop</strong>. Its execution location depends on num_workers. {source:single}; {source:spawn}; {source:pin}</p>
<div class="loader-table"><table><thead><tr><th>Configuration</th><th>Fetching and collate_fn</th><th>Automatic pin_memory</th></tr></thead><tbody>
<tr><td><code>num_workers=0</code></td><td>The thread calling next in the training process, usually its main thread</td><td>The same thread, synchronously inside next</td></tr>
<tr><td><code>num_workers&gt;0</code></td><td>A worker subprocess</td><td><strong>A dedicated pin-memory thread in the training process</strong></td></tr>
</tbody></table></div>
<p>With workers, the pin-memory thread consumes assembled batches from the worker result queue, pins them, and puts them into a data queue within the training process. The training thread then obtains batches according to the iterator's delivery rules. Each DDP rank has its own path; the pin-memory thread does not belong to a loading worker. {source:pin}; {source:spawn}</p>
<pre class="code">num_workers=0:
Training thread: fetch → collate_fn → pin_memory → return batch

num_workers&gt;0:
Worker: fetch → collate_fn → result queue
Training process / pin-memory thread: result queue → pin_memory → data queue
Training process / training thread: data queue → return batch in delivery order</pre>
<p>The two sequence diagrams above use the default pin_memory=False and omit this optional stage. <strong>Pinned memory is still CPU memory; DataLoader does not automatically move the batch to the GPU.</strong> The training code initiates H2D through <code>.to(device)</code>:</p>
{code:cuda}
<p>non_blocking=True permits asynchronous transfer submission. Actual overlap with computation also depends on streams, dependencies, and hardware; a consumer on the same CUDA stream still waits for its copy. Custom batch classes need pin_memory support, whereas ordinary tensor dictionaries are traversed by the default implementation.</p>

<h2 id="en-ddp">5. Reading data under DDP</h2>
<h3 id="en-ranks">Ranks and workers</h3>
<p>A typical DDP setup assigns one training process to each GPU, with a Dataset, DataLoader, and worker pool per rank. DDP synchronizes model gradients; <strong>it does not shard DataLoader inputs automatically</strong>. Map-style training commonly uses DistributedSampler for that job. <a href="https://docs.pytorch.org/docs/2.8/generated/torch.nn.parallel.DistributedDataParallel.html">DDP documentation</a>.</p>
<p>Rank sharding precedes local batching. Each rank computes the same global permutation using the same seed and epoch, selects <code>indices[rank:total_size:world_size]</code>, and passes its indices to its local BatchSampler. These computations are rank-local and normally need no epoch-by-epoch index broadcast. {source:dist}</p>
<pre class="code">Global order: [3, 0, 4, 1, 2]
Pad to six:   [3, 0, 4, 1, 2, 3*]
Rank 0:      [3,    4,    2]   → [3,4], [2]
Rank 1:         [0,    1,    3*] → [0,1], [3*]</pre>
<p>With N=5 and world_size=2, DistributedSampler(drop_last=False) appends indices from the start so each rank receives three positions. The star marks another occurrence of sample 3, not a sixth distinct sample. PyTorch 2.8 happens to produce our example permutation with seed=193 and epoch=0. Training should rely on consistent seeds and set_epoch, not identical random permutations across releases.</p>
{figure:ddp}
<p>Two ranks with num_workers=2 each create two training processes and four loader subprocesses. Their worker 0 processes are distinct; worker IDs are not global ranks. For an ordinary map-style Dataset, applying another worker-ID filter can discard indices already assigned by the parent. IterableDataset has different sharding responsibilities and is outside this article's execution path.</p>
<h3 id="en-drop-last">Two drop_last decisions</h3>
<div class="loader-table"><table><thead><tr><th>Sampler drop_last</th><th>Loader drop_last</th><th>Rank 0 batches</th><th>Rank 1 batches</th><th>Total</th></tr></thead><tbody>
<tr><td>False</td><td>False</td><td>[3,4], [2]</td><td>[0,1], [3*]</td><td>6 positions, 5 distinct samples</td></tr>
<tr><td>False</td><td>True</td><td>[3,4]</td><td>[0,1]</td><td>4 positions; this example drops sample 2 and the padded 3</td></tr>
<tr><td>True</td><td>False</td><td>[3,4]</td><td>[0,1]</td><td>Global order is truncated to four first</td></tr>
<tr><td>True</td><td>True</td><td>[3,4]</td><td>[0,1]</td><td>Local batches are complete; no further drop</td></tr>
</tbody></table></div>
<p>DistributedSampler.drop_last handles <strong>divisibility across ranks</strong>; DataLoader / BatchSampler.drop_last handles <strong>incomplete local batches</strong>. Dropping local tails does not generally remove every padded duplicate. It happens to do so in this example. Evaluation requiring one contribution per sample needs an explicit evaluation shard strategy or sample-ID deduplication. {source:dist}; {source:batch}</p>
{lab}
<h3 id="en-epoch">Epochs and training steps</h3>
<p>Call sampler.set_epoch(epoch) before creating the DataLoader iterator for that epoch. DistributedSampler generates its permutation from seed+epoch; without set_epoch it repeats the same order. Ranks must agree on sampler seed, dataset length, and stable index meanings. Worker augmentation seeds can instead differ by rank. {source:dist}</p>
<p>With W workers per rank and prefetch factor P, automatic batching attempts a global prefetch window of roughly <code>world_size × W × P</code> tasks, limited by remaining data. batch_size is <strong>per rank</strong>. Full batches without gradient accumulation give <code>world_size × batch_size</code> sample positions per training step; tails and padding can change actual sizes or distinct-sample counts.</p>
<p>Ordinary DDP training requires compatible gradient collective participation across ranks. Equal sampler lengths give equal iteration lengths; filtering, custom sharding, or different dataset sizes require another check. Setting shuffle=True alone without rank sharding generally makes every rank traverse the full dataset.</p>
<h3 id="en-ddp-code">Runnable DDP example</h3>
<p>The <a href="../assets/pytorch-internals/dataloader-demo.py" download>complete example script</a> includes the Dataset, collation functions, and command-line entry point. Its DDP training function below supports CPU/Gloo and CUDA/NCCL. The worker_options helper sets spawn and prefetch_factor=2 only when workers&gt;0.</p>
{code:ddp}
<pre class="code"># Save the full script as dataloader-demo.py in an environment with PyTorch.
python dataloader-demo.py --workers 0
python dataloader-demo.py --workers 1
python dataloader-demo.py --workers 2 --slow
python dataloader-demo.py --workers 2 --ragged
python dataloader-demo.py --workers 2 --bulk

# Two CPU ranks, one data worker per rank.
torchrun --standalone --nproc-per-node=2 dataloader-demo.py --ddp --workers 1

# Two visible GPUs, two data workers per rank.
torchrun --standalone --nproc-per-node=2 dataloader-demo.py --ddp --device cuda --workers 2</pre>
<p>At epoch 0, rank 0 outputs <code>[3,4]</code> and <code>[2]</code>; rank 1 outputs <code>[0,1]</code> and <code>[3]</code>. Printed lines can interleave across processes. Epoch 1 uses another permutation. --drop-sampler and --drop-batch independently enable the two drop policies.</p>

<h2 id="en-reading">6. Source and diagnosis</h2>
<div class="loader-table"><table><thead><tr><th>Symptom</th><th>First check</th></tr></thead><tbody>
<tr><td>Bad samples or opaque exceptions</td><td>Use num_workers=0 for a direct Dataset / collate traceback, then restore multiprocessing.</td></tr>
<tr><td>A worker completed a batch but training waits</td><td>Check whether an earlier slow task blocks in_order delivery.</td></tr>
<tr><td>More workers reduce performance</td><td>Inspect storage contention, process startup, serialization, CPU thread competition, and very small batches; measure steady state separately from startup.</td></tr>
<tr><td>Epoch changes do not reach workers</td><td>Check persistent Dataset replicas; set_epoch changes sampler order, not arbitrary Dataset state.</td></tr>
<tr><td>DDP repeats samples or has mismatched steps</td><td>Inspect rank sharding, both drop_last flags, padded indices, and per-rank dataset lengths.</td></tr>
</tbody></table></div>
<p>Source path: {source:construct} → {source:single} / {source:dispatch} → {source:fetch} → {source:worker} → {source:order}. Rank sharding is in {source:dist}; parameter definitions are in the <a href="https://docs.pytorch.org/docs/2.8/data.html">data-loading documentation</a>. Process boundaries, queues, and version-sensitive options here refer to the pinned revision.</p>
'''

def expand(body,lang):
    body=re.sub(r'\{code:(\w+)\}', lambda m:'<pre class="code" data-language="python"><code>'+escape(SNIPPETS[m[1]])+'</code></pre>',body)
    body=re.sub(r'\{source:(\w+)\}',lambda m:source(m[1]),body)
    body=re.sub(r'\{figure:(\w+)\}',lambda m:figure(m[1],lang),body)
    return body.replace('{lab}',lab(lang))

def main():
    metadata={
        'title':'PyTorch DataLoader 工作原理','title_en':'PyTorch DataLoader internals',
        'slug':'pytorch-dataloader','date':'2026-10-26',
        'tags':'PyTorch, 深度学习, DataLoader, DDP','tags_en':'PyTorch, Deep Learning, DataLoader, DDP',
        'reading':'20 分钟','reading_en':'20 min',
        'summary':'围绕五个样本解释 map-style DataLoader 的采样、分批、读取与组装，从单进程、单 worker 扩展到多 worker 预取和 DDP 分片。',
        'summary_en':'Follow five samples through map-style sampling, batching, fetching, collation, worker prefetch, and distributed rank sharding.',
        'series':'pytorch-internals','series_title':'PyTorch 内部机制','series_title_en':'PyTorch Internals','series_order':'10',
    }
    meta='\n'.join(f'<meta name="post:{key}" content="{escape(value,quote=True)}">' for key,value in metadata.items())
    html=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PyTorch DataLoader 工作原理</title>
{meta}
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<link rel="stylesheet" href="../assets/pytorch-internals/dataloader.css">
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<script src="../assets/pytorch-internals/dataloader.js" defer></script>
</head><body><div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div></aside><main class="content">
<div class="lang-zh">{expand(ZH,'zh')}</div><div class="lang-en">{expand(EN,'en')}</div>
</main></div></body></html>\n'''
    target=ROOT/'posts/pytorch-dataloader.html';target.write_text(html)
    print('Wrote',target)

if __name__=='__main__':
    main()
