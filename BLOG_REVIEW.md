# 博客审稿报告

审稿日期: 2026-06-03

修稿状态: 2026-06-04 已按本报告先处理高优先级问题: 修正 PyTorch `custom_op` / `register_fake` 语义、Python namespace package 边界、双语页面重复 `id`、若干版本/来源说明和过度绝对的措辞。本文仍保留为“修改前审稿记录 + 修稿依据”,不是最终发布说明。

范围: `posts/*.html` 下 10 篇博客。审稿重点是可读性、结构完整性、AI 味、事实风险。本报告生成时没有直接改正文;后续修稿见上面的修稿状态。

## 总体结论

这些文章不是空泛的 AI 文。相反，大多数文章的技术密度很高，像是作者把源码、论文和工程经验揉成了一份长笔记。真正的问题有三类:

1. 有几处事实边界写错或写得太确定，尤其是 PyTorch `custom_op` 与 Python namespace package。
2. 很多文章没有版本锚点。源码链接大量指向 `main` 分支和行号，长期看会漂移。
3. 结构上偏“巨型教程脚本”。中英双语同页、长篇目录、重复 h1/h2、术语表缺失，会让读者进入成本偏高。

建议先修 P0/P1，再做文风和结构优化。

## P0/P1 必修问题

### P0: `torch.library.custom_op + register_fake` 不能被写成 Inductor 自动看穿语义

涉及:

- `posts/aoti-cuda-deployment.html`
- `posts/pytorch-dispatcher.html`

现有说法多次表达了这样的意思: `torch.library.custom_op` 注册了 functional + fake impl 后，Inductor 就能把它当 pointwise 看穿，并把 custom op 与后续 `relu` 融合进 Triton。

这和 PyTorch 2.12 官方文档口径冲突。文档说明 `custom_op` 的用途之一就是阻止 `torch.compile/export/FX` peek inside；`triton_op` 才是让 Triton kernel 实现对 compiler 可见的 wrapper。`register_fake` 主要提供 FakeTensor/shape/dtype/device 语义，不等价于 decomposition 或 Inductor lowering。

建议改法:

- 把“fake impl 让 Inductor 识别 pointwise 并融合”改成“fake impl 让 export/compile 能做形状推断，但 op 语义仍然是 opaque”。
- 若要融合，明确需要 decomposition/lowering、`torch.library.triton_op`、或其他 compiler-visible 实现。
- AOTI 例子如果真的跑出融合 kernel，需要补上完整可复现实验、PyTorch commit、日志和生成代码；否则按 opaque custom op 处理。

参考:

- PyTorch `torch.library.custom_op` / `triton_op` 文档: https://docs.pytorch.org/docs/2.12/library.html

### P0: Python import 文章对 namespace package 的边界有一处错误

涉及:

- `posts/python-imports.html`

现有说法: 在 `app/pkg/a.py` 从 `..sib.e` 相对导入时，如果 `app/` 下没有 `__init__.py` 就非法。

这在 Python 3 / PEP 420 下不成立。`app/` 可以是 namespace package；只要用 `python -m app.pkg.a`，`__package__ == "app.pkg"`，相对导入可以成功。我用临时项目验证了 `app/`、`app/pkg/`、`app/sib/` 都没有 `__init__.py` 时仍可从 `..sib.e` 导入。

建议改法:

- 改成: “`..` 不能越过当前顶级 package；顶级 package 可以是 regular package，也可以是 namespace package。”
- 例子里不要把“没有 `app/__init__.py`”等同于非法。

参考:

- Python import system: https://docs.python.org/3/reference/import.html
- PEP 420: https://peps.python.org/pep-0420/

### P1: 中英双语页面存在大量重复 HTML `id`

影响:

- 锚点跳转不稳定。
- TOC / hash 链接可能跳到中文或英文中的任意一个。
- 评论、外链、SEO 和可访问性都会受影响。

检测结果:

- `context-parallel.html`: 31 个重复 id。
- `gemm-ai.html`: `tldr` 重复。
- `onetrans-yambda-study.html`: 26 个重复 id。
- `python-imports.html`: 27 个重复 id。
- `pytorch-dispatcher.html`: 46 个重复 id。
- `pytorch-torch-dispatch-mode.html`: 29 个重复 id。

