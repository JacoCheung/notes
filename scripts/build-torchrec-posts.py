#!/usr/bin/env python3
"""Build both bilingual TorchRec posts and the legacy URL redirect.

Run render-torchrec-diagrams.py first when sequence specifications change, then
this script and build-index.py. Shared diagram assets keep stable filenames.
"""
from pathlib import Path
from html import escape, unescape
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = 'torchrec-row-wise-sharding-pipeline'
REV = '1d87b8f79b7bb1671cb8be3e646e99e835cce610'
BASE = f'https://github.com/pytorch/torchrec/blob/{REV}/torchrec/'
SOURCES = {
 'forward': ('distributed/types.py', 'L1278-L1293', 'ShardedModule.forward', 'ShardedModule.forward'),
 'prepare': ('distributed/embedding.py', 'L1406-L1460', 'EC 去重与 inverse mapping', 'EC deduplication and inverse mapping'),
 'input': ('distributed/embedding.py', 'L1542-L1625', 'ShardedEmbeddingCollection.input_dist', 'ShardedEmbeddingCollection.input_dist'),
 'bucket': ('distributed/embedding_sharding.py', 'L268-L353', 'bucketize_kjt_before_all2all', 'bucketize_kjt_before_all2all'),
 'rw': ('distributed/sharding/rw_sequence_sharding.py', 'L57-L193', 'row-wise sequence sharding 组件', 'Row-wise sequence sharding components'),
 'splits': ('distributed/dist_data.py', 'L440-L685', 'SplitsAllToAllAwaitable', 'SplitsAllToAllAwaitable'),
 'tensors': ('distributed/dist_data.py', 'L686-L1036', 'KJT 的 payload awaitable', 'KJT payload awaitables'),
 'kjt_splits': ('sparse/jagged_tensor.py', 'L3201-L3210', 'KJT.dist_splits', 'KJT.dist_splits'),
 'kjt_lengths': ('sparse/jagged_tensor.py', 'L1359-L1410', 'length_per_key 的按需计算', 'On-demand length_per_key computation'),
 'kjt_init': ('sparse/jagged_tensor.py', 'L3300-L3379', 'KJT.dist_init 的重排与 sync', 'KJT.dist_init: permutation and sync'),
 'pipeline_splits': ('distributed/train_pipeline/runtime_forwards.py', 'L395-L420', 'Pipeline 的 split sizes 准备', 'Pipeline split-size preparation'),
 'fused_validation': ('distributed/embedding_sharding.py', 'L942-L956', '融合 splits 前的校验读回', 'Validation readbacks before fused splits'),
 'split_validation': ('distributed/dist_data.py', 'L644-L661', '第一次 wait 中的发送端校验读回', 'Sent-split validation readback in the first wait'),
 'host_copy': ('sparse/jagged_tensor.py', 'L68-L140', 'CUDA metadata 的 D2H 与 stream synchronize', 'CUDA metadata D2H and stream synchronization'),
 'kjt_split_prepare': ('sparse/jagged_tensor.py', 'L2662-L2676', 'KJT.split 的主机 metadata', 'Host metadata in KJT.split'),
 'split_h2d': ('distributed/dist_data.py', 'L938-L947', 'Split lists 与 stride 的 H2D', 'Split-list and stride H2D'),
 'split_sizes_h2d': ('distributed/dist_data.py', 'L941-L943', 'Lengths / values splits 的 H2D', 'Lengths / values split H2D'),
 'split_stride_h2d': ('distributed/dist_data.py', 'L944-L947', 'Stride 的 H2D', 'Stride H2D'),
 'split_d2h': ('distributed/dist_data.py', 'L586-L597', '接收 splits 的 D2H', 'Received-split D2H'),
 'split_layout': ('distributed/dist_data.py', 'L529-L542', 'Splits 的打包与 AllToAll', 'Split packing and AllToAll'),
 'rw_feature_splits': ('distributed/sharding/rw_sharding.py', 'L478-L481', 'Row-wise 的 feature splits', 'Row-wise feature splits'),
 'fused_split_layout': ('distributed/embedding_sharding.py', 'L915-L940', '多个请求的 splits 合并', 'Combining splits from multiple requests'),
 'input_recat': ('distributed/dist_data.py', 'L249-L367', '输入 recat 与可变 batch offsets', 'Input recat and unequal-batch offsets'),
 'collective_tag': ('distributed/dist_data.py', 'L463-L489', 'Collective 校验 tag 的 H2D', 'Collective-validation tag H2D'),
 'compute': ('distributed/embedding.py', 'L1627-L1718', 'EC compute 与 output_dist', 'EC compute and output_dist'),
 'lookup': ('distributed/embedding_lookup.py', 'L408-L433', 'GroupedEmbeddingsLookup.forward', 'GroupedEmbeddingsLookup.forward'),
 'tbe': ('distributed/batched_embedding_kernel.py', 'L2530-L2605', 'BatchedFusedEmbedding 的 backend 配置', 'BatchedFusedEmbedding backend configuration'),
 'tbe_call': ('distributed/batched_embedding_kernel.py', 'L1834-L1856', 'BaseBatchedEmbedding.forward 的 IDs / offsets 转换', 'BaseBatchedEmbedding.forward: ID / offset conversion'),
 'output': ('distributed/dist_data.py', 'L1941-L2098', 'SequenceEmbeddingsAllToAll 与 unbucketize', 'SequenceEmbeddingsAllToAll and unbucketize'),
 'seq': ('distributed/comm_ops.py', 'L1916-L2165', 'sequence AllToAll 的 forward / backward', 'Sequence AllToAll forward / backward'),
 'jt': ('modules/utils.py', 'L246-L311', 'construct_jagged_tensors', 'construct_jagged_tensors'),
 'fused': ('distributed/batched_embedding_kernel.py', 'L1631-L1637', 'EmbeddingFusedOptimizer.step', 'EmbeddingFusedOptimizer.step'),
 'rewrite': ('distributed/train_pipeline/utils.py', 'L248-L356', '启动 input_dist 与融合 splits', 'Starting input_dist and fusing splits'),
 'runtime': ('distributed/train_pipeline/runtime_forwards.py', 'L85-L140', 'PipelinedForward', 'PipelinedForward'),
 'preforward': ('distributed/train_pipeline/runtime_forwards.py', 'L288-L334', 'PrefetchPipelinedForward', 'PrefetchPipelinedForward'),
 'ordinary': ('distributed/train_pipeline/train_pipelines.py', 'L838-L922', 'TrainPipelineSparseDist.progress', 'TrainPipelineSparseDist.progress'),
 'wait': ('distributed/train_pipeline/train_pipelines.py', 'L1129-L1195', 'start / wait_sparse_data_dist', 'start / wait_sparse_data_dist'),
 'prefetch': ('distributed/train_pipeline/train_pipelines.py', 'L2137-L2256', 'PrefetchTrainPipelineSparseDist.progress / _prefetch', 'PrefetchTrainPipelineSparseDist.progress / _prefetch'),
 'prefetch_helper': ('distributed/train_pipeline/utils.py', 'L746-L820', 'prefetch_embeddings 的第二次 wait 与状态交接', 'prefetch_embeddings: second wait and state handoff'),
 'prefetch_module': ('distributed/embedding_types.py', 'L423-L439', 'ShardedEmbeddingModule.prefetch', 'ShardedEmbeddingModule.prefetch'),
 'cache': ('distributed/embedding_lookup.py', 'L368-L406', 'lookup.prefetch 与 backend 配置检查', 'lookup.prefetch and backend configuration checks'),
 'need_prefetch': ('distributed/embedding_lookup.py', 'L252-L269', '需要 prefetch 的 compute kernel', 'Compute kernels that require prefetch'),
 'stream': ('distributed/train_pipeline/utils.py', 'L151-L182', '_wait_for_batch 的 stream 依赖与 record_stream', '_wait_for_batch: stream dependencies and record_stream'),
 'fill': ('distributed/train_pipeline/train_pipelines.py', 'L751-L836', '普通 pipeline 的入队、出队与填充', 'Ordinary pipeline enqueue, dequeue, and fill'),
 'prefill': ('distributed/train_pipeline/train_pipelines.py', 'L2097-L2132', 'prefetch pipeline 的填充', 'Prefetch pipeline fill'),
 'prefstreams': ('distributed/train_pipeline/train_pipelines.py', 'L2060-L2095', 'prefetch 相关 stream 的构造', 'Construction of prefetch-related streams'),
}
FIGS = {'01': ('01-native-forward', 'forward 的模块总览', 'Forward module overview', ['forward', 'input', 'compute']), '02': ('02-input-prepare', '输入重排与可选 unique 的细分调用', 'Input permutation and optional unique', ['prepare', 'input']), '03': ('03-input-distribution', 'Input distribution：H2D、host sync 与三次 AllToAll', 'Input distribution: H2D, host sync, and three AllToAll calls', ['bucket', 'splits', 'tensors', 'host_copy']), '04': ('04-local-lookup', 'Grouped lookup、BatchedFusedEmbedding 与 TBE', 'Grouped lookup, BatchedFusedEmbedding, and TBE', ['lookup', 'tbe', 'tbe_call']), '05': ('05-output-distribution', '输出通信的布局准备、codec 与 AllToAll 发起', 'Output layout preparation, codec, and AllToAll launch', ['output', 'seq']), '06': ('06-output-postprocess', 'Lazy wait、unbucketize 与 reverse_indices 展开', 'Lazy wait, unbucketize, and reverse_indices expansion', ['output', 'jt']), '07': ('07-backward-overview', 'Backward 的完整 autograd 拓扑', 'Complete backward autograd topology', ['jt', 'seq', 'tbe']), '08': ('08-gradient-restore', 'Split、reverse_indices 与 unbucketize 的梯度恢复', 'Gradients through split, reverse_indices, and unbucketize', ['jt', 'output']), '09': ('09-backward-launch', '反向 AllToAll 的 encode、launch 与请求保存', 'Reverse AllToAll encode, launch, and request storage', ['seq']), '10': ('10-backward-finalize', '反向请求的 wait、decode、recat 与梯度缩放', 'Reverse request wait, decode, recat, and gradient scaling', ['seq']), '11': ('11-fused-backward', 'TBE 的本地 backward 与示例中的 fused update', 'Local TBE backward and the sample fused update', ['tbe', 'tbe_call', 'fused']), '12': ('12-gradient-boundary', 'Forward wrapper 与整数输入的梯度边界', 'Gradient boundaries at forward wrappers and integer inputs', ['input', 'tbe', 'fused']), '13': ('13-context-handoff', '两种 pipeline 的 batch context 交接', 'Per-batch state handoff in both pipelines', ['rewrite', 'runtime', 'prefetch_helper', 'preforward']), '14': ('14-sparse-pipeline', '普通 sparse dist pipeline 的稳定态调用序列', 'Steady-state ordinary sparse dist pipeline', ['ordinary', 'runtime', 'wait']), '15': ('15-sparse-pipeline-timeline', '普通 sparse-dist pipeline：三轮交互时间线', 'Ordinary sparse-dist pipeline: interactive three-iteration timeline', ['ordinary', 'wait', 'runtime']), '16': ('16-prefetch-pipeline', '带 prefetch 的 sparse dist pipeline 的稳定态调用序列', 'Steady-state prefetch sparse dist pipeline', ['prefetch', 'prefetch_helper', 'preforward'])}

SPLITS_PRIMER_ZH = r'''
<aside class="note-box splits-primer" id="zh-splits-primer" role="note" aria-labelledby="zh-splits-primer-title">
<p id="zh-splits-primer-title"><strong>Splits：每个 rank 的收发计数</strong></p>
<p>输入通信中的 <code>splits</code> 是各 rank 要收发的 <strong>tensor 元素数量</strong>，不是 ID 本身，也不是字节数。以下用一个独立例子说明：<code>P=2</code> 个 rank、一个 feature、每个 rank 的 batch size 为 <code>B=2</code>，固定 stride、无 weights，关闭去重和 collective tag 校验。分桶后，两端准备的 metadata 如下；每个张量都是 CUDA 上的 <code>int64</code>，shape 为 <code>[P]=[2]</code>，元素按目标 rank 0、1 排列。</p>
<div class="table-scroll"><table><thead><tr><th scope="col">Metadata tensor</th><th scope="col">rank 0 发送端</th><th scope="col">rank 1 发送端</th><th scope="col">每项的含义</th></tr></thead><tbody>
<tr><td>lengths splits</td><td><code>[2, 2]</code></td><td><code>[2, 2]</code></td><td>发送多少个 lengths 元素；本例为 feature 数 × B = 2</td></tr>
<tr><td>values splits</td><td><code>[3, 1]</code></td><td><code>[2, 4]</code></td><td>发送多少个 ID；由本批次 ID 的分桶结果决定</td></tr>
<tr><td>stride metadata</td><td><code>[2, 2]</code></td><td><code>[2, 2]</code></td><td>把发送端的 batch size B 告知每个接收端</td></tr>
</tbody></table></div>
<p>因此 rank 0 向 rank 0、1 分别发送 3、1 个 ID，rank 1 分别发送 2、4 个 ID。源码把这三个 metadata tensor 按 <code>stack(..., dim=1)</code> 排成 <code>[P, 3]</code>，再 flatten 成真正交给 splits AllToAll 的一维 tensor：</p>
<pre class="code" data-language="text"># 每个三元组：[lengths 元素数, ID 数, stride]
rank 0 发送：[2, 3, 2,  2, 1, 2]   # shape [6]，按目标 rank 排列
rank 1 发送：[2, 2, 2,  2, 4, 2]   # shape [6]，按目标 rank 排列
rank 0 接收：[2, 3, 2,  2, 2, 2]   # shape [6]，按来源 rank 排列</pre>
<p>rank 0 接收后用 <code>view(P, -1).T</code> 得到 <code>[3, P]</code>，读回的列表是 <code>[[2, 2], [3, 2], [2, 2]]</code>，依次对应 lengths、values 和 stride。其中 values 的接收 splits <code>[3, 2]</code> 表示从 rank 0 收 3 个 ID、从 rank 1 收 2 个 ID，因此后续 values 接收 buffer 有 5 个元素。Splits 通信每个 peer 只交换固定数量的计数；真正的 lengths / ID payload 随后按这些计数传输。{source:kjt_splits}；{source:split_h2d}；{source:split_layout}；{source:split_d2h}</p>
<p>源码中 <code>KJTAllToAll(splits=[1, 1])</code> 的构造参数另指<strong>每个 rank 分配的 feature 数</strong>；它和上述随 batch 变化的 ID 数不同。一般有 N 个 metadata tensor 时，打包布局为 <code>[P, N]</code>，实际收发 shape 为 <code>[P × N]</code>；weights、variable stride 和可选校验 tag 的字段组成应按实际路径确定。{source:rw_feature_splits}</p>
{fused_splits_primer}
</aside>
'''