建议改法:

- 中文 id 统一加 `zh-` 前缀，英文 id 统一加 `en-` 前缀。
- TOC 也同步指向语言前缀。
- `gemm-ai.html` 的两个 `tldr` 至少改成 `zh-tldr` / `en-tldr`。

### P1: 源码引用必须 pin 到版本或 commit

涉及大多数 PyTorch、CUDA、OneTrans 文章。

现在很多链接形如:

- `https://github.com/pytorch/pytorch/blob/main/...#Lxxx`
- `https://github.com/AMD-AGI/Primus-DLRM/blob/main/...#Lxxx`

这类链接几周后就可能跳行，甚至内容变化。对源码导读文章来说，这是事实风险。

建议改法:

- 每篇文章开头加“核对版本”: 例如 `PyTorch v2.12.0`、`CUDA 12.x`、`Primus-DLRM commit abc1234`。
- 所有 GitHub 链接从 `main` 改成具体 tag 或 commit SHA。
- 行号引用旁边写“行号可能随版本变动”，但最好直接 pin commit。

## 全站可读性问题

### AI 味来源

不是因为技术内容像 AI，而是因为表达模式像教程生成稿:

- 标题里频繁出现“全景”“全栈”“完整”“深入”“关键”。
- 正文里高频出现“核心观察”“关键点”“真正的痛点”“本质”“致命约束”。
- 英文版里 `key`、`complete`、`actually`、`real`、`magic` 过多。
- 很多段落先宣布“本文将/本节先/最后给”，再进入内容。
- 结尾常是清单式“坑与边界”，有用，但容易模板化。

建议:

- 技术文章保留清晰结构，但少用夸张判断词。
- 把“全景解析”改成更朴素的主题描述，比如“Context Parallel 方法笔记”。
- 每篇保留一个短 TL;DR，减少正文里的反复 signposting。

### 结构建议

每篇深度技术文建议固定加这 5 个块:

- `适用读者`: 需要哪些前置知识。
- `本文版本`: 代码、库、硬件、论文版本。
- `一句话结论`: 3 到 5 条，不要写成营销摘要。
- `假设与边界`: 哪些公式省略了常数、mask、dtype、overlap。
- `参考资料`: 官方文档、源码 commit、论文、benchmark 来源。

## 逐篇审稿

### 1. `aoti-cuda-deployment.html`

适合公开程度: 暂不建议直接公开。先修 `custom_op`/fake impl/fusion 的事实问题。

优点:

- 阶段划分清楚: export、lowering、Triton、`.pt2`、C++ loader。
- 能把 Python API、生成物、`.so` 边界连起来，这是很有价值的。

主要问题:

- P0: `custom_op + fake impl` 被写成能自动 inline/fuse。应改为 opaque op + fake shape 语义，除非另有 decomposition/lowering 或 `triton_op`。
- `torch._inductor.*` 虽然在官方 AOTInductor 文档出现，但仍是 underscored API。需要写清版本和稳定性边界。
- 对第三方 pybind op 的 AOTI 处理写得很确定。建议拆成“必须 dispatcher-visible”与“C++ runtime 必须加载实现库”两个条件。
- `[[pytorch-shared-libs]]` 这种内部 wiki 链接如果站点没有处理，会让读者困惑。

建议:

- 先把 toy custom op 改成两版: opaque 版和显式 lowering / `triton_op` 版。
- 加一段“我实际验证的环境”: PyTorch、CUDA、Triton、GPU、命令。
- 把“完全融合”“只有 1 次 GPU 访存”改成可验证日志或保守说法。

参考:

- AOTInductor 文档: https://docs.pytorch.org/docs/2.12/user_guide/torch_compiler/torch.compiler_aot_inductor.html
- `torch.library` 文档: https://docs.pytorch.org/docs/2.12/library.html

### 2. `context-parallel.html`

适合公开程度: 可以作为高质量 survey 草稿，但需要修重复 id、公式口径和新方法措辞。