SPLITS_PRIMER_EN = r'''
<aside class="note-box splits-primer" id="en-splits-primer" role="note" aria-labelledby="en-splits-primer-title">
<p id="en-splits-primer-title"><strong>Splits: per-rank send and receive counts</strong></p>
<p>In input communication, <code>splits</code> count <strong>tensor elements</strong> sent to or received from each rank, rather than IDs themselves or bytes. This standalone example has <code>P=2</code> ranks, one feature, and local batch size <code>B=2</code> on each rank, with fixed stride, no weights, no deduplication, and no collective validation tag. After bucketization, each sender prepares the metadata below. Each tensor is CUDA <code>int64</code> with shape <code>[P]=[2]</code>; entries follow destination ranks 0 and 1.</p>
<div class="table-scroll"><table><thead><tr><th scope="col">Metadata tensor</th><th scope="col">Rank 0 sender</th><th scope="col">Rank 1 sender</th><th scope="col">Meaning of each entry</th></tr></thead><tbody>
<tr><td>Lengths splits</td><td><code>[2, 2]</code></td><td><code>[2, 2]</code></td><td>Number of lengths elements; feature count × B = 2 here</td></tr>
<tr><td>Values splits</td><td><code>[3, 1]</code></td><td><code>[2, 4]</code></td><td>Number of IDs, determined by this batch's bucketization</td></tr>
<tr><td>Stride metadata</td><td><code>[2, 2]</code></td><td><code>[2, 2]</code></td><td>Sender batch size B, repeated for every destination</td></tr>
</tbody></table></div>
<p>Rank 0 sends 3 and 1 IDs to ranks 0 and 1; rank 1 sends 2 and 4. The implementation packs the three metadata tensors with <code>stack(..., dim=1)</code> into <code>[P, 3]</code>, then flattens them into the actual one-dimensional input to splits AllToAll:</p>
<pre class="code" data-language="text"># Each triple: [lengths element count, ID count, stride]
rank 0 sends:    [2, 3, 2,  2, 1, 2]   # shape [6], destination order
rank 1 sends:    [2, 2, 2,  2, 4, 2]   # shape [6], destination order
rank 0 receives: [2, 3, 2,  2, 2, 2]   # shape [6], source order</pre>
<p>Rank 0 applies <code>view(P, -1).T</code> to obtain <code>[3, P]</code> and reads back <code>[[2, 2], [3, 2], [2, 2]]</code> for lengths, values, and stride. The values receive splits <code>[3, 2]</code> mean 3 IDs from rank 0 and 2 from rank 1, so the subsequent values receive buffer has 5 elements. Splits communication exchanges a fixed number of counts per peer; lengths and ID payloads follow using those counts. {source:kjt_splits}; {source:split_h2d}; {source:split_layout}; {source:split_d2h}</p>
<p>The constructor argument in <code>KJTAllToAll(splits=[1, 1])</code> instead assigns a <strong>feature count to each rank</strong>, distinct from batch-dependent ID counts. With N metadata tensors, the packed layout is <code>[P, N]</code> and the actual send and receive shape is <code>[P × N]</code>. Weights, variable stride, and an optional validation tag affect which fields are present. {source:rw_feature_splits}</p>
{fused_splits_primer}
</aside>
'''

FUSED_SPLITS_PRIMER = {
    'zh': '<p>Pipeline 的 fused splits 将同一个 process group 中多个请求的 metadata 一起打包。若合并 M 个上述基础 KJT 请求，且不附加 tag，则 <code>N=3M</code>，收发 shape 为 <code>[3MP]</code>；例如 <code>M=2, P=2</code> 时为 <code>[12]</code>。融合的是计数，ID payload 仍单独传输。{source:fused_split_layout}</p>',
    'en': '<p>Pipeline fused splits pack metadata from multiple requests in the same process group. For M baseline KJT requests as above, without a tag, <code>N=3M</code> and the send and receive shape is <code>[3MP]</code>; for <code>M=2, P=2</code>, it is <code>[12]</code>. Counts are fused; ID payloads still travel separately. {source:fused_split_layout}</p>',
}

NATIVE_ZH = r'''
<h1>TorchRec Row-wise Sharding</h1>
<p class="lead">Row-wise sharding 是 TorchRec 分布式 embedding 的一种分片方式，通过跨 rank 划分表行扩展存储与查表能力。本文以 <code>ShardedEmbeddingCollection</code> 为对象，介绍 KJT 输入组织、ID 分发、本地 lookup、输出顺序恢复与梯度回传，并用源码链接和序列图标明 forward、backward 中的 NCCL 通信、主机同步与数据依赖。</p>
<div class="note-box"><p>本文分析 TorchRec 提交 <a href="https://github.com/pytorch/torchrec/tree/1d87b8f79b7bb1671cb8be3e646e99e835cce610"><code>1d87b8f79b7bb</code></a> 中的 <code>ShardedEmbeddingCollection</code>，采用多 rank、CUDA/NCCL 和 eager 模式。它返回 unpooled sequence embeddings。基础例子使用固定 batch stride、无权重的 KJT，去重和通信 codec 单独作为可选分支说明。实现机制以这份 TorchRec 源码为依据；Pooled EmbeddingBag 的输出通信走另一条路径。</p></div>
{splits_primer}
<p class="reading-note">序列图从上往下阅读。生命线上的 activation bar 表示调用执行或数据访问区间，错开的窄条表示嵌套 self-call；虚线空心条表示尚未消费的异步请求。Stream 泳道中的 bar 对应提交阶段，长度不代表 GPU 耗时。整行色块用 <span class="seq-key seq-h2d">蓝色标 H2D</span>、<span class="seq-key seq-host">红色标 D2H / host sync</span>、<span class="seq-key seq-comm">紫色标 AllToAll</span>，黄色标 request wait，绿色标 GPU stream 依赖。图 3 的 D1 / D2 / D3 对应三处主机读回位置，实际 stall 次数取决于执行路径。点击消息文字或下方的文件行号可打开对应的 TorchRec 源码。图表默认适应宽度，也可放大或单独打开。</p>

<p class="reading-note">图中细分模块调用、异步请求和 backend 计算。消息下方的源码链接定位 TorchRec 调用点；GPU activity 编号、拷贝大小、kernel 名称和 optimizer 配置用于说明具体执行示例，实际运行会随输入、backend 和配置变化。阅读通信与同步时，以函数之间的数据依赖和 wait 位置为准。</p>
<h2 id="zh-layout">1. 行分片与 KJT</h2>
<p>假设 embedding 表有 8 行，每行 D 个元素，均匀分在两个 rank 上：rank 0 持有全局行 0-3，rank 1 持有全局行 4-7。每个 rank 都有自己的训练样本，但样本中的 ID 可以指向任何一段表。</p>
<div class="table-scroll"><table><thead><tr><th>请求 rank 0 的一个 feature</th><th>发往 rank 0</th><th>发往 rank 1</th></tr></thead><tbody><tr><td>全局 ID：<code>[6, 2, 6, 1]</code></td><td>本地 ID：<code>[2, 1]</code></td><td>本地 ID：<code>[2, 2]</code>，对应全局行 6</td></tr><tr><td>最终需要的向量</td><td colspan="2"><code>[E6, E2, E6, E1]</code>，保持原始 occurrence 顺序</td></tr></tbody></table></div>
<p>在这个等长、连续分片的例子中，<code>owner = id // 4</code>，<code>local_id = id % 4</code>。实际分桶还会读取分片的 block sizes 等信息，不能把这个简化公式直接用于所有 sharding plan。TorchRec 用 <code>KeyedJaggedTensor</code>（KJT）携带 feature keys、展平后的 ID values，以及各样本的 lengths / offsets；路由 ID 时必须一起重排这些边界信息。{source:bucket}</p>
<p>每次 lookup 在 rank 之间传输的是 ID 请求和查到的向量，embedding 表仍由各 rank 持有自己的分片。本地 lookup 处理来自所有请求 rank 的 ID，只访问本 rank 的行，然后把结果发回请求方。{source:rw}</p>

<h2 id="zh-native">2. Forward 数据流</h2>
<p><code>ShardedModule.forward</code> 创建 context 后，依次执行输入分发、本地计算和输出分发。省略类型标注后，调用顺序如下：</p>
<pre class="code" data-language="python">ctx = module.create_context()
dist_input = module.input_dist(ctx, features).wait().wait()
output = module.compute_and_output_dist(ctx, dist_input)
# output 是 lazy awaitable；消费结果时才完成输出等待与重建。</pre>
<p>两个 <code>wait()</code> 各完成一段工作。第一个取得接收尺寸并发起 KJT payload 通信；第二个消费 payload，重建本地 lookup 所需的 KJT。随后，<code>compute_and_output_dist</code> 查本地表并发起输出通信。{source:forward}；{source:compute}</p>
<p>图 1 按模块阶段概括通信。对于本文固定 stride、无 weights 的 KJT，每个 rank 的一个 row-wise group 在 forward 中发起 <strong>4 次 AllToAll：输入 splits、lengths、ID values 各 1 次，输出 embedding vectors 1 次</strong>。输入阶段先发起 splits，第一次 wait 时再发起 lengths 和 ID values。图中 IN / OUT 色块分别汇总这 3 次和 1 次调用；计数对应使用 NCCL backend 的 PyTorch collective，不是底层 NCCL send/recv 或 GPU kernel 的数量。Backward 的梯度通信另见第 5 节。{source:splits}；{source:tensors}；{source:seq}</p>
{figure:01}

<h2 id="zh-input">3. Input Distribution</h2>
<h3 id="zh-input-mapping">输入重排映射</h3>
<p><code>ShardedEmbeddingCollection.input_dist</code> 先按 sharding / lookup 需要的顺序重排 feature，再按组拆分。若开启 <code>use_index_dedup</code>，它会调用 <code>jagged_unique_indices</code>，保存原始 features 和 <code>reverse_indices</code>，并把去重后的 KJT 交给分桶逻辑。这是在请求 rank 的输入上做去重，并不是一次跨 rank 的全局去重。{source:input}；{source:prepare}</p>
<p>图 2 的 01 标记分桶前的条件读回：输入 KJT 的 <code>length_per_key</code> 未缓存且 CUDA lengths 非空时，<code>permute()</code> 在重排 kernel 之前触发 D2H；若跳过重排，则由后续 <code>split()</code> 首次触发。两处调用复用同一份主机计数，不能累计为两次读回。<code>offset_per_key()</code> 对缓存计数求 CPU 前缀和，不新增 D2H。{source:kjt_split_prepare}；{source:kjt_lengths}</p>
<p>Row-wise 分桶把 ID 按目标 rank 分组，生成 owner-local IDs 和新的 lengths，同时保存 <code>unbucketize_permute_tensor</code>。这张映射负责撤销路由导致的重排；可选的 <code>reverse_indices</code> 则负责把 unique 结果展开为原始的每一次出现。两者用途不同，不能互相替代。{source:bucket}</p>
{figure:02}

<h3 id="zh-input-waits">两阶段 AllToAll</h3>
<p>每个 rank 要接收多少 ID，取决于本批次的请求分布。TorchRec 因此先交换 split-size metadata，再按已知尺寸分配接收 buffer 并传输真正的 KJT 数据。</p>
<ol><li>发起 splits 通信。 <code>SplitsAllToAllAwaitable</code> 发起异步 <code>dist.all_to_all_single</code>，交换各 rank 之间需要发送的数据尺寸。</li><li>第一次 wait。 先消费 splits 的 Work，再把 CUDA 上的尺寸通过 <code>_safe_tolist_2d</code> 转成 Python lists。CPU 必须读到这些数值，才能决定接收尺寸。随后构造 tensors awaitable，并在其构造过程中发起 payload 通信。</li><li>传输 payload。 对于本文的基础 KJT，主要是 lengths 和 ID values 各自的 AllToAll；有 weights 或 variable stride 时，实际 tensor 列表会变化。</li><li>第二次 wait。 消费 payload 的 Work，执行 <code>KJT.dist_init</code>，把接收到的布局 recat 为 lookup 所需的 feature 布局，并整理 KJT metadata。</li></ol>
<p><code>Awaitable[Awaitable[KJTList]]</code> 对应的正是这两个阶段：外层确定接收尺寸并发起传输，内层把收到的数据整理成可用输入。因此，第一次 wait 返回时，ID payload 仍可能在传输。{source:splits}；{source:tensors}</p>
{figure:03}
<h3 id="zh-input-sync">等待与主机同步</h3>
<p>CPU 等待不只发生在接收 splits 之后。发起通信前，<code>KJT.dist_splits()</code> 就需要主机上的 <code>length_per_key</code>。若这个 metadata 尚未缓存，TorchRec 会对 CUDA lengths 求和，再通过 <code>_safe_tolist</code> 取回 Python list。接收 payload 后，固定 stride 分支的 <code>dist_init()</code> 又会对新 KJT 调用 <code>sync()</code>，整理它的 <code>length_per_key</code> 和 offsets metadata。{source:kjt_splits}；{source:kjt_lengths}；{source:kjt_init}</p>
<p>图 3 的 D1、D2、D3 分别标出分桶后的发送尺寸准备、接收尺寸读回和 KJT metadata 重建。分桶前的条件读回 01 位于图 2。非空 CUDA tensor 经过 safe-list 路径时，会先做 D2H，再显式同步当前 stream。{source:host_copy}；{source:splits}</p>
<p>图中的一个 H1 消息包含三次独立拷贝：H1-a、H1-b、H1-c 分别上传 lengths splits、values splits 和 stride。在固定 stride、无 weights 的路径上，每次 <code>torch.tensor(..., device=cuda)</code> 传输 <code>8P</code> 字节；之后才打包并发起 splits AllToAll。{source:split_h2d}</p>
<p>这个固定版本还在第一次 wait 中读回发送端 <code>_input_tensor</code>，用于检查 split sizes 的整数溢出，图中另标为 V2。这次读回发生在正常执行路径上，并不以发现错误为前提。因此，D1 / D2 / D3 标识三类主要数据依赖，不代表全部同步调用，也不代表每次运行恰好出现三次 stall。{source:split_validation}</p>
<p>逐项的传输方向、字节数与触发条件见<a href="#zh-host-transfers">主机与设备拷贝表</a>。表中 01 对应图 2 的同名标记，03–05 分别列出图 3 中 H1 包含的三次拷贝。</p>
<p>这些校验读回由 <a href="https://github.com/meta-pytorch/torchrec/commit/a950331f5d1778a25a3ff44fe3a255277e1338f2">PR #3978（<code>a950331f5</code>）</a>引入，最早包含它们的周版本是 <a href="https://github.com/meta-pytorch/torchrec/releases/tag/v2026.04.13.00"><code>v2026.04.13.00</code></a>；正式发布的 1.6.0 尚未包含，<a href="https://github.com/meta-pytorch/torchrec/releases/tag/v1.7.0-rc1">1.7.0</a> 已包含。最初使用 CUDA tensor 的 <code>.tolist()</code>，随后 <a href="https://github.com/meta-pytorch/torchrec/commit/ec5baf373ef8ef3ea82c23e4c3086815e7ffcd3f">PR #4131（<code>ec5baf373</code>）</a> 将其替换为 safe-list 路径，保留主机读回，并显式同步当前 stream。本文固定的 <code>1d87b8f79b7bb</code> 已包含这两次改动。</p>
<p>异步 collective 的 <code>Work.wait()</code> 标出消费通信结果的位置。仅凭这个调用，无法断定 CPU 会等待整张 GPU，也无法推断 NCCL 内部所有 stream 的行为。读图时应把这类通信依赖与必须拿到主机数值的 metadata 同步分开。</p>
<p>Recat 在本地重排数据，把通信接收时的 rank / feature 布局转成 lookup 所需的布局，这一步不发起跨 rank 通信。完成后，row owner 就有了各请求 rank 发来的 ID，可以开始查表；embedding 向量将在后面的输出分发阶段送回。</p>

<h2 id="zh-lookup">4. Lookup 与输出恢复</h2>
<h3 id="zh-lookup-local">本地 Lookup</h3>
<p><code>GroupedEmbeddingsLookup</code> 将本地 KJT 按兼容的 embedding 配置拆组，调用对应的 embedding kernel。以 fused backend 为例，<code>BatchedFusedEmbedding</code> 构造的 TBE 使用 <code>PoolingMode.NONE</code>，向 backend 传入 IDs 和 offsets，得到每个 ID 对应的向量。这里没有新增跨 rank collective。图中的 backend 计算与 TorchRec 包装层分开标出，便于区分输入准备和查表；具体 kernel 实现和数量取决于输入与 backend。{source:lookup}；{source:tbe}</p>
<p>调用 backend 前，TorchRec 还会取得 KJT offsets，并把 values / offsets 转成对应 backend 配置的 index / offset dtype。这些本地准备操作应与真正的查表区分开，不应仅凭它们处在 lookup 调用范围内就算成一次 embedding 访存。{source:tbe_call}</p>
{figure:04}
<h3 id="zh-output-a2a">输出 AllToAll</h3>
<p><code>SequenceEmbeddingsAllToAll</code> 把向量从 row owners 送回请求 ranks。<code>All2All_Seq_Req.forward</code> 先用 <code>forward_recat</code> 整理发送布局，按需执行通信 codec 的 encode，再发起异步 AllToAll。输出被消费时，<code>All2All_Seq_Req_Wait.forward</code> 消费通信请求并按需 decode。{source:output}；{source:seq}</p>
{figure:05}
<h3 id="zh-output-reconstruct">Lazy Wait 与顺序恢复</h3>
<p>收到向量后，恢复顺序分成两层：先通过 <code>unbucketize_permute_tensor</code> 回到分桶前的输入顺序；如果输入做过去重，再通过 <code>reverse_indices</code> 展开回原始 occurrences。最后按 feature 拆分并附上原始 lengths，构造 <code>Dict[str, JaggedTensor]</code>。默认路径用 <code>index_select</code> 展开，源码也提供可选的 <code>gather</code> 分支；两者承担相同的 occurrence 恢复任务。{source:jt}</p>
{figure:06}
<p>例如启用去重后，<code>[2, 6, 2]</code> 可以表示为 unique IDs <code>[2, 6]</code> 和映射 <code>[0, 1, 0]</code>。通信回来的 unique embeddings 是 <code>[E2, E6]</code>，展开后仍然必须得到 <code>[E2, E6, E2]</code>。Unique 的实际排列由算子返回，例子只说明 inverse mapping 的作用。</p>

<h2 id="zh-backward">5. Backward 与参数更新</h2>
<p>输出 embedding 的梯度沿 autograd 图回传，依次经过顺序恢复操作、反向 AllToAll 和本地 embedding kernel。图 7 展示整条路径，图 8 至图 12 展开各阶段；图中的 forward wrapper 和实际执行 backward 的 autograd node 分开列出。</p>
{figure:07}
<h3 id="zh-backward-reconstruct">输出重建的反向传播</h3>
<p>Backward 从下游对每个输出 embedding 的梯度开始。按 feature 拆开的向量先汇回对应的布局；若 forward 展开过 duplicate occurrences，反向要把这些位置的梯度加回同一个 unique 位置。例如 <code>[2, 6, 2]</code> 的三个 occurrence 梯度 <code>[g0, g1, g2]</code>，给 unique IDs 的梯度就是 <code>[g0 + g2, g1]</code>。接着，unbucketize 对应的张量操作把梯度恢复为输出 AllToAll 接收时的 bucket 布局。这是对 forward 中 tensor 操作的求导，不是依次调用各个 <code>nn.Module.backward()</code>。{source:jt}；{source:output}</p>
{figure:08}
<h3 id="zh-backward-a2a">反向 AllToAll</h3>
<p><code>All2All_Seq_Req_Wait.backward</code> 先发起反向 AllToAll，把请求 rank 上的向量梯度送回 row owners；它交换 forward 的 send / receive splits，并按需使用 backward codec。随后，沿 dummy tensor 建立的 autograd 依赖，<code>All2All_Seq_Req.backward</code> 消费这个请求，按需 decode，再用 <code>backward_recat</code> 恢复本地 lookup 的布局。若 <code>GRADIENT_DIVISION</code> 开启，还会除以 process-group size。{source:seq}</p>
{figure:09}
<h3 id="zh-backward-wait">请求端通信等待</h3>
<p>发起反向通信后，dummy gradient 继续推动 autograd 执行 request-side backward。这个节点先调用 <code>req.wait()</code>，再 decode、执行 backward recat，并按配置缩放梯度，最后把结果交回本地 lookup。</p>
{figure:10}
<h3 id="zh-backward-update">本地 Embedding 更新</h3>
<p>向量梯度回到本地 lookup 后，fused TBE 路径由 backend 在 backward 中完成其配置的 embedding 更新。TorchRec 暴露的 <code>EmbeddingFusedOptimizer.step()</code> 在此实现中设置 backend 的 learning rate，并不是另一次独立的逐行更新。模型其他参数由各自的 optimizer 管理，其他 compute kernel 的更新方式则取决于其实现。{source:tbe}；{source:fused}</p>
{figure:11}
<h3 id="zh-backward-boundary">整数输入边界</h3>
<p>输入 ID、lengths、offsets 是整数，EC 的输入准备和分发运行在 <code>torch.no_grad()</code> 内。因此，本文这条反向路径不会再把输入阶段的 splits、lengths、IDs AllToAll 各倒放一遍。需要跨 rank 返回的是 embedding 输出的梯度。{source:input}</p>
{figure:12}

<h2 id="zh-sync">6. 通信与同步汇总</h2>
<h3 id="zh-host-transfers">主机与设备拷贝</h3>
<p>仅统计每批执行的 TorchRec metadata 拷贝，不含输入 KJT 搬运。基础路径：单个 row-wise group、固定 stride、各 rank 的 batch size 相同，无 weights、去重、codec 或 collective tag。<code>P &gt; 1</code> 为 rank 数，<code>F</code> 为分桶前的 feature 数；下表字节数均按每 rank 计算。</p>
<div class="table-scroll"><table class="transfer-inventory"><thead><tr><th>序号</th><th>方向</th><th>阶段</th><th>数据（源码）</th><th>字节 / 批</th><th>必要性 / 条件</th></tr></thead><tbody>
<tr><td>01</td><td><span class="seq-key seq-host">D2H</span></td><td>输入重排 / 拆组</td><td>{source:kjt_split_prepare|分桶前各 feature 的 ID 数}</td><td><code>8F</code></td><td>按需；metadata 已缓存或 lengths 为空时跳过。</td></tr>
<tr><td>02 · D1</td><td><span class="seq-key seq-host">D2H</span></td><td>Splits 准备</td><td>{source:kjt_splits|各 rank × feature 的 ID 数}</td><td><code>8FP</code></td><td>当前非空路径需要；分桶后的计数重新计算。</td></tr>
<tr><td>03 · H1-a</td><td><span class="seq-key seq-h2d">H2D</span></td><td>Splits 发起前</td><td>{source:split_sizes_h2d|Lengths splits}</td><td><code>8P</code></td><td>当前实现需要；交换 lengths 元素数。</td></tr>
<tr><td>04 · H1-b</td><td><span class="seq-key seq-h2d">H2D</span></td><td>Splits 发起前</td><td>{source:split_sizes_h2d|Values splits}</td><td><code>8P</code></td><td>当前实现需要；交换 ID 数。</td></tr>
<tr><td>05 · H1-c</td><td><span class="seq-key seq-h2d">H2D</span></td><td>Splits 发起前</td><td>{source:split_stride_h2d|Stride}</td><td><code>8P</code></td><td>固定 stride 路径；交换 batch size。</td></tr>
<tr><td>06 · D2</td><td><span class="seq-key seq-host">D2H</span></td><td>第一次 wait</td><td>{source:split_d2h|接收端 splits + stride}</td><td><code>24P</code></td><td>需要；确定 payload 接收尺寸。</td></tr>
<tr><td>07 · V2</td><td><span class="seq-key seq-host">D2H</span></td><td>第一次 wait</td><td>{source:split_validation|发送端 splits + stride 校验}</td><td><code>24P</code></td><td>校验额外读回；非算法必需。</td></tr>
<tr><td>08 · H2</td><td><span class="seq-key seq-h2d">H2D</span></td><td>第一次 wait</td><td>{source:input_recat|输入 recat 索引}</td><td><code>4FP</code></td><td>当前每批上传；固定布局可复用。</td></tr>
<tr><td>09 · D3</td><td><span class="seq-key seq-host">D2H</span></td><td>第二次 wait</td><td>{source:kjt_init|接收 KJT 各 feature 的总 ID 数}</td><td><code>8F</code></td><td>当前非空路径需要；重建主机 metadata。</td></tr>
</tbody></table></div>
<p>D2H 经 safe-list 读回并同步<strong>当前 stream</strong>；H2D 为普通 CUDA tensor 构造的阻塞拷贝。整数 lengths 求和得到 int64，因此计数按 <code>8 B</code> 计算。{source:host_copy|同步实现}；{source:kjt_lengths|计数实现}。</p>
<div class="note-box"><p><strong>V2 在正常路径上执行。</strong>关闭 overflow debug 不会消除读回。D2 / V2 都复制完整 metadata，而非仅校验所用的最后一行。</p></div>
<p>例如 <code>P=8, F=1</code>：D1 + D2 + V2 + D3 合计 <strong>456 B D2H</strong>、四处显式同步；H1 + H2 合计 <strong>224 B H2D</strong>。01 若触发，再加 <code>8 B</code> D2H 和一次同步。等待包含 stream 上的前置工作，不能由字节数推算耗时。</p>
<h3 id="zh-transfer-conditions">条件触发的拷贝</h3>
<p>满足相应配置或 pipeline 路径时，按每批额外计入以下拷贝。</p>
<div class="table-scroll"><table class="transfer-inventory"><thead><tr><th>序号</th><th>方向</th><th>阶段</th><th>数据（源码）</th><th>字节</th><th>必要性 / 条件</th></tr></thead><tbody>
<tr><td>10</td><td><span class="seq-key seq-h2d">H2D</span></td><td>第一次 wait</td><td>{source:input_recat|Recat 的 input / output offsets}</td><td>额外 <code>8(FP+1)</code></td><td>仅各 rank 的 batch size 不同。</td></tr>
<tr><td>11</td><td><span class="seq-key seq-h2d">H2D</span><br><span class="seq-key seq-host">D2H</span></td><td>Splits 校验</td><td>{source:collective_tag|Collective 一致性 tag}</td><td>H2D +<code>8P</code><br>D2、V2 各 +<code>8P</code></td><td>仅启用 tag 校验；并入 D2/V2，不新增 D2H 同步调用。</td></tr>
<tr><td>12 · V1</td><td><span class="seq-key seq-host">D2H</span></td><td><a href="torchrec-sparse-dist-pipeline.html#zh-pipeline-distribution">Pipeline 融合前</a></td><td>{source:fused_validation|逐个 split tensor 校验}</td><td>每份 <code>8P</code><br>基础 KJT 合计 <code>24P</code></td><td>每份各同步一次；额外校验，直接 row-wise 不发生。</td></tr>
</tbody></table></div>
<p>VBE、不均匀分桶、weights、codec 和 backend 内部拷贝另计；NCCL AllToAll 与本地 D2D 不计入 H2D / D2H。</p>
<h3 id="zh-rank-communication">跨 rank 通信</h3>
<div class="table-scroll"><table><thead><tr><th>阶段</th><th>跨 rank 传输</th><th>结果在哪消费</th><th>需要区分的同步</th></tr></thead><tbody>
<tr><td>发送 metadata 准备</td><td>无</td><td><code>dist_splits → length_per_key</code></td><td>未缓存时，CUDA lengths 汇总后读回主机</td></tr>
<tr><td>Input splits</td><td>Split sizes</td><td>外层 awaitable 的 wait</td><td>CUDA sizes 转 Python lists，存在明确的 CPU 等待</td></tr>
<tr><td>Input payload</td><td>KJT lengths、ID values；其他字段视配置而定</td><td>内层 awaitable 的 wait</td><td>消费通信结果；KJT recat 后 sync 会准备主机 metadata</td></tr>
<tr><td>Local lookup</td><td>无</td><td>本地 embedding kernel</td><td>依赖 owner-local KJT 就绪</td></tr>
<tr><td>Output distribution</td><td>Embedding vectors</td><td>lazy output 被消费时</td><td>通信结果可用后 decode、unbucketize、恢复 occurrences</td></tr>
<tr><td>Backward distribution</td><td>Embedding vector gradients</td><td>Req.backward</td><td>反向通信结果可用后 recat，再进入本地 lookup backward</td></tr>
</tbody></table></div>
<p>对于单个通信组、无额外 KJT 字段的基础路径，AllToAll 调用分别传输输入 splits、lengths、values，输出 embeddings，以及反向 embedding gradients。这个计数描述调用层面的五类通信。多个 sharding group、可选字段和后面的 metadata 融合会改变调用组织方式，NCCL kernel 数量也不能直接由它推出；其他模型参数的通信另计。{source:splits}；{source:tensors}；{source:seq}</p>
<p>一个 batch 按以下依赖执行：ID 路由完成 → 本地 lookup → embedding 回传与恢复 → 下游计算 → 梯度回传 → 本地更新。输入分发还包含一条 CPU 依赖：主机必须先读到 split-size metadata，才能发起对应 payload。这些先后关系也约束着多个 batch 之间可以重叠的工作。</p>

<h2 id="zh-sources">源码与图表索引</h2>
<p>这 12 张图分别展开 forward 与 backward，各有 6 张。输入分发图标出 H2D、三处 host read 和各次 AllToAll；输出通信与结果重建、反向 launch 与 finalize、本地更新与梯度边界分别列出，方便回查。源码链接对应本文固定的 TorchRec 版本。</p>
{figure_index}
<p>阅读源码时，可以从 {source:forward} 的两个 wait 开始，沿 {source:splits}、{source:tensors} 到 {source:seq}，对照通信请求的发起与消费位置。</p>
<p class="series-next">同系列文章：<a href="torchrec-sparse-dist-pipeline.html">TorchRec Sparse Dist Pipeline</a>。</p>
'''