优点:

- 方法覆盖完整，结构从 AllGather 到 Ring、Ulysses、2D、MagiAttention，读者能建立全局图。
- 公式化通信/计算模型是文章核心价值。
- 有较多参考链接，资料意识好。

主要问题:

- 重复 id 很多。
- “所有主流公开方案”“零冗余通信”“任意 mask”“致命约束”都偏绝对。
- Ulysses 通信公式需要明确是 forward、backward、per pass 还是 full layer。
- MagiAttention 属于新方案，很多性能说法来自项目 README/官方博客，建议标为“官方 benchmark claim”。
- “DGX-H100 8 NIC / ring 只用一条路径”这类硬件拓扑判断需要来源。

建议:

- 在 §1 前加“建模假设”: dtype、是否 causal、是否 GQA、是否重叠、是否忽略 softmax 和 reorder。
- 方法总表提前放一张短版，长表放文末。
- 对 MagiAttention 加“未被第三方广泛复现”的提醒。

参考:

- NVIDIA Megatron Bridge HCP 文档: https://docs.nvidia.com/nemo/megatron-bridge/nightly/training/hierarchical-context-parallel.html
- Megatron-Core CP 文档: https://docs.nvidia.com/megatron-core/developer-guide/0.16.0/user-guide/features/context_parallel.html
- Striped Attention: https://arxiv.org/abs/2311.09431
- DeepSpeed Ulysses: https://arxiv.org/abs/2309.14509
- MagiAttention docs: https://sandai-org.github.io/MagiAttention/docs/

### 3. `gemm-ai.html`

适合公开程度: 可公开为数学/性能笔记，但必须补参考资料和硬件数字来源。

优点:

- 推导路线清楚: 方阵、无复用、blocking、任意 tile、两级 blocking、B2B GEMM。
- 对 `K_t` 何时影响 AI 的澄清很好。

主要问题:

- 没有任何外部参考链接。
- H100/B200 平衡点、Hopper L2/HBM 带宽比例、Stream-K/cuBLAS/CUTLASS 调度组合都需要来源或改成量级估算。
- `C = A * B` 和 `C += A * B` 的访存口径需要统一。是否读旧 C、是否写 C、是否 beta=0 要写清。
- “H100 只能发挥不到 4% 峰值”需要用具体峰值与带宽算式支撑。

建议:

- 加 `Assumptions` 小节: dtype、是否读 C、DRAM vs cache、FMA 算 2 FLOPs。
- 补 Roofline、Hong-Kung、CUTLASS Stream-K/B2B、H100/B200 specs 的链接。
- 把 `Takeaway` 改成中文小标题，减少模板感。

### 4. `hopper-cga-cluster.html`

适合公开程度: 暂不建议直接公开。内容价值很高，但没有来源，且部分硬件调度描述像推断。

优点:

- Cluster、DSMEM、cluster barrier、mbarrier、TMA 的组织方式很好。
- CUDA C++ 与 CuTe DSL 双版本例子对读者有帮助。

主要问题:

- 没有外部参考链接。
- “CWD 原子分派”“gang-lock”“地址翻译表”“SM-to-SM 网络带宽远高于 L2 出口”这些说法需要区分官方文档、白皮书、反汇编推断、作者推断。
- `portable` cluster size、非 portable 上限、GPC 约束、grid/cluster 整除，建议引用 CUDA Programming Guide / Runtime API。
- TMA 跨 CTA 例子应标明是否实际编译运行。若只是概念示例，不能写“可运行”。

建议:

- 开头加“本文哪些内容来自官方文档，哪些是推断”。
- 每个例子后面加 tested command 和预期输出。
- 补 CUDA Programming Guide、PTX ISA、CUDA Runtime API、CUTLASS/CuTe docs。

参考:

- CUDA Runtime API `cudaLaunchKernelEx`: https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__EXECUTION.html
- PTX ISA cluster / `barrier.cluster` / `mbarrier`: https://docs.nvidia.com/cuda/parallel-thread-execution/index.html

### 5. `llm-attention-zoo.html`