PIPELINE_ZH = r'''<h1>TorchRec Sparse Dist Pipeline</h1>
<p class="lead">TorchRec 的 sparse dist pipeline 通过跨 batch 调度，将后续输入的准备和分发与当前 batch 的训练重叠。本文比较 <code>TrainPipelineSparseDist</code> 与 <code>PrefetchTrainPipelineSparseDist</code> 的执行流程，重点说明两阶段输入通信、batch context 交接、CUDA stream 依赖和 embedding prefetch 的缓存条件，并用序列图与时间线呈现启动、稳定运行和排空过程。</p>
<div class="note-box"><p>本文分析 TorchRec 提交 <a href="https://github.com/pytorch/torchrec/tree/1d87b8f79b7bb1671cb8be3e646e99e835cce610"><code>1d87b8f79b7bb</code></a> 中的两种 sparse dist pipeline，以多 rank、eager CUDA/NCCL 下的 <code>ShardedEmbeddingCollection</code> 为例。它返回 unpooled sequence embeddings，基础输入是固定 batch stride、无权重的 KJT。实现机制以这份 TorchRec 源码为依据。</p></div>
<p>Row-wise sharding 把 embedding 表按行分到多个 rank。每个 rank 的样本可能请求其他 rank 持有的行，所以输入分发要把 ID 送到对应的 row owner。<code>KeyedJaggedTensor</code>（KJT）携带 feature keys、ID values 和 lengths / offsets。Row owner 收到输入后查本地表，再通过输出 AllToAll 把向量发回请求方；backward 则沿相反方向回传向量梯度。Pipeline 主要提前调度输入准备和分发，本地 lookup、输出通信和 backward 仍由当前 batch 的模型执行。{source:rw}；{source:input}；{source:seq}</p>
{splits_primer}
<p>输入分发分两次等待。第一次消费 split-size metadata，读回接收尺寸并发起 KJT payload 通信；第二次消费 payload，重建本地 lookup 所需的 KJT。第一次返回时，payload 仍可能在传输。Pipeline 可以把这两个阶段安排在不同位置，提前推进后续 batch 的输入准备。各次 AllToAll 的细分调用也可参阅本系列的<a href="torchrec-row-wise-sharding.html#zh-input">row-wise 输入分发</a>。{source:forward}；{source:splits}；{source:tensors}</p>
<p>这里的 CPU 同步来自 metadata：发送前需要准备各 rank 的 split sizes，第一次 wait 要把接收尺寸从 CUDA 读成 Python lists，第二次 wait 的固定 stride 分支还会整理新 KJT 的 lengths / offsets。非空 CUDA tensor 走 <code>_safe_tolist</code> 路径时，会做 D2H 并同步当前 stream；已经缓存的 metadata 可以跳过重新计算。单独看到 <code>Work.wait()</code>，则不能据此断定 CPU 会等待整张 GPU。{source:kjt_splits}；{source:kjt_init}；{source:host_copy}</p>
<p class="reading-note">序列图从上往下表示主机提交顺序和逻辑依赖。Activation bar 表示调用或访问区间，错开的窄条表示嵌套 self-call，虚线空心条表示尚未消费的请求；stream 泳道和 bar 长度不代表实测 GPU 耗时。<span class="seq-key seq-h2d">蓝色标 H2D</span>、<span class="seq-key seq-host">红色标 D2H / host sync</span>、<span class="seq-key seq-comm">紫色标 AllToAll</span>，黄色标 request wait，绿色标 stream 依赖。D1 / D2 / D3 与 row-wise 文章的读回位置一一对应；V1 / V2 标出固定版本中的额外校验读回。实际 stall 次数取决于 metadata 缓存和执行路径。点击消息或文件行号可打开源码，所有图默认适应宽度。</p>
<h2 id="zh-pipeline">1. Pipeline 调度机制</h2>
<p>训练处理 batch <code>i</code> 时，下一批 <code>i+1</code> 的 ID 已经可以从输入中取出。它的 row-wise 输入分发不依赖当前 batch 的模型输出，所以 TorchRec 可以提前发起这部分工作。当模型执行到下一批的 embedding 调用时，就可以继续处理之前发起的请求。</p>
<p>TorchRec 通过 tracing / rewrite 找到输入可以提前取出的 sharded module，并改写它的 <code>forward</code>。调度器提前创建 module context、调用 <code>input_dist</code>；模型执行到该模块时，runtime wrapper 从当前 batch 的 context 取回请求和状态，再调用 <code>compute_and_output_dist</code>。本地 lookup、输出 AllToAll 和 backward 仍按原有依赖执行。只有满足改写条件的调用才能采用这种调度。{source:rewrite}；{source:runtime}</p>
<h3 id="zh-pipeline-distribution">Input Dist 的启动与等待</h3>
<ul><li><code>start_sparse_data_dist(batch, ctx)</code>：调用输入分发，并组织可融合的 splits 通信。兼容的 metadata 可按 process group 合并；这不意味着所有 ID payload 合成了一个 collective。</li><li><code>wait_sparse_data_dist(ctx)</code>：消费 fused splits awaitables，把得到的 tensors requests 存入 <code>input_dist_tensors_requests</code>。在这个过程中发起 payload 通信；函数返回时，payload 仍可在进行。</li></ul>
<p>两种 pipeline 把第二次 wait 放在不同位置。普通版本在 <code>PipelinedForward</code> 中等待并重建输入；prefetch 版本在 <code>prefetch_embeddings</code> 中完成这一步，因为缓存预取需要已经分发好的 ID。{source:wait}；{source:prefetch_helper}</p>
<p>Pipeline 改变这些操作的调度位置。<code>KJTAllToAllForward</code> 仍会调用 <code>dist_splits()</code> 取得主机发送尺寸，融合 splits 也仍需读回接收尺寸。第二次 wait 则必须把收到的 KJT 整理好，才能交给 lookup 或 prefetch。{source:pipeline_splits}；{source:kjt_init}</p>
<div class="table-scroll"><table><thead><tr><th>读回位置</th><th>主机需要的数据</th><th>普通 Pipeline</th><th>Prefetch Pipeline</th></tr></thead><tbody>
<tr><td>D1 · 发送尺寸</td><td>分桶后 KJT 的 <code>length_per_key</code>；未缓存的非空 CUDA lengths 需读回</td><td><code>start_sparse_data_dist(i+1)</code> 内，splits 发起前</td><td><code>start_sparse_data_dist(i+2)</code> 内，本轮末尾</td></tr>
<tr><td>D2 · 接收尺寸</td><td>Splits AllToAll 的输出；决定 payload 接收 buffer 大小</td><td><code>wait_sparse_data_dist(i+1)</code> 内，当前 forward 返回后</td><td><code>wait_sparse_data_dist(i+1)</code> 内，当前 forward 之前</td></tr>
<tr><td>D3 · KJT metadata</td><td><code>dist_init().sync()</code> 为新 KJT 构建主机 lengths / offsets metadata</td><td><code>PipelinedForward(i)</code> 的第二次 wait 内</td><td><code>prefetch_embeddings(i+1)</code> 的第二次 wait 内</td></tr>
</tbody></table></div>
<p>沿同一个 batch 看，主要依赖仍是 <code>D1 → splits → D2 → payload → D3</code>。沿一次 <code>progress(i)</code> 看，普通版本是 <code>D1(i+1) → D3(i) → D2(i+1)</code>，prefetch 版本是 <code>D2(i+1) → D3(i+1) → D1(i+2)</code>。跨 batch 的交错调度使图中的编号不按数值递增。</p>
<aside class="note-box" id="zh-fused-splits-sync" role="note" aria-labelledby="zh-fused-splits-sync-title">
<p id="zh-fused-splits-sync-title"><strong>Fused splits 的额外主机同步（V1）</strong></p>
<p>在本文固定版本的 eager CUDA 路径中，fused-splits 构造阶段引入了额外的主机读回：<code>FusedKJTListSplitsAwaitable</code> 在发起 splits AllToAll 前，逐个对 CUDA split tensor 调用 <code>_safe_tolist</code>，执行 D2H，并通过 <code>current_stream().synchronize()</code> 阻塞 CPU，直到当前 stream 的前序工作和拷贝完成。{source:fused_validation}；{source:host_copy}</p>
<p>这是该版本校验实现带来的额外开销。<strong>关闭 <code>TORCHREC_OVERFLOW_DEBUG</code> 仍会执行读回与同步</strong>，因为调试开关在读回之后的检查函数内判断。循环按 split tensor 执行，因此图中一个 V1 标记可能包含多次同步调用。</p>
</aside>
<p>V2 则位于 splits 的第一次 wait 内，对发送端 <code>_input_tensor</code> 调用 <code>_safe_tolist_2d</code>。这次校验读回同样发生在检查函数判断调试开关之前，并产生 D2H 与主机等待。{source:split_validation}</p>
<p>这些校验读回由 <a href="https://github.com/meta-pytorch/torchrec/commit/a950331f5d1778a25a3ff44fe3a255277e1338f2">PR #3978（<code>a950331f5</code>）</a>引入，最早包含它们的周版本是 <a href="https://github.com/meta-pytorch/torchrec/releases/tag/v2026.04.13.00"><code>v2026.04.13.00</code></a>；正式发布的 1.6.0 尚未包含，<a href="https://github.com/meta-pytorch/torchrec/releases/tag/v1.7.0-rc1">1.7.0</a> 已包含。最初使用 CUDA tensor 的 <code>.tolist()</code>，随后 <a href="https://github.com/meta-pytorch/torchrec/commit/ec5baf373ef8ef3ea82c23e4c3086815e7ffcd3f">PR #4131（<code>ec5baf373</code>）</a> 将其替换为 safe-list 路径，保留主机读回，并显式同步当前 stream。本文固定的 <code>1d87b8f79b7bb</code> 已包含这两次改动。</p>
<p>V1 属于 pipeline 的 fused-splits 构造路径；直接调用 row-wise 模块时不经过这一融合步骤。V2 位于两条路径共用的 <code>SplitsAllToAllAwaitable._wait_impl</code>，因此本系列两篇文章都标注 V2。两篇文章使用相同的源码提交。</p>
{figure:13}
<h3 id="zh-pipeline-streams">Stream 依赖与生命周期</h3>
<p>交接输入和 module context 时，TorchRec 分别处理执行顺序和存储生命周期。<code>wait_stream</code> 让消费者的 GPU 工作等待生产者；<code>record_stream</code> 记录 tensor 在另一个 stream 上的使用，避免 allocator 过早复用它的存储。通信结果是否就绪仍由执行依赖保证，<code>record_stream</code> 不承担等待。{source:stream}；{source:runtime}</p>

<h2 id="zh-sparse">2. 普通 Sparse Dist Pipeline</h2>
<p>普通 sparse dist pipeline 分别调度 H2D、input distribution 和训练，最多容纳三个在途 batch。稳定态时，<code>i</code> 做本次 forward / backward，<code>i+1</code> 做输入分发，<code>i+2</code> 从 dataloader 入队并拷到 GPU。以下采用默认配置 <code>enqueue_batch_after_forward=False</code>。{source:ordinary}</p>
<pre class="code" data-language="python"># 稳定态语义示意；省略边界检查与配置分支。
zero_grad()
wait_for_current_batch(i)
start_sparse_data_dist(i + 1)   # 发起 splits
enqueue_batch(i + 2)           # H2D
losses, output = model(i)      # wrapper 内做 i 的第二次 wait
wait_sparse_data_dist(i + 1)   # 第一阶段 wait；发起 payload
backward(losses)
optimizer_step()
dequeue_batch(i)</pre>
{figure:14}
<p>当 batch <code>i</code> 的 forward 到达 embedding 模块，<code>PipelinedForward</code> 从 context 取出当前 batch 的 tensors request，在 data_dist stream 的上下文中调用 <code>request.wait()</code>，完成 KJT 重建。训练 stream 随后等待 data_dist stream 的相关工作，并接过输入与 context，继续 lookup 和输出通信。{source:runtime}</p>
<p>下一批 <code>i+1</code> 的 splits 在当前 forward 之前发起；它的 payload 要等当前 forward 返回后、backward 提交前才发起。这样，splits 有机会与当前 forward 重叠，payload 有机会与当前 backward 重叠。设置 <code>enqueue_batch_after_forward=True</code> 会把 H2D 入队移到 forward 之后，仍采用普通 pipeline 的调度。{source:ordinary}</p>
<p>普通版本没有单独调度 cache prefetch，lookup 内部的缓存管理由 backend 配置决定。实际能重叠多少工作，还取决于 metadata 的 CPU 等待、collective 次序、GPU 资源竞争和 kernel 时长。多个 stream 提供了调度空间，并不保证通信耗时都能被计算覆盖。</p>

<h3 id="zh-multi-iteration">跨迭代调度</h3>
<p>沿三次连续的 <code>progress</code> 看，同一个 batch 会依次经过搬运、分发和计算。图 3 默认追踪 <code>N+2</code>：它在 <code>progress(N)</code> 搬到 GPU，在 <code>progress(N+1)</code> 做 input distribution，在 <code>progress(N+2)</code> 被消费并计算。选择阶段或点击操作，可以查看相应依赖和 TorchRec 源码。{source:ordinary}；{source:runtime}</p>
<p>图 3 的 A1-A4 按一次 progress 内的提交顺序编号：<code>splits(N+1) → output dist(N) → lengths(N+1) → ID values(N+1)</code>。其中既有当前 batch 的工作，也有下一批的工作，编号表示本次 progress 内的提交次序。Backward 仍有 embedding 梯度 AllToAll，只是没有计入这四个 input / forward 标记。图中分别标出 Python forward 返回和 GPU forward 完成，红色标记覆盖 D1 / D2 / D3 及 V1 / V2 的主机读回，并标明 batch。{source:ordinary}；{source:host_copy}；{source:seq}</p>
{figure:15}

<h2 id="zh-prefetch">3. Prefetch Pipeline</h2>
<p>Prefetch 版本在 input distribution 之后，单独调度 embedding prefetch。需要缓存的 backend 用分发后的 owner-local IDs 提前准备本地查表所需的缓存；真正的 lookup 仍在当前 batch 的 forward 中执行。<code>ShardedEmbeddingModule.prefetch</code> 把各组输入交给对应 lookup 的 <code>prefetch</code>。{source:prefetch_module}；{source:cache}</p>
<h3 id="zh-prefetch-waits">Payload 与 Prefetch 调度</h3>
<p>在固定版本里，下一批的 <code>wait_sparse_data_dist(i+1)</code> 被放在当前 forward <strong>之前</strong>，所以下一批的 ID payload 有机会与当前 forward 重叠。当前 forward 返回后，<code>_prefetch(i+1)</code> 才消费 payload、重建 KJT，并发起 prefetch；之后提交当前 batch 的 backward / optimizer，最后再启动 <code>i+2</code> 的 splits。{source:prefetch}</p>
<pre class="code" data-language="python"># 稳定态语义示意；i+1 的 splits 已在此前启动。
zero_grad()
wait_for_prefetch(i)
enqueue_batch(i + 2)
wait_sparse_data_dist(i + 1)   # 先发起下一批 payload
losses, output = model(i)      # 消费 i 的 post-prefetch input/context
clear_consumed_prefetch_state(i)
prefetch(i + 1)                # 第二次 wait + backend prefetch
backward(losses)
optimizer_step()
start_sparse_data_dist(i + 2)  # 准备下一次 progress
dequeue_batch(i)</pre>
{figure:16}
<p><code>prefetch_embeddings</code> 在 data_dist stream 中做第二次 <code>request.wait()</code>；prefetch stream 等待该 stream 后，调用模块的 <code>prefetch</code>，并保存 <code>module_input_post_prefetch</code> 与 <code>module_contexts_post_prefetch</code>。下次 forward 的 <code>PrefetchPipelinedForward</code> 直接取这两份状态，让训练 stream 等待 prefetch stream，再执行 <code>compute_and_output_dist</code>，不再在那里消费 input payload request。{source:prefetch_helper}；{source:preforward}</p>
<h3 id="zh-prefetch-backend">Prefetch 后端约束</h3>
<p><code>GroupedEmbeddingsLookup</code> 只为需要预取的 compute kernel 执行 prefetch，例如 <code>FUSED_UVM_CACHING</code>，其他路径可以直接返回。代码检查的 TBE backend 还要求正确设置 <code>prefetch_pipeline</code>，否则 TorchRec 会记录错误，指出 backward 使用的 cache locations 可能不正确。缓存位置的正确性依赖这些 backend 配置和约束，单独增加 CUDA stream 无法保证。{source:need_prefetch}；{source:cache}</p>
<p>在 <code>progress()</code> 中，主机先调用 <code>_prefetch(i+1)</code>，再提交 <code>backward(i)</code>。源码没有在这两次调用之间设置统一的 host barrier 来等待下一批 prefetch 完成。两者能否重叠、backend 如何保护 cache locations，要结合 stream 和 cache 约束判断；图中的提交顺序也不能直接换算成 GPU 并行耗时。{source:prefetch}</p>
<p class="reading-note">图中的 H2D、input distribution、prefetch 和训练泳道按工作角色划分，底层可能还有其他 CUDA/NCCL streams。这个版本另外创建了一个新 Stream 对象，变量名为 <code>_default_stream</code>，并通过 <code>forward_stream</code> 参数传给 prefetch helper。这里的变量名并不表示 CUDA 默认 stream。{source:prefstreams}；{source:prefetch_helper}</p>

<h2 id="zh-compare">4. Pipeline 对比</h2>
<div class="table-scroll"><table><thead><tr><th>比较点</th><th>TrainPipelineSparseDist</th><th>PrefetchTrainPipelineSparseDist</th></tr></thead><tbody>
<tr><td><code>i+1</code> 的 splits 启动</td><td>本次 progress 的 forward 前</td><td>前一次 progress 尾部，或首次 fill 时</td></tr>
<tr><td><code>i+1</code> 的 payload 启动</td><td><code>forward(i)</code> 返回后</td><td><code>forward(i)</code> 之前</td></tr>
<tr><td>第二次 input wait</td><td>本 batch 的 <code>PipelinedForward</code></td><td>本 batch 的 <code>prefetch_embeddings</code></td></tr>
<tr><td>进入 embedding forward 时的状态</td><td>待消费的 tensors request + module context</td><td>已重建的 input + post-prefetch context</td></tr>
<tr><td>训练 stream 接入</td><td>等待 data_dist stream</td><td>等待 prefetch stream</td></tr>
<tr><td>独立的 backend prefetch 阶段</td><td>无</td><td>有；backend 可能无需执行实际缓存预取</td></tr>
<tr><td>当前 batch 的实际计算</td><td colspan="2">本地 lookup → 输出 AllToAll → 下游计算 → backward / 反向 AllToAll → optimizer</td></tr>
</tbody></table></div>
<p>在本文的源码版本中，prefetch 版本除了多出预取阶段，还改变了 payload 发起时机、第二次 wait 的位置，以及 context 中保存的内容。对照调度时需要一起看这些差异。{source:ordinary}；{source:prefetch}</p>
<h3 id="zh-pipeline-fill-drain">启动、稳态与排空</h3>
<p>启动时，普通版本先为第一批发起 input distribution，执行第一次 wait，取得 tensors request，再把第二批入队。Prefetch 版本还要完成第一批的第二次 wait 和 prefetch，然后启动第二批的 splits。第一批没有前一批计算可以覆盖这些准备工作，所以启动耗时要单独分析。{source:fill}；{source:prefill}</p>
<p>进入稳定态后，batch 与 context 始终配对移动。Runtime 消费模块请求时，会从对应字典中 pop；batch 出队时，也要移走匹配的 context。这里假设被改写的 embedding 模块每次 forward 只调用一次，重复消费会报错。队列最多容纳三批，实际在途数量可以更少，显存占用也不能简单按单批大小乘三。{source:fill}；{source:runtime}</p>
<p>默认 <code>execute_all_batches=True</code> 时，dataloader 耗尽后仍会执行已经入队的批次；没有 <code>i+1</code> 或 <code>i+2</code> 时，相应预备步骤会被跳过。评估模式则不会执行 training 分支中的 backward / optimizer。首尾阶段因此与上面的三批稳定态序列不同。{source:fill}；{source:ordinary}；{source:prefetch}</p>

<h2 id="zh-sources">源码与图表索引</h2>
<p>图 1 比较两种 pipeline 的 context 交接；图 2 和图 4 分别展开普通版本与 prefetch 版本的稳定态调用；图 3 沿三次 progress 追踪同一个 batch。三张序列图和交互时间线都按本文源码版本解释调度与依赖。</p>
{figure_index}
<p>对照 {source:ordinary} 和 {source:prefetch}，可以看到 payload 的发起位置不同；继续查看 {source:runtime} 和 {source:prefetch_helper}，则能定位第二次 wait 以及 context 的交接。</p>
<p class="series-next">同系列文章：<a href="torchrec-row-wise-sharding.html">TorchRec Row-wise Sharding</a>。</p>
'''

NATIVE_EN = r'''
<h1>TorchRec row-wise sharding</h1>
<p class="lead">Row-wise sharding distributes embedding-table rows across ranks to scale storage and lookup in TorchRec. Using <code>ShardedEmbeddingCollection</code>, this article covers KJT inputs, ID distribution, local lookup, output reconstruction and gradient return. Source-linked sequence diagrams identify NCCL communication, host synchronization and data dependencies in forward and backward execution.</p>
<div class="note-box"><p>The implementation described here is <code>ShardedEmbeddingCollection</code> at TorchRec commit <a href="https://github.com/pytorch/torchrec/tree/1d87b8f79b7bb1671cb8be3e646e99e835cce610"><code>1d87b8f79b7bb</code></a>, running in eager mode across multiple ranks with CUDA/NCCL. It returns unpooled sequence embeddings. The baseline uses an unweighted KJT with fixed batch stride; deduplication and communication codecs appear as optional branches. All implementation explanations refer to this TorchRec source. Pooled EmbeddingBag output distribution follows a different path.</p></div>
{splits_primer}
<p class="reading-note">Read each sequence from top to bottom. Activation bars mark execution or data-access scopes, and offset bars mark nested self-calls. Hollow dashed bars represent unconsumed asynchronous requests. Bars in stream lanes show submission stages; their lengths do not measure GPU time. Full-row bands mark <span class="seq-key seq-h2d">H2D in blue</span>, <span class="seq-key seq-host">D2H / host sync in red</span>, and <span class="seq-key seq-comm">AllToAll in purple</span>. Amber marks request waits, and green marks GPU stream dependencies. D1 / D2 / D3 in Fig. 3 identify three host-read sites; the number of runtime stalls depends on the execution path. Click a message or its file:line label to open the corresponding TorchRec source. Diagrams fit the available width by default and can be enlarged or opened separately.</p>

<p class="reading-note">The diagrams separate module calls, asynchronous requests, and backend computation. Source links below messages locate TorchRec callsites. GPU activity IDs, copy sizes, kernel names, and optimizer settings illustrate specific executions and can vary with inputs, backends, and configuration. Function dependencies and wait locations describe the communication and synchronization mechanism.</p>
<h2 id="en-layout">1. Row sharding and KJT</h2>
<p>Consider an eight-row embedding table with D elements per row. Rank 0 owns global rows 0-3 and rank 1 owns rows 4-7. Each rank receives its own training examples, whose IDs may refer to either shard.</p>
<div class="table-scroll"><table><thead><tr><th>One feature requested by rank 0</th><th>Send to rank 0</th><th>Send to rank 1</th></tr></thead><tbody><tr><td>Global IDs: <code>[6, 2, 6, 1]</code></td><td>Local IDs: <code>[2, 1]</code></td><td>Local IDs: <code>[2, 2]</code>, both referring to global row 6</td></tr><tr><td>Required output</td><td colspan="2"><code>[E6, E2, E6, E1]</code>, in original occurrence order</td></tr></tbody></table></div>
<p>For this equally sized, contiguous partition, <code>owner = id // 4</code> and <code>local_id = id % 4</code>. The actual bucketization code takes shard block sizes and other metadata; this simple formula is not universal. TorchRec carries feature keys, flattened ID values, and per-example lengths / offsets in a <code>KeyedJaggedTensor</code> (KJT). Routing values must preserve the corresponding sequence boundaries. {source:bucket}</p>
<p>Each lookup exchanges ID requests and result vectors while the table remains partitioned across ranks. A local lookup handles requests from all participating ranks, reads only its own table shard, and sends the results back to the requesters. {source:rw}</p>

<h2 id="en-native">2. Forward data flow</h2>
<p><code>ShardedModule.forward</code> creates a context, distributes input, then runs local computation and output distribution. With type annotations omitted, the call order is:</p>
<pre class="code" data-language="python">ctx = module.create_context()
dist_input = module.input_dist(ctx, features).wait().wait()
output = module.compute_and_output_dist(ctx, dist_input)
# Consuming the lazy output completes output waiting and reconstruction.</pre>
<p>The two waits represent different stages. The first obtains receive sizes and launches KJT payload communication. The second consumes that payload and reconstructs the KJT needed by the local lookup. <code>compute_and_output_dist</code> then performs local computation and initiates output distribution. {source:forward}; {source:compute}</p>
<p>Figure 1 summarizes communication by module stage. With the fixed-stride, unweighted KJT used here, each rank issues <strong>4 forward AllToAll calls per row-wise group: one each for input splits, lengths, and ID values, plus one for output embedding vectors</strong>. Splits launch first; the first wait then launches lengths and ID values. The IN / OUT bands summarize these 3 and 1 calls. These are PyTorch collective calls using the NCCL backend; the count does not describe underlying NCCL send/recv operations or GPU kernels. Section 5 covers backward gradient communication separately. {source:splits}; {source:tensors}; {source:seq}</p>
{figure:01}

<h2 id="en-input">3. Input distribution</h2>
<h3 id="en-input-mapping">Input permutation maps</h3>
<p><code>ShardedEmbeddingCollection.input_dist</code> orders features for the sharding and lookup layout, then splits them into groups. With <code>use_index_dedup</code>, it calls <code>jagged_unique_indices</code>, saves the original features and <code>reverse_indices</code>, and sends the deduplicated KJT into bucketization. This deduplicates inputs on the requesting rank; it is not a cross-rank global deduplication operation. {source:input}; {source:prepare}</p>
<p>Marker 01 in Fig. 2 is the conditional read before bucketization. When the input KJT's <code>length_per_key</code> is uncached and CUDA lengths are nonempty, <code>permute()</code> triggers D2H before its reorder kernels. If permutation is skipped, the first read occurs in <code>split()</code>. These calls reuse the same host counts; they do not count as two readbacks. <code>offset_per_key()</code> computes a CPU prefix sum from cached counts without another D2H. {source:kjt_split_prepare}; {source:kjt_lengths}</p>
<p>Row-wise bucketization groups IDs by destination rank, producing owner-local IDs and new lengths. It also saves <code>unbucketize_permute_tensor</code>, which reverses the routing permutation. The optional <code>reverse_indices</code> mapping expands unique results back to their original occurrences. These mappings solve distinct problems. {source:bucket}</p>
{figure:02}

<h3 id="en-input-waits">Two-stage AllToAll</h3>
<p>Receive sizes depend on this batch's requests. TorchRec first exchanges split-size metadata, then allocates receive buffers and transfers the KJT payload.</p>
<ol><li>Launch splits. <code>SplitsAllToAllAwaitable</code> issues asynchronous <code>dist.all_to_all_single</code> for the sizes exchanged between ranks.</li><li>First wait. Consume the splits Work and convert CUDA sizes to Python lists through <code>_safe_tolist_2d</code>. The host needs these values to determine receive sizes. Constructing the tensors awaitable then launches payload communication.</li><li>Transfer payload. The baseline KJT sends lengths and ID values in separate AllToAll calls. Weights or variable stride can change the tensor list.</li><li>Second wait. Consume payload Work handles and run <code>KJT.dist_init</code>, recatting the received data into the lookup layout and preparing KJT metadata.</li></ol>
<p><code>Awaitable[Awaitable[KJTList]]</code> reflects these two stages. The outer awaitable determines receive sizes and starts the transfer; the inner one turns the received data into usable input. The ID payload may still be in flight when the first wait returns. {source:splits}; {source:tensors}</p>
{figure:03}
<h3 id="en-input-sync">Waits and host synchronization</h3>
<p>Host waiting is not limited to receiving splits. Before communication starts, <code>KJT.dist_splits()</code> requires host-side <code>length_per_key</code>. If uncached, TorchRec reduces CUDA lengths and obtains a Python list through <code>_safe_tolist</code>. After receiving payload, the fixed-stride branch of <code>dist_init()</code> calls <code>sync()</code> on the new KJT to prepare its length and offset metadata. {source:kjt_splits}; {source:kjt_lengths}; {source:kjt_init}</p>
<p>D1, D2, and D3 in Fig. 3 mark post-bucket send-size preparation, receive-size readback, and KJT metadata reconstruction. The conditional pre-bucket read 01 appears in Fig. 2. For a nonempty CUDA tensor, the safe-list path performs D2H and explicitly synchronizes the current stream. {source:host_copy}; {source:splits}</p>
<p>The single H1 message groups three independent copies: H1-a, H1-b, and H1-c upload lengths splits, values splits, and stride, respectively. On the fixed-stride, unweighted path, each <code>torch.tensor(..., device=cuda)</code> call transfers <code>8P</code> bytes. Packing and the splits AllToAll follow these uploads. {source:split_h2d}</p>
<p>The pinned version also reads back the sent <code>_input_tensor</code> during the first wait to check split-size integer overflow, marked V2 in the diagram. This read runs on the normal path, before any error is detected. D1 / D2 / D3 identify three primary data dependencies, not every synchronization call or an exact count of runtime stalls. {source:split_validation}</p>
<p>The <a href="#en-host-transfers">host/device transfer inventory</a> lists directions, byte counts, and conditions. Row 01 matches the marker in Fig. 2; rows 03–05 list the three copies grouped under H1 in Fig. 3.</p>
<p>These validation readbacks were introduced by <a href="https://github.com/meta-pytorch/torchrec/commit/a950331f5d1778a25a3ff44fe3a255277e1338f2">PR #3978 (<code>a950331f5</code>)</a>, first included in the weekly tag <a href="https://github.com/meta-pytorch/torchrec/releases/tag/v2026.04.13.00"><code>v2026.04.13.00</code></a>. Release 1.6.0 did not contain them; <a href="https://github.com/meta-pytorch/torchrec/releases/tag/v1.7.0-rc1">1.7.0</a> does. They originally used CUDA tensor <code>.tolist()</code>. <a href="https://github.com/meta-pytorch/torchrec/commit/ec5baf373ef8ef3ea82c23e4c3086815e7ffcd3f">PR #4131 (<code>ec5baf373</code>)</a> later replaced those conversions with safe-list helpers, retaining host readback and explicitly synchronizing the current stream. The pinned <code>1d87b8f79b7bb</code> contains both changes.</p>
<p>An asynchronous collective's <code>Work.wait()</code> marks where TorchRec consumes communication results. The call alone does not establish that the CPU waits for the entire device, or explain all internal NCCL stream behavior. Keep this communication dependency separate from metadata operations that require values on the host.</p>
<p>Recat transforms the received rank / feature layout into the layout required by the local lookup. It is a local permutation, not another cross-rank transfer. The row owner now has its requests, but has not yet returned embedding vectors.</p>

<h2 id="en-lookup">4. Lookup and output reconstruction</h2>
<h3 id="en-lookup-local">Local lookup</h3>
<p><code>GroupedEmbeddingsLookup</code> splits the local KJT into compatible embedding groups and calls their embedding kernels. In the fused path, <code>BatchedFusedEmbedding</code> configures TBE with <code>PoolingMode.NONE</code>, passing IDs and offsets to obtain vectors for the distributed ID occurrences. This stage adds no cross-rank collective. The diagram separates backend computation from TorchRec wrappers to distinguish input preparation and table access. Kernel implementations and counts depend on the input and backend. {source:lookup}; {source:tbe}</p>
<p>Before calling the backend, TorchRec obtains KJT offsets and converts values / offsets to the backend's configured index / offset dtypes. These local preparation operations are distinct from the table lookup, even though they occur within the lookup call's scope. {source:tbe_call}</p>
{figure:04}
<h3 id="en-output-a2a">Output AllToAll</h3>
<p><code>SequenceEmbeddingsAllToAll</code> returns vectors from row owners to requesting ranks. <code>All2All_Seq_Req.forward</code> applies <code>forward_recat</code> to prepare the send layout, optionally encodes the payload, and launches asynchronous AllToAll. When the output is consumed, <code>All2All_Seq_Req_Wait.forward</code> consumes the request and optionally decodes the result. {source:output}; {source:seq}</p>
{figure:05}
<h3 id="en-output-reconstruct">Lazy waits and order restoration</h3>
<p>Reconstruction has two layers. First, <code>unbucketize_permute_tensor</code> restores the pre-bucketization order. If IDs were deduplicated, <code>reverse_indices</code> expands unique embeddings back to occurrences. The result is split by feature and paired with the original lengths to form <code>Dict[str, JaggedTensor]</code>. The default expansion uses <code>index_select</code>; an optional <code>gather</code> branch serves the same purpose. {source:jt}</p>
{figure:06}
<p>For example, <code>[2, 6, 2]</code> can be represented by unique IDs <code>[2, 6]</code> and the inverse map <code>[0, 1, 0]</code>. Returning <code>[E2, E6]</code> must still produce <code>[E2, E6, E2]</code> for the caller. The operator determines the actual unique ordering; the example illustrates the mapping.</p>

<h2 id="en-backward">5. Backward and parameter updates</h2>
<p>Output embedding gradients flow through the reconstruction operations, reverse AllToAll, and the local embedding kernel. Figure 7 shows the full path; Figures 8 through 12 expand its stages. Forward wrappers and the autograd nodes that execute backward appear as separate actors.</p>
{figure:07}
<h3 id="en-backward-reconstruct">Backward through reconstruction</h3>
<p>Backward starts from downstream gradients for each output embedding. Gradients from feature splits rejoin the corresponding layout. If forward expanded duplicate occurrences, backward adds their gradients into the same unique position: occurrence gradients <code>[g0, g1, g2]</code> for <code>[2, 6, 2]</code> become <code>[g0 + g2, g1]</code> for the unique IDs. Differentiating unbucketization then restores the bucket layout received by output AllToAll. These are derivatives of tensor operations, not successive calls to wrapper modules' <code>backward()</code> methods. {source:jt}; {source:output}</p>
{figure:08}
<h3 id="en-backward-a2a">Backward AllToAll</h3>
<p><code>All2All_Seq_Req_Wait.backward</code> launches the reverse AllToAll, returning embedding gradients from requesting ranks to row owners. It swaps the forward send / receive splits and optionally applies a backward codec. The dummy-tensor autograd edge then leads to <code>All2All_Seq_Req.backward</code>, which consumes the request, optionally decodes, and applies <code>backward_recat</code> to recover the local lookup layout. When <code>GRADIENT_DIVISION</code> is enabled, it also divides by process-group size. {source:seq}</p>
{figure:09}
<h3 id="en-backward-wait">Request-side communication waits</h3>
<p>After reverse communication launches, the dummy gradient advances autograd to the request-side backward. That node consumes the request, decodes, applies backward recat, optionally scales the gradient, and returns it to the local lookup.</p>
{figure:10}
<h3 id="en-backward-update">Local embedding updates</h3>
<p>In the fused TBE path, the backend performs its configured embedding update during backward after receiving the local lookup gradients. TorchRec's <code>EmbeddingFusedOptimizer.step()</code> sets the backend learning rate in this implementation; it is not a second independent row update. Other model parameters still use their configured optimizers, and other compute kernels need not follow this fused behavior. {source:tbe}; {source:fused}</p>
{figure:11}
<h3 id="en-backward-boundary">Integer-input boundary</h3>
<p>IDs, lengths, and offsets are integers, and EC prepares and distributes input under <code>torch.no_grad()</code>. Consequently, this backward path does not reverse each input splits, lengths, and ID AllToAll. It sends the differentiable embedding output gradients back to their owners. {source:input}</p>
{figure:12}

<h2 id="en-sync">6. Communication and synchronization</h2>
<h3 id="en-host-transfers">Host/device transfers</h3>
<p>Only per-batch TorchRec metadata copies are counted; input KJT upload is excluded. Baseline: one row-wise group, fixed stride, equal per-rank batch sizes, no weights, deduplication, codec, or collective tag. <code>P &gt; 1</code> is the rank count and <code>F</code> the pre-bucket feature count. All byte counts are per rank.</p>
<div class="table-scroll"><table class="transfer-inventory"><thead><tr><th>No.</th><th>Direction</th><th>Stage</th><th>Data (source)</th><th>Bytes / batch</th><th>Required / condition</th></tr></thead><tbody>
<tr><td>01</td><td><span class="seq-key seq-host">D2H</span></td><td>Input permute / split</td><td>{source:kjt_split_prepare|Pre-bucket ID counts per feature}</td><td><code>8F</code></td><td>On demand; skipped for cached metadata or empty lengths.</td></tr>
<tr><td>02 · D1</td><td><span class="seq-key seq-host">D2H</span></td><td>Split preparation</td><td>{source:kjt_splits|ID counts per rank × feature}</td><td><code>8FP</code></td><td>Required on the current nonempty path; bucket counts are recomputed.</td></tr>
<tr><td>03 · H1-a</td><td><span class="seq-key seq-h2d">H2D</span></td><td>Before splits launch</td><td>{source:split_sizes_h2d|Lengths splits}</td><td><code>8P</code></td><td>Required to exchange lengths element counts.</td></tr>
<tr><td>04 · H1-b</td><td><span class="seq-key seq-h2d">H2D</span></td><td>Before splits launch</td><td>{source:split_sizes_h2d|Values splits}</td><td><code>8P</code></td><td>Required to exchange ID counts.</td></tr>
<tr><td>05 · H1-c</td><td><span class="seq-key seq-h2d">H2D</span></td><td>Before splits launch</td><td>{source:split_stride_h2d|Stride}</td><td><code>8P</code></td><td>Fixed-stride path; exchanges batch sizes.</td></tr>
<tr><td>06 · D2</td><td><span class="seq-key seq-host">D2H</span></td><td>First wait</td><td>{source:split_d2h|Received splits + stride}</td><td><code>24P</code></td><td>Required to determine payload receive sizes.</td></tr>
<tr><td>07 · V2</td><td><span class="seq-key seq-host">D2H</span></td><td>First wait</td><td>{source:split_validation|Sent splits + stride for validation}</td><td><code>24P</code></td><td>Extra validation read; not algorithmically required.</td></tr>
<tr><td>08 · H2</td><td><span class="seq-key seq-h2d">H2D</span></td><td>First wait</td><td>{source:input_recat|Input recat indices}</td><td><code>4FP</code></td><td>Currently uploaded each batch; reusable with a fixed layout.</td></tr>
<tr><td>09 · D3</td><td><span class="seq-key seq-host">D2H</span></td><td>Second wait</td><td>{source:kjt_init|Received KJT ID totals per feature}</td><td><code>8F</code></td><td>Required on the current nonempty path to rebuild host metadata.</td></tr>
</tbody></table></div>
<p>D2H uses safe-list readback and synchronizes the <strong>current stream</strong>; H2D uses blocking CUDA tensor construction. Integer lengths reduce to int64, so each count occupies <code>8 B</code>. {source:host_copy|Synchronization implementation}; {source:kjt_lengths|count computation}.</p>
<div class="note-box"><p><strong>V2 executes on the normal path.</strong>Disabling overflow debug does not remove the readback. D2 / V2 copy the entire metadata tensor, not just the last row used by validation.</p></div>
<p>For <code>P=8, F=1</code>, D1 + D2 + V2 + D3 total <strong>456 B D2H</strong> and four explicit synchronizations; H1 + H2 total <strong>224 B H2D</strong>. If 01 is needed, add <code>8 B</code> D2H and one synchronization. Waiting includes upstream stream work, so bytes do not determine latency.</p>
<h3 id="en-transfer-conditions">Conditional transfers</h3>
<p>Count these additional per-batch copies when the configuration or pipeline path applies.</p>
<div class="table-scroll"><table class="transfer-inventory"><thead><tr><th>No.</th><th>Direction</th><th>Stage</th><th>Data (source)</th><th>Bytes</th><th>Required / condition</th></tr></thead><tbody>
<tr><td>10</td><td><span class="seq-key seq-h2d">H2D</span></td><td>First wait</td><td>{source:input_recat|Recat input / output offsets}</td><td>Extra <code>8(FP+1)</code></td><td>Only for unequal per-rank batch sizes.</td></tr>
<tr><td>11</td><td><span class="seq-key seq-h2d">H2D</span><br><span class="seq-key seq-host">D2H</span></td><td>Split validation</td><td>{source:collective_tag|Collective-consistency tag}</td><td>H2D +<code>8P</code><br>D2, V2 each +<code>8P</code></td><td>Only when tag validation is enabled; included in D2/V2 without another D2H sync call.</td></tr>
<tr><td>12 · V1</td><td><span class="seq-key seq-host">D2H</span></td><td><a href="torchrec-sparse-dist-pipeline.html#en-pipeline-distribution">Pipeline, before fusion</a></td><td>{source:fused_validation|Per-split-tensor validation}</td><td><code>8P</code> per tensor<br><code>24P</code> per baseline KJT</td><td>One sync per tensor; extra validation, absent from direct row-wise execution.</td></tr>
</tbody></table></div>
<p>VBE, uneven bucketization, weights, codecs, and internal backend copies require separate accounting. NCCL AllToAll and local D2D are not H2D / D2H.</p>
<h3 id="en-rank-communication">Cross-rank communication</h3>
<div class="table-scroll"><table><thead><tr><th>Stage</th><th>Cross-rank payload</th><th>Consumption point</th><th>Synchronization distinction</th></tr></thead><tbody>
<tr><td>Send metadata preparation</td><td>None</td><td><code>dist_splits → length_per_key</code></td><td>Uncached CUDA lengths are reduced and read back to the host</td></tr>
<tr><td>Input splits</td><td>Split sizes</td><td>Outer awaitable wait</td><td>CUDA sizes become Python lists: explicit host waiting</td></tr>
<tr><td>Input payload</td><td>KJT lengths, ID values, optional fields</td><td>Inner awaitable wait</td><td>Consume communication; recat and sync host metadata</td></tr>
<tr><td>Local lookup</td><td>None</td><td>Local embedding kernel</td><td>Requires the owner-local KJT</td></tr>
<tr><td>Output distribution</td><td>Embedding vectors</td><td>Lazy output consumption</td><td>Then decode, unbucketize, and restore occurrences</td></tr>
<tr><td>Backward distribution</td><td>Embedding vector gradients</td><td>Req.backward</td><td>Then recat and differentiate the local lookup</td></tr>
</tbody></table></div>
<p>For one communication group with the baseline KJT fields, the inventory is input splits, lengths, and values; output embeddings; and reverse embedding gradients. These five AllToAll calls are not a fixed NCCL kernel count. Additional sharding groups, optional fields, and later metadata fusion change how calls are organized. Communication for other model parameters is outside this inventory. {source:splits}; {source:tensors}; {source:seq}</p>
<p>A batch follows this dependency chain: route IDs → local lookup → return and reconstruct embeddings → downstream computation → return gradients → local update. Input distribution also has a CPU dependency: the host must read split sizes before launching the corresponding payload. These dependencies also constrain which work can overlap across batches.</p>

<h2 id="en-sources">Source and diagram index</h2>
<p>The twelve figures give six views of forward and six of backward. Input distribution labels H2D, three host-read sites, and each AllToAll. Output communication and reconstruction, reverse launch and completion, and local updates and gradient boundaries have separate diagrams for reference. Source links refer to the TorchRec revision used here.</p>
{figure_index}
<p>Start with the two waits in {source:forward}, then follow {source:splits}, {source:tensors}, and {source:seq} to locate where communication requests are launched and consumed.</p>
<p class="series-next">Also in the TorchRec series: <a href="torchrec-sparse-dist-pipeline.html">TorchRec sparse dist pipeline</a>.</p>
'''