适合公开程度: 适合作为 living map，不适合作为已完全考证的 survey。

优点:

- 可点击树的形式适合“模型架构地图”。
- 把 dense/sparse/linear/SSM/mLSTM 与正交件分开，读者容易扫全局。

主要问题:

- 很多 2025-2026 模型归类还在快速变化，且树里有“80% 把握”“仓库 URL 不完全确定”的条目。
- DeepSeek V4、Gemma 4、Qwen3.5、Laguna、ZAYA 等叶节点需要逐条来源。否则读者不知道哪些已验证、哪些是占位。
- “参考资料”较粗粒度，模型叶节点没有 source mapping。
- 交互树对搜索引擎和无 JS 环境不友好，建议提供静态表格 fallback。

建议:

- 每个叶节点加 `source` 字段，tooltip 或表格里显示。
- 分成 Verified / Tentative / Placeholder 三类颜色。
- 标明“最后核对日期”。
- 把“Zoo”保留可以，但副标题应写明这是“架构地图草稿”。

参考:

- OpenAI gpt-oss 官方发布: https://openai.com/index/introducing-gpt-oss

### 6. `onetrans-yambda-study.html`

适合公开程度: 适合团队内部或源码读者；公开前需要更友好的问题引入和 commit pin。

优点:

- 资料非常具体，有 schema、feature、embedding、DataLoader、batch flow。
- 这篇 AI 味相对少，更像真实源码研读笔记。

主要问题:

- 标题 `oneTrans+YaMBDA study` 不告诉读者为什么要读。
- 大量 AMD repo 链接指向 `main` 分支行号，需要 pin commit。
- 没有独立参考资料 section，虽然正文里有很多 inline links。
- 重复 id 很多。
- 对非推荐系统读者缺少“这套 pipeline 要解决什么训练问题”的入口。

建议:

- 改标题为“YaMBDA 到 OneTrans: 推荐模型训练数据流笔记”一类。
- 开头加 5 行背景: dataset、task、model、reader target。
- 加 commit hash、config 文件版本、样例 batch 的可复现命令。
- 把 batch tensor flow 图提前，帮助读者建立坐标系。

### 7. `python-imports.html`

适合公开程度: 修正 namespace package 错误后可以公开。

优点:

- 结构清楚，例子贴近真实踩坑。
- 语言比其他深度文更自然，可读性好。

主要问题:

- P0: 把没有 `app/__init__.py` 直接判为相对导入非法，这与 PEP 420 namespace package 不符。
- 没有官方参考资料。
- 重复 id 很多。
- 解析出的标题里带 `#`，可能是 headerlink 文本进入了标题内容。需要浏览器检查是否可见或影响可访问性。

建议:

- 修正 Example 2 的边界。
- 补 Python Language Reference 和 PEP 420。
- 加一句“本文默认 Python 3.11+ / 3.x，Python 2 不讨论”。

参考:

- Python import system: https://docs.python.org/3/reference/import.html
- PEP 420: https://peps.python.org/pep-0420/

### 8. `pytorch-dispatcher.html`

适合公开程度: 技术价值最高之一，但需要先修 `custom_op`/fake impl 问题，并拆掉过于绝对的措辞。

优点:

- 调度键、schema、TORCH_LIBRARY、torchgen、`aten::add` 调用链串得很完整。
- 对源码读者很有帮助。

主要问题:

- P0: `custom_op` “自动登记 Inductor lowering 入口”这类说法不准确。
- `TORCH_SHOW_DISPATCH_TRACE` 需要 caveat。它可能要求 debug/build flag，不应写成所有安装包都直接可用。
- “当旧博客和本文有冲突，trust this article”太绝对。更好的说法是“以你使用的 PyTorch 版本源码为准”。
- Autograd fallback / CompositeImplicitAutograd 的解释有过度简化风险，建议逐段核对 `VariableFallbackKernel.cpp`。
- 重复 id 很多。

建议:

- 把文章拆成两篇: Dispatcher 基础 + `aten::add` 端到端追踪。
- 每个源码表都标 PyTorch 版本。
- 对“当前实现”类句子加版本限定。