PIPELINE_EN = r'''<h1>TorchRec sparse dist pipeline</h1>
<p class="lead">TorchRec sparse distribution pipelines overlap preparation and distribution of later inputs with training of the current batch. This article compares <code>TrainPipelineSparseDist</code> and <code>PrefetchTrainPipelineSparseDist</code>, covering two-stage input communication, batch-context handoff, CUDA stream dependencies and embedding-cache requirements. Sequence diagrams and a timeline show startup, steady-state operation and drain.</p>
<div class="note-box"><p>This article examines the two sparse distribution pipelines at TorchRec commit <a href="https://github.com/pytorch/torchrec/tree/1d87b8f79b7bb1671cb8be3e646e99e835cce610"><code>1d87b8f79b7bb</code></a>, using multi-rank eager CUDA/NCCL <code>ShardedEmbeddingCollection</code>. It returns unpooled sequence embeddings. The baseline input is an unweighted KJT with fixed batch stride. Implementation explanations refer to this TorchRec source.</p></div>
<p>Row-wise sharding divides embedding-table rows across ranks. A rank's samples can request rows owned by other ranks, so input distribution routes IDs to their row owners. A <code>KeyedJaggedTensor</code> (KJT) carries feature keys, ID values, and lengths / offsets. Each owner looks up its local rows and returns vectors through output AllToAll; backward sends vector gradients in the reverse direction. Pipeline scheduling advances input preparation and distribution. Local lookup, output communication, and backward still execute as part of the current batch's model work. {source:rw}; {source:input}; {source:seq}</p>
{splits_primer}
<p>Input distribution has two waits. The first consumes split-size metadata, reads receive sizes onto the host, and launches the KJT payload. The second consumes that payload and reconstructs the KJT for local lookup. Payload may still be in flight when the first wait returns. A pipeline can schedule these stages separately to prepare later batches ahead of use. For individual AllToAll calls, see <a href="torchrec-row-wise-sharding.html#en-input">row-wise input distribution</a> in this series. {source:forward}; {source:splits}; {source:tensors}</p>
<p>Host synchronization comes from metadata: split sizes must be prepared before sending, the first wait converts received CUDA sizes to Python lists, and the fixed-stride branch of the second wait prepares the new KJT's length and offset metadata. For nonempty CUDA tensors, <code>_safe_tolist</code> performs D2H and synchronizes the current stream. Cached metadata can avoid recomputation. A <code>Work.wait()</code> call alone does not establish that the CPU waits for the entire device. {source:kjt_splits}; {source:kjt_init}; {source:host_copy}</p>
<p class="reading-note">Read sequences from top to bottom as host submission order and logical dependencies. Activation bars mark calls or access scopes, offset bars mark nested self-calls, and hollow dashed bars mark unconsumed requests. Stream lanes and bar lengths do not measure GPU time. Bands mark <span class="seq-key seq-h2d">H2D in blue</span>, <span class="seq-key seq-host">D2H / host sync in red</span>, and <span class="seq-key seq-comm">AllToAll in purple</span>; amber marks request waits and green marks stream dependencies. D1 / D2 / D3 match the read sites in the row-wise article; V1 / V2 identify additional validation readbacks in the pinned version. Runtime stalls depend on cached metadata and the execution path. Messages and file:line labels link to source. All figures fit the available width by default.</p>
<h2 id="en-pipeline">1. Pipeline scheduling</h2>
<p>While the model processes batch <code>i</code>, IDs for batch <code>i+1</code> can already be obtained from the next input. Their distribution does not depend on the current batch's model output. TorchRec can advance this preparation so that execution reaches the embedding module with an existing request.</p>
<p>The scheduler rewrites eligible sharded-module forwards, creates their contexts, and calls <code>input_dist</code> early. When model execution reaches a rewritten module, a runtime wrapper retrieves the request and state for the current batch and continues with <code>compute_and_output_dist</code>. Local lookup, output AllToAll, and backward dependencies remain. Tracing and rewriting determine eligibility; arbitrary sharded calls inside a model do not automatically qualify. {source:rewrite}; {source:runtime}</p>
<h3 id="en-pipeline-distribution">Input distribution launch and wait</h3>
<ul><li><code>start_sparse_data_dist(batch, ctx)</code> initiates input distribution and organizes compatible splits communication. Metadata can be fused by process group; this does not merge every ID payload into one collective.</li><li><code>wait_sparse_data_dist(ctx)</code> consumes fused splits awaitables and stores tensors requests in <code>input_dist_tensors_requests</code>. It launches payload communication along the way; that payload can still be in flight when the function returns.</li></ul>
<p>The two pipelines place the second wait in different functions. The ordinary version waits and reconstructs input in <code>PipelinedForward</code>. The prefetch version does so in <code>prefetch_embeddings</code>, because cache prefetch needs IDs that have already been distributed. {source:wait}; {source:prefetch_helper}</p>
<p>Pipelining changes where these operations run in the schedule. <code>KJTAllToAllForward</code> still calls <code>dist_splits()</code> for host send sizes, fused splits still require host receive sizes, and the second wait must prepare a usable KJT before lookup or prefetch. {source:pipeline_splits}; {source:kjt_init}</p>
<div class="table-scroll"><table><thead><tr><th>Read site</th><th>Values needed on the host</th><th>Ordinary pipeline</th><th>Prefetch pipeline</th></tr></thead><tbody>
<tr><td>D1 · Send sizes</td><td>Bucketized KJT <code>length_per_key</code>; read back uncached, nonempty CUDA lengths</td><td>Inside <code>start_sparse_data_dist(i+1)</code>, before splits launch</td><td>Inside <code>start_sparse_data_dist(i+2)</code>, at the end of this progress</td></tr>
<tr><td>D2 · Receive sizes</td><td>Splits AllToAll output, needed to size payload receive buffers</td><td>Inside <code>wait_sparse_data_dist(i+1)</code>, after current forward returns</td><td>Inside <code>wait_sparse_data_dist(i+1)</code>, before current forward</td></tr>
<tr><td>D3 · KJT metadata</td><td><code>dist_init().sync()</code> prepares the new KJT's host length / offset metadata</td><td>Inside the second wait in <code>PipelinedForward(i)</code></td><td>Inside the second wait in <code>prefetch_embeddings(i+1)</code></td></tr>
</tbody></table></div>
<p>For one batch, the primary dependencies remain <code>D1 → splits → D2 → payload → D3</code>. Within one <code>progress(i)</code>, the ordinary schedule is <code>D1(i+1) → D3(i) → D2(i+1)</code>; the prefetch schedule is <code>D2(i+1) → D3(i+1) → D1(i+2)</code>. Interleaving batches changes the order in which these labels appear.</p>
<aside class="note-box" id="en-fused-splits-sync" role="note" aria-labelledby="en-fused-splits-sync-title">
<p id="en-fused-splits-sync-title"><strong>Additional host synchronization in fused splits (V1)</strong></p>
<p>On the pinned eager CUDA path, fused-splits construction adds a host readback: before launching splits AllToAll, <code>FusedKJTListSplitsAwaitable</code> calls <code>_safe_tolist</code> on each CUDA split tensor. Each conversion performs D2H and calls <code>current_stream().synchronize()</code>, blocking the CPU until preceding work on that stream and the copy complete. {source:fused_validation}; {source:host_copy}</p>
<p>This is additional overhead from the validation implementation in this version. <strong>Disabling <code>TORCHREC_OVERFLOW_DEBUG</code> still leaves these readbacks and synchronization calls in place</strong>: the checker evaluates the flag after the readback. The loop runs per split tensor, so one V1 marker can represent multiple synchronization calls.</p>
</aside>
<p>V2 runs inside the first splits wait and calls <code>_safe_tolist_2d</code> on the sent <code>_input_tensor</code>. This validation readback also precedes the checker's debug-flag guard and performs D2H with host waiting. {source:split_validation}</p>
<p>These validation readbacks were introduced by <a href="https://github.com/meta-pytorch/torchrec/commit/a950331f5d1778a25a3ff44fe3a255277e1338f2">PR #3978 (<code>a950331f5</code>)</a>, first included in the weekly tag <a href="https://github.com/meta-pytorch/torchrec/releases/tag/v2026.04.13.00"><code>v2026.04.13.00</code></a>. Release 1.6.0 did not contain them; <a href="https://github.com/meta-pytorch/torchrec/releases/tag/v1.7.0-rc1">1.7.0</a> does. They originally used CUDA tensor <code>.tolist()</code>. <a href="https://github.com/meta-pytorch/torchrec/commit/ec5baf373ef8ef3ea82c23e4c3086815e7ffcd3f">PR #4131 (<code>ec5baf373</code>)</a> later replaced those conversions with safe-list helpers, retaining host readback and explicitly synchronizing the current stream. The pinned <code>1d87b8f79b7bb</code> contains both changes.</p>
<p>V1 belongs to the pipeline fused-splits constructor; a direct row-wise module call does not take that fusion path. V2 belongs to the shared <code>SplitsAllToAllAwaitable._wait_impl</code>, so both articles mark it. Both articles use the same source revision.</p>
{figure:13}
<h3 id="en-pipeline-streams">Stream dependencies and lifetimes</h3>
<p>TorchRec handles execution order and storage lifetime separately when handing off distributed input and module context. <code>wait_stream</code> makes consumer GPU work wait for the producer. <code>record_stream</code> records tensor use on another stream so the allocator does not reuse its storage too early. Execution dependencies determine when communication results are ready; recording the stream does not perform that wait. {source:stream}; {source:runtime}</p>

<h2 id="en-sparse">2. Standard sparse dist pipeline</h2>
<p>The ordinary pipeline schedules H2D, input distribution, and training, with room for up to three batches in flight. In steady state, <code>i</code> runs forward / backward, <code>i+1</code> advances input distribution, and <code>i+2</code> enters the queue and is copied to the GPU. The sequence uses the default <code>enqueue_batch_after_forward=False</code>. {source:ordinary}</p>
<pre class="code" data-language="python"># Steady-state pseudocode: boundary checks and configuration branches omitted.
zero_grad()
wait_for_current_batch(i)
start_sparse_data_dist(i + 1)   # launch splits
enqueue_batch(i + 2)           # H2D
losses, output = model(i)      # wrapper performs the second wait for i
wait_sparse_data_dist(i + 1)   # first-stage wait; launch payload
backward(losses)
optimizer_step()
dequeue_batch(i)</pre>
{figure:14}
<p>When forward for batch <code>i</code> reaches an embedding module, <code>PipelinedForward</code> pops its tensors request and calls <code>request.wait()</code> in the data_dist stream context, reconstructing the KJT. The training stream then joins that stream's work, receives the input and context, and continues with lookup and output distribution. {source:runtime}</p>
<p>For <code>i+1</code>, splits launch before the current forward, whereas payload launches after forward returns and before backward is submitted. This creates opportunities for splits to overlap current forward work, and payload to overlap current backward work. Setting <code>enqueue_batch_after_forward=True</code> moves H2D enqueue after forward; it does not add an independent prefetch stage. {source:ordinary}</p>
<p>The ordinary version has no separately scheduled cache prefetch. The backend configuration controls caching within lookup. Host metadata waits, collective ordering, GPU resource contention, and kernel duration determine how much work can overlap. Multiple streams allow overlap but do not guarantee that computation hides all communication time.</p>

<h3 id="en-multi-iteration">Scheduling across iterations</h3>
<p>Across three consecutive progress calls, one batch is copied, distributed, then used for computation. Figure 3 follows <code>N+2</code> by default: it is copied during <code>progress(N)</code>, distributed during <code>progress(N+1)</code>, and consumed during <code>progress(N+2)</code>. Select a phase or click an operation to inspect its dependencies and TorchRec source. {source:ordinary}; {source:runtime}</p>
<p>In Fig. 3, A1-A4 follow submission order within one progress call: <code>splits(N+1) → output dist(N) → lengths(N+1) → ID values(N+1)</code>. The labels cover work from both the current and next batch and follow submission order within this progress call. Backward still includes embedding-gradient AllToAll, which is outside these four input / forward labels. The diagram marks Python forward return separately from GPU forward completion. Red markers cover D1 / D2 / D3 and V1 / V2 host reads with batch identities. {source:ordinary}; {source:host_copy}; {source:seq}</p>
{figure:15}

<h2 id="en-prefetch">3. Prefetch pipeline</h2>
<p>The prefetch version schedules embedding prefetch after input distribution. Backends that need caching use the distributed owner-local IDs to prepare the cache before lookup. The lookup itself still runs in the current batch's forward. <code>ShardedEmbeddingModule.prefetch</code> passes each group's input to the corresponding lookup's <code>prefetch</code> method. {source:prefetch_module}; {source:cache}</p>
<h3 id="en-prefetch-waits">Payload and prefetch scheduling</h3>
<p>In the pinned implementation, <code>wait_sparse_data_dist(i+1)</code> runs <strong>before</strong> the current forward, allowing the next ID payload to overlap forward computation. After forward returns, <code>_prefetch(i+1)</code> consumes the payload, reconstructs the KJT, and schedules prefetch. The scheduler then submits current backward / optimizer work and starts splits for <code>i+2</code>. {source:prefetch}</p>
<pre class="code" data-language="python"># Steady-state pseudocode: splits for i+1 have already been started.
zero_grad()
wait_for_prefetch(i)
enqueue_batch(i + 2)
wait_sparse_data_dist(i + 1)   # launch next payload before current forward
losses, output = model(i)      # consume post-prefetch input/context for i
clear_consumed_prefetch_state(i)
prefetch(i + 1)                # second wait + backend prefetch
backward(losses)
optimizer_step()
start_sparse_data_dist(i + 2)  # prepare the following progress call
dequeue_batch(i)</pre>
{figure:16}
<p><code>prefetch_embeddings</code> performs the second <code>request.wait()</code> on the data_dist stream. The prefetch stream joins it, calls the module's <code>prefetch</code>, and saves <code>module_input_post_prefetch</code> and <code>module_contexts_post_prefetch</code>. On the next forward, <code>PrefetchPipelinedForward</code> consumes those objects, makes the training stream wait for the prefetch stream, and invokes <code>compute_and_output_dist</code>. It no longer consumes an input payload request there. {source:prefetch_helper}; {source:preforward}</p>
<h3 id="en-prefetch-backend">Prefetch backend constraints</h3>
<p><code>GroupedEmbeddingsLookup</code> enters its prefetch path only for compute kernels requiring it, such as <code>FUSED_UVM_CACHING</code>; otherwise it can return immediately. For the TBE backends checked in the code, <code>prefetch_pipeline</code> must also be configured correctly. TorchRec logs an error otherwise, warning that backward cache locations may be wrong. Adding a CUDA stream alone does not establish the complete cache correctness protocol. {source:need_prefetch}; {source:cache}</p>
<p>The host calls <code>_prefetch(i+1)</code> before submitting <code>backward(i)</code>. The <code>progress()</code> implementation does not insert a universal host barrier requiring next-batch prefetch to finish before current backward. Actual overlap and protection of cache locations depend on backend stream and cache constraints. These source-level submission sequences are not measured GPU timelines. {source:prefetch}</p>
<p class="reading-note">The four GPU work lanes represent H2D, input distribution, prefetch, and training roles, not an exhaustive list of CUDA/NCCL streams. This version also creates a new Stream object named <code>_default_stream</code> and passes it as <code>forward_stream</code> to the prefetch helper. Its variable name does not make it CUDA's default stream. {source:prefstreams}; {source:prefetch_helper}</p>

<h2 id="en-compare">4. Pipeline comparison</h2>
<div class="table-scroll"><table><thead><tr><th>Operation</th><th>TrainPipelineSparseDist</th><th>PrefetchTrainPipelineSparseDist</th></tr></thead><tbody>
<tr><td>Launch splits for <code>i+1</code></td><td>Before forward in this progress call</td><td>At the end of the preceding call, or during initial fill</td></tr>
<tr><td>Launch payload for <code>i+1</code></td><td>After <code>forward(i)</code> returns</td><td>Before <code>forward(i)</code></td></tr>
<tr><td>Second input wait</td><td>This batch's <code>PipelinedForward</code></td><td>This batch's <code>prefetch_embeddings</code></td></tr>
<tr><td>State at embedding forward</td><td>Tensors request + module context</td><td>Reconstructed input + post-prefetch context</td></tr>
<tr><td>Training stream joins</td><td>data_dist stream</td><td>prefetch stream</td></tr>
<tr><td>Independent backend prefetch</td><td>Absent</td><td>Present; the backend may require no actual cache work</td></tr>
<tr><td>Current-batch computation</td><td colspan="2">Local lookup → output AllToAll → downstream computation → backward / reverse AllToAll → optimizer</td></tr>
</tbody></table></div>
<p>In this source revision, the prefetch version changes the payload launch point, second-wait location, and saved context as well as adding a prefetch stage. All of these differences affect the schedule. {source:ordinary}; {source:prefetch}</p>
<h3 id="en-pipeline-fill-drain">Fill, steady state, and drain</h3>
<p>At startup, the ordinary version begins input distribution for the first batch, performs its first wait to obtain a tensors request, and enqueues the second batch. The prefetch version also completes the first batch's second wait and prefetch before starting splits for the second batch. The first batch has no preceding computation to cover this preparation, so startup needs to be considered separately. {source:fill}; {source:prefill}</p>
<p>In steady state, batches and contexts move together. Runtime pops a module's request from the corresponding dictionary when consuming it, and dequeue must remove the matching context. Rewritten embedding modules are assumed to run once per model forward; repeated consumption raises an error. The queue holds up to three batches. Fewer may be in flight, and memory usage cannot be inferred by multiplying the size of one batch by three. {source:fill}; {source:runtime}</p>
<p>With the default <code>execute_all_batches=True</code>, already queued batches continue after the dataloader is exhausted. Preparation is skipped when <code>i+1</code> or <code>i+2</code> does not exist. Evaluation omits the training branch's backward and optimizer calls. These startup and drain sequences therefore differ from the full three-batch steady-state diagrams. {source:fill}; {source:ordinary}; {source:prefetch}</p>

<h2 id="en-sources">Source and diagram index</h2>
<p>Figure 1 compares context handoff in both pipelines. Figures 2 and 4 show the ordinary and prefetch steady-state call sequences. Figure 3 follows one batch across three progress calls. The sequences and interactive timeline describe scheduling and dependencies in the source revision used here.</p>
{figure_index}
<p>Compare {source:ordinary} with {source:prefetch} to locate their payload launches, then inspect {source:runtime} and {source:prefetch_helper} for the second wait and context handoff.</p>
<p class="series-next">Also in the TorchRec series: <a href="torchrec-row-wise-sharding.html">TorchRec row-wise sharding</a>.</p>
'''
NATIVE_NAV_ZH = [('layout', '1. 行分片与 KJT'), ('native', '2. Forward 数据流'), ('input', '3. Input Distribution'), ('lookup', '4. Lookup 与输出恢复'), ('backward', '5. Backward 与参数更新'), ('sync', '6. 通信与同步汇总'), ('sources', '源码与图表索引')]
PIPELINE_NAV_ZH = [('pipeline', '1. Pipeline 调度机制'), ('sparse', '2. 普通 Sparse Dist Pipeline'), ('prefetch', '3. Prefetch Pipeline'), ('compare', '4. Pipeline 对比'), ('sources', '源码与图表索引')]
NATIVE_NAV_EN = [('layout', '1. Row sharding and KJT'), ('native', '2. Forward data flow'), ('input', '3. Input distribution'), ('lookup', '4. Lookup and output reconstruction'), ('backward', '5. Backward and parameter updates'), ('sync', '6. Communication and synchronization'), ('sources', 'Source and diagram index')]
PIPELINE_NAV_EN = [('pipeline', '1. Pipeline scheduling'), ('sparse', '2. Standard sparse dist pipeline'), ('prefetch', '3. Prefetch pipeline'), ('compare', '4. Pipeline comparison'), ('sources', 'Source and diagram index')]

def source(key, lang, label=None):
    path, lines, zh, en = SOURCES[key]
    text = label if label is not None else (zh if lang == "zh" else en)
    return f'<a href="{BASE}{path}#{lines}">{escape(text)}</a>'

def figure(key, lang):
    slug, zh, en, sources = FIGS[key]
    title = zh if lang == 'zh' else en
    number = int(key) if int(key) <= 12 else int(key) - 12
    display_key = f'{number:02}'
    path = f'../assets/{ASSET_DIR}/{slug}.svg'
    if key == '15':
        timeline = f'../assets/{ASSET_DIR}/{slug}.html?lang={lang}'
        return f'''<figure class="sequence timeline-figure" id="{lang}-fig-{display_key}">
<div class="diagram-toolbar"><span>{'图 03 · 可交互时间线' if lang == 'zh' else 'Fig. 03 · Interactive timeline'}</span><a href="{timeline}" target="_blank" rel="noopener">{'单独打开交互图' if lang == 'zh' else 'Open interactive timeline'} ↗</a></div>
<iframe class="pipeline-timeline" src="{timeline}" title="{escape(title)}" height="1350"></iframe>
<figcaption><strong>{'图' if lang == 'zh' else 'Fig.'} {number} · {title}</strong><span class="figure-sources">{'源码：' if lang == 'zh' else 'Source: '}{' · '.join(source(k, lang) for k in sources)}</span></figcaption></figure>'''
    svg = ET.parse(ROOT / 'assets' / ASSET_DIR / (slug + '.svg')).getroot()
    height = svg.attrib['height']
    width = svg.attrib['width']
    return f'''<figure class="sequence" id="{lang}-fig-{display_key}">
<div class="diagram-toolbar"><span>{'图' if lang == 'zh' else 'Fig.'} {number:02} · {'调用序列' if lang == 'zh' else 'Call sequence'}</span><div class="diagram-zoom" role="group" aria-label="{'图表缩放' if lang == 'zh' else 'Diagram zoom'}"><button type="button" data-zoom="fit" aria-pressed="true">{'适应宽度' if lang == 'zh' else 'Fit'}</button><button type="button" data-zoom="1" aria-pressed="false">100%</button><button type="button" data-zoom="1.5" aria-pressed="false">150%</button></div><a href="{path}" target="_blank" rel="noopener">{'单独打开' if lang == 'zh' else 'Open SVG'} ↗</a></div>
<div class="diagram-viewport" tabindex="0" role="region" aria-label="{escape(title)}"><object class="sequence-svg" data="{path}" type="image/svg+xml" width="{width}" height="{height}" style="aspect-ratio: {width} / {height}" aria-label="{escape(title)}"><a href="{path}" target="_blank" rel="noopener">{escape(title)}: {'打开交互式序列图' if lang == 'zh' else 'Open interactive sequence diagram'}</a></object></div>
<figcaption><strong>{'图' if lang == 'zh' else 'Fig.'} {number} · {title}</strong><span class="figure-sources">{'源码：' if lang == 'zh' else 'Source: '}{' · '.join(source(k, lang) for k in sources)}</span></figcaption></figure>'''