参考:

- PyTorch dispatcher tutorial: https://pytorch.org/tutorials/advanced/dispatcher.html
- PyTorch source `DispatchKeySet.h`: https://github.com/pytorch/pytorch/blob/v2.12.0/c10/core/DispatchKeySet.h
- PyTorch `torch.library`: https://docs.pytorch.org/docs/2.12/library.html

### 9. `pytorch-shared-libs.html`

适合公开程度: 可以公开，但要加版本、平台和 wheel 布局 caveat。

优点:

- 依赖图 + 每个 `.so` 的源码目录说明很实用。
- 重复 id 没有问题。
- 参考资料 section 比较完整。

主要问题:

- 仍然指向 PyTorch `main`，建议 pin 到版本。
- “`libtorch_python.so` 即 `torch._C`”需要更精确: `torch._C` 是 Python 扩展模块入口，构建目标和 wheel 布局可能因平台不同而不同；不要让读者以为所有平台文件名都完全一样。
- 应明确本文默认 Linux CUDA wheel，不一定覆盖 macOS、Windows、ROCm、CPU-only、source build。

建议:

- 开头写“本文以 Linux CUDA wheel / PyTorch version X 为准”。
- 图里每个节点标“Python wheel 中是否常见”。
- 参考链接改成 tag/commit。

参考:

- PyTorch CMake `torch_python`: https://github.com/pytorch/pytorch/blob/v2.12.0/torch/CMakeLists.txt
- PyTorch CMake `torch_global_deps`: https://github.com/pytorch/pytorch/blob/v2.12.0/caffe2/CMakeLists.txt
- PyTorch `torch/__init__.py` global deps loading: https://github.com/pytorch/pytorch/blob/v2.12.0/torch/__init__.py

### 10. `pytorch-torch-dispatch-mode.html`

适合公开程度: 适合高级 PyTorch 读者；需要加版本约束并减少“源码真相”式语气。

优点:

- 和 Dispatcher 主文互补，主题明确。
- `PyInterpreterVTable`、`TensorImpl::pyobj_slot`、`PythonFallbackKernel`、mode stack 的线索很有价值。
- 当前 PyTorch source 中确实有 `Python`、`PythonTLSSnapshot`、`PreDispatch`、`PythonDispatcher` 这些 key。

主要问题:

- 大量 private/internal 名称，很容易随版本变化。
- 重复 id 很多。
- 对 C++→Python 跨界成本的数值或组成需要来源，否则应写成定性描述。
- 与 `torch.compile` / AOTAutograd 的关系建议加“版本限定”和“路径之一”，避免写成唯一机制。

建议:

- 开头声明: “以下按 PyTorch v2.12.0 source 描述。”
- 加一张和 `pytorch-dispatcher.html` 的关系图，避免读者从零开始。
- 把“什么时候用/不用”提前，帮助读者判断这篇是否值得读完。

参考:

- PyTorch `DispatchKey.h`: https://github.com/pytorch/pytorch/blob/v2.12.0/c10/core/DispatchKey.h
- PyTorch `PythonFallbackKernel.cpp`: https://github.com/pytorch/pytorch/blob/v2.12.0/aten/src/ATen/core/PythonFallbackKernel.cpp

## 建议修稿顺序

1. 修 P0: AOTI/Dispatcher 的 `custom_op` 语义，Python import 的 namespace package。
2. 修重复 id。这个是机械活，收益很大。
3. 给所有源码/论文型文章加版本锚点和 commit pin。
4. 给 `gemm-ai.html`、`hopper-cga-cluster.html`、`python-imports.html` 补参考资料。
5. 每篇开头加“适用读者 / 本文版本 / 一句话结论 / 假设边界”。
6. 再做文风: 少用“全景、全栈、完整、关键、真正、本质、致命、magic、actually”等词。

## 一句话评价

这些文章的底子很好，不是要“去 AI 化重写”，而是要把几个事实边界修准，把版本证据钉牢，再把读者入口做得更轻。修完之后会更像认真工程师写的源码笔记，而不是一组自动生成的长教程。