def expand(body, lang, keys):
    primer = globals()['SPLITS_PRIMER_' + lang.upper()]
    fused = FUSED_SPLITS_PRIMER[lang] if keys[0] == '13' else ''
    body = body.replace('{splits_primer}', primer.replace('{fused_splits_primer}', fused))
    body = re.sub(r'\{source:(\w+)(?:\|([^{}]+))?\}', lambda m: source(m[1], lang, m[2]), body)
    body = re.sub(r'\{figure:(\d+)\}', lambda m: figure(m[1], lang), body)
    entries = ''.join(f'<li><a href="#{lang}-fig-{i:02}">{i:02} · {FIGS[k][1] if lang == "zh" else FIGS[k][2]}</a></li>' for i, k in enumerate(keys, 1))
    return body.replace('{figure_index}', f'<ol class="figure-index">{entries}</ol>')

def nav(items, lang, body):
    """Build two TOC levels from the article's h2/h3 order and stable IDs."""
    labels = {f'{lang}-{key}': label for key, label in items}
    sections = []
    for level, anchor, title in re.findall(r'<h([23]) id="([^"]+)">(.*?)</h\1>', body):
        label = labels.get(anchor, unescape(re.sub(r'<[^>]+>', '', title)))
        entry = f'<a href="#{escape(anchor, quote=True)}">{escape(label)}</a>'
        if level == '2':
            sections.append((entry, []))
        else:
            sections[-1][1].append(f'<li>{entry}</li>')
    entries = []
    for entry, children in sections:
        subtree = '<ul class="toc-subsections">' + ''.join(children) + '</ul>' if children else ''
        entries.append(f'<li>{entry}{subtree}</li>')
    return f'<div class="lang-{lang}"><ul class="toc-sections">' + ''.join(entries) + '</ul></div>'


def series_nav(current):
    items = []
    for post in sorted(POSTS, key=lambda item: item['series_order']):
        is_current = post['slug'] == current['slug']
        label = (f'<span class="lang-zh">{escape(post["title"])}</span>'
                 f'<span class="lang-en">{escape(post["title_en"])}</span>')
        if is_current:
            entry = f'<span class="post-series-current" aria-current="page">{label}</span>'
        else:
            entry = f'<a href="{post["slug"]}.html">{label}</a>'
        items.append(f'<li class="{"current" if is_current else ""}"><span class="post-series-order">{post["series_order"]:02}</span>{entry}</li>')
    return ('<section class="post-series-nav" data-static-series="torchrec" aria-label="TorchRec">'
            '<div class="post-series-title">TorchRec</div><ol class="post-series-list">'
            + ''.join(items) + '</ol></section>')


HEAD = '''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
__POST_META__
<script src="../lang-toggle.js?v=post-toc-3" defer></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&amp;family=Geist+Mono:wght@400;500&amp;display=swap">
<link rel="stylesheet" href="../assets/site.css?v=post-toc-3">
<style>
html[lang="en"] .lang-zh { display: none !important; }
html[lang="zh-CN"] .lang-en { display: none !important; }
main.content { max-width: 1120px; min-width: 0; padding: 56px 32px 96px; letter-spacing: 0; }
.post-page main.content { width: 100% !important; max-width: 824px !important; margin: 0 auto !important; overflow-wrap: anywhere; }
@media (min-width: 1100px) {
  .post-page main.content { width: calc(100% - 280px) !important; max-width: 1120px !important; margin: 0 max(0px, calc((100vw - 1400px) / 2)) 0 auto !important; }
  .post-page aside.toc { left: max(20px, calc((100vw - 1400px) / 2 + 20px)) !important; }
}
main.content h1, main.content h2, main.content h3 { letter-spacing: 0; }
.lead { font-size: 17px; line-height: 1.85; color: var(--fg-muted); }
.note-box { margin: 24px 0; padding: 12px 18px; border-left: 3px solid var(--accent); background: var(--accent-tint); }
.note-box p { margin: 6px 0; }
.reading-note { font-size: 13px; color: var(--fg-muted); }
.table-scroll { overflow-x: auto; margin: 22px 0 28px; }
.table-scroll table { width: 100%; min-width: 680px; border-collapse: collapse; font-size: 13.5px; }
.table-scroll th, .table-scroll td { padding: 11px 13px; border: 1px solid var(--border); text-align: left; vertical-align: top; }
.table-scroll th { background: var(--bg-elevated); }
.table-scroll table.transfer-inventory { min-width: 880px; }
.transfer-inventory th:first-child, .transfer-inventory td:first-child { min-width: 65px; white-space: nowrap; }
.transfer-inventory .seq-key { white-space: nowrap; }
.sequence { --diagram-paper: #fdfdfe; --diagram-control: #f1f3f6; --diagram-ink: #283344; --diagram-muted: #526071; --diagram-line: #dce1e7; margin: 32px 0 40px; border: 1px solid var(--diagram-line); border-radius: 8px; overflow: hidden; background: var(--diagram-paper); font-family: var(--font-sans); }
html[data-theme="dark"] .sequence { --diagram-paper: #171b22; --diagram-control: #252e3b; --diagram-ink: #e7ebf1; --diagram-muted: #aeb9c9; --diagram-line: #343d4b; }
.diagram-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; padding: 12px 18px; background: var(--diagram-paper); border-bottom: 1px solid var(--diagram-line); font-size: 12px; line-height: 1.4; }
.diagram-toolbar > span { margin-right: auto; color: var(--diagram-muted); font-weight: 500; }
.diagram-zoom { display: flex; align-items: center; gap: 2px; padding: 3px; border-radius: 6px; background: var(--diagram-control); }
.diagram-toolbar button { min-height: 32px; padding: 5px 11px; font: inherit; font-variant-numeric: tabular-nums; white-space: nowrap; color: var(--diagram-muted); border: 0; border-radius: 4px; background: transparent; cursor: pointer; }
.diagram-toolbar button:hover { color: var(--diagram-ink); background: var(--diagram-paper); }
.diagram-toolbar button[aria-pressed="true"] { color: var(--diagram-paper); background: var(--diagram-ink); }
.diagram-toolbar button:active { transform: translateY(1px); }
.post-page main.content .diagram-toolbar a { color: var(--diagram-muted); font: inherit; white-space: nowrap; text-decoration: none; }
.post-page main.content .diagram-toolbar a:hover { color: var(--diagram-ink); text-decoration: underline; text-underline-offset: 3px; }
.diagram-toolbar button:focus-visible, .diagram-toolbar a:focus-visible, .diagram-viewport:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.pipeline-timeline { display: block; width: 100%; border: 0; background: #fff; }
.diagram-viewport { overflow: auto; max-height: 84vh; background: var(--diagram-paper); scrollbar-color: var(--diagram-line) var(--diagram-paper); }
.diagram-viewport .sequence-svg { display: block; width: 100%; min-width: 0; max-width: none; height: auto; }
.post-page main.content .sequence figcaption { margin: 0; padding: 16px 20px 18px; border-top: 1px solid var(--diagram-line); font-family: var(--font-sans); font-size: 13px; line-height: 1.75; text-align: left; color: var(--diagram-muted); background: var(--diagram-paper); }
.sequence figcaption strong { color: var(--diagram-ink); font-weight: 500; }
.post-page main.content .sequence .figure-sources a { color: var(--diagram-muted); text-decoration: underline; text-decoration-color: var(--diagram-line); text-underline-offset: 3px; }
.post-page main.content .sequence .figure-sources a:hover { color: var(--diagram-ink); }
@media (max-width: 640px) { .diagram-toolbar { gap: 10px; padding: 10px 12px; } .diagram-toolbar > span { width: 100%; } .diagram-toolbar > a { margin-left: auto; } .diagram-toolbar button { min-height: 36px; } .post-page main.content .sequence figcaption { padding: 14px; } }
.seq-key { display: inline-block; padding: 1px 6px; border-radius: 3px; border: 1px solid; }
.seq-h2d { color: #1d4ed8; background: #eff6ff; border-color: #93c5fd; }
.seq-host { color: #b91c1c; background: #fef2f2; border-color: #fca5a5; }
.seq-comm { color: #6d28d9; background: #f5f3ff; border-color: #c4b5fd; }
.figure-sources { display: block; margin-top: 5px; color: var(--fg-muted); font-size: 12px; }
.series-next { margin-top: 28px; padding-top: 18px; border-top: 1px solid var(--border); }
.post-page .post-series-list a, .post-page .post-series-current { white-space: normal; overflow-wrap: anywhere; line-height: 1.55; }
.figure-index { list-style: none; padding-left: 0; }
.figure-index li { padding: 6px 0; border-bottom: 1px solid var(--border); }
@media (max-width: 960px) { main.content { width: 100%; max-width: 100%; padding: 44px 20px 80px; } }
@media (max-width: 640px) { .post-page main.content { max-width: 100% !important; padding: 32px 18px 72px !important; } }
</style>
</head>
<body>
<div class="layout"><aside class="toc"><div class="toc-title">目录 · TOC</div>
'''

FOOT = '''</main></div>
<script>
// Keep diagrams and the standalone timeline aligned with the article theme.
const pipelineFrames = Array.from(document.querySelectorAll('iframe.pipeline-timeline'));
const sequenceObjects = Array.from(document.querySelectorAll('object.sequence-svg'));
function syncTimelineTheme() {
  const theme = document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
  sequenceObjects.forEach(object => {
    object.contentDocument?.documentElement.setAttribute('data-theme', theme);
  });
  pipelineFrames.forEach(frame => {
    frame.contentWindow?.postMessage({type: 'torchrec-pipeline-theme', theme}, location.origin);
    frame.contentWindow?.postMessage({type: 'torchrec-pipeline-resize'}, location.origin);
  });
}
pipelineFrames.forEach(frame => frame.addEventListener('load', syncTimelineTheme));
sequenceObjects.forEach(object => object.addEventListener('load', syncTimelineTheme));
new MutationObserver(syncTimelineTheme).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme', 'lang']});
syncTimelineTheme();
window.addEventListener('message', function (event) {
  if (event.origin !== location.origin || event.data?.type !== 'torchrec-pipeline-timeline-height') return;
  const frame = pipelineFrames.find(item => item.contentWindow === event.source);
  const height = Number(event.data.height);
  if (frame && Number.isFinite(height) && height >= 400 && height <= 4000) frame.style.height = Math.ceil(height) + 'px';
});

document.querySelectorAll('[data-zoom]').forEach(function (button) {
  button.addEventListener('click', function () {
    var figure = button.closest('.sequence');
    var image = figure.querySelector('.sequence-svg');
    var fit = button.dataset.zoom === 'fit';
    image.style.minWidth = '0';
    image.style.width = fit ? '100%' : (Number(image.getAttribute('width')) * Number(button.dataset.zoom)) + 'px';
    figure.querySelectorAll('[data-zoom]').forEach(function (item) {
      item.setAttribute('aria-pressed', String(item === button));
    });
  });
});
</script>
</body></html>
'''

POSTS = [{'slug': 'torchrec-row-wise-sharding', 'title': 'TorchRec Row-wise Sharding', 'title_en': 'TorchRec row-wise sharding', 'tags': 'TorchRec, Row-wise Sharding, Embedding, NCCL', 'reading': '18 分钟', 'reading_en': '15 min', 'summary': 'TorchRec 行分片的输入分发、查表、输出恢复与梯度回传；12 张源码关联序列图标明 H2D、主机同步和 AllToAll。', 'summary_en': 'TorchRec row-wise input distribution, lookup, output reconstruction and gradient return, with twelve source-linked diagrams marking H2D, host synchronization and AllToAll.', 'series_order': 1, 'prefix': 'NATIVE', 'keys': ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']}, {'slug': 'torchrec-sparse-dist-pipeline', 'title': 'TorchRec Sparse Dist Pipeline', 'title_en': 'TorchRec sparse dist pipeline', 'tags': 'TorchRec, Pipeline, Embedding, Prefetch, NCCL', 'reading': '12 分钟', 'reading_en': '10 min', 'summary': '普通与 prefetch sparse dist pipeline 的两阶段通信、context 交接、stream 依赖和缓存条件，配合序列图与交互时间线。', 'summary_en': 'Ordinary and prefetch sparse distribution pipelines: two-stage communication, context handoff, stream dependencies and cache requirements, with diagrams and an interactive timeline.', 'series_order': 2, 'prefix': 'PIPELINE', 'keys': ['13', '14', '15', '16']}]

def build_post(post):
    metadata = {key: post[key] for key in ('title', 'title_en', 'slug', 'tags', 'reading', 'reading_en', 'summary', 'summary_en', 'series_order')}
    metadata.update(date='2026-10-11', tags_en=post['tags'], series='torchrec', series_title='TorchRec', series_title_en='TorchRec')
    meta_html = '\n'.join(f'<meta name="post:{key}" content="{escape(str(value), quote=True)}">' for key, value in metadata.items())
    html = HEAD.replace('__TITLE__', escape(post['title'])).replace('__POST_META__', meta_html)
    prefix = post['prefix']
    bodies = {lang: expand(globals()[prefix+'_'+lang.upper()], lang, post['keys']) for lang in ('zh', 'en')}
    html += nav(globals()[prefix+'_NAV_ZH'], 'zh', bodies['zh']) + nav(globals()[prefix+'_NAV_EN'], 'en', bodies['en'])
    html += series_nav(post)
    html += '</aside><main class="content">\n'
    for lang in ('zh', 'en'):
        html += f'<div class="lang-{lang}">' + bodies[lang] + '</div>\n'
    html += FOOT
    destination = ROOT / 'posts' / (post['slug'] + '.html')
    destination.write_text(html, encoding='utf-8')
    print(f'Wrote {destination.name}: {len(post["keys"])} figures per language')


def build_redirect():
    # Keep links shared during review useful after splitting and renumbering.
    routes = {}
    for lang in ('zh', 'en'):
        for post in POSTS:
            body = globals()[post['prefix']+'_'+lang.upper()]
            for anchor in re.findall(r'id="([^"]+)"', body):
                routes[anchor] = post['slug'] + '.html#' + anchor
            for index, key in enumerate(post['keys'], 1):
                routes[f'{lang}-fig-{key}'] = post['slug'] + f'.html#{lang}-fig-{index:02}'
        routes[lang+'-sources'] = POSTS[0]['slug'] + '.html#'+lang+'-sources'
    import json
    html = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TorchRec 系列</title></head><body>'
    html += '<h1>TorchRec</h1><p>原文章已分为两篇。The article is now a two-part series.</p><ol>'
    html += ''.join(f'<li><a href="{p["slug"]}.html">{escape(p["title"])}</a></li>' for p in POSTS) + '</ol>'
    html += '<script>const routes = '+json.dumps(routes, ensure_ascii=False)+'; location.replace(routes[location.hash.slice(1)] || "'+POSTS[0]['slug']+'.html");</script></body></html>\n'
    (ROOT / 'posts' / (ASSET_DIR + '.html')).write_text(html, encoding='utf-8')


if __name__ == '__main__':
    for post in POSTS:
        build_post(post)
    build_redirect()
