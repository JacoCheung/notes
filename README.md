# Notes

学习笔记与技术文章。

**线上访问**：<https://jacocheung.github.io/notes/>

## 目录结构

```
index.html                   — 文章索引（数据来自 posts.json，前端渲染）
posts.json                   — 文章元数据（由 CI 自动生成，不要手改）
posts/<slug>.html            — 单篇文章，每篇一个独立 HTML
scripts/build-index.py       — 扫描 posts/*.html 生成 posts.json
.github/workflows/           — push 时自动重建 posts.json
```

## 加一篇新文章的流程

1. 在 `posts/<slug>.html` 放好文章 HTML。
2. 在 `<head>` 里加 metadata（这是 CI 识别文章的依据）：

   ```html
   <meta name="post:title"   content="文章标题">
   <meta name="post:slug"    content="slug">
   <meta name="post:date"    content="YYYY-MM-DD">
   <meta name="post:tags"    content="GPU, CUDA, 性能分析">
   <meta name="post:reading" content="10 分钟">
   <meta name="post:summary" content="摘要,一两句话">
   ```

3. 本地先跑一下（可选）：`python3 scripts/build-index.py`
4. `git add posts/<slug>.html && git commit -m "Add: 文章标题" && git push`
5. GitHub Action 会自动重建 `posts.json` 并再 push 一次。Pages 随后重新部署。

## 本地预览

```bash
python3 -m http.server -d . 8080
# 浏览器访问 http://localhost:8080
```

## 文章排版

文章共用 `assets/site.css` 和 `lang-toggle.js`。页面宽度随视口变化，正文阅读栏居中并控制行长，标题和段落保持左对齐。代码、表格及插图与阅读栏共享中心线；宽图和交互工具可使用更宽的内容区。桌面目录位于左侧，窄屏目录移入正文。

- 文章代码块与正文栏等宽、居中，内部文字左对齐；统一使用等宽字体，桌面 14px、手机 13px、行高 1.55。长行在块内横向滚动，保留缩进。
- 代码高亮由共享脚本 `assets/post-content.js` 加载本地 Highlight.js，支持深浅主题。优先读取 `<pre data-language="python">` 或 `<code class="language-cpp">`；未标注源码会保守识别。日志和调用树使用 `data-language="text"`，源码链接与注释节点保留。
- 普通表格居中，超出可用宽度时在组件内横向滚动。
- 插图、SVG 和 SVG object 共用中心线，最大宽度为 72rem，保持比例并以原图宽度限制放大；默认适应宽度，已有的原尺寸和缩放控件继续可用。图注统一为 13px、1.6 行高。
- 并排代码用内容决定列宽，整组居中；窄屏滚动整个对照组，保持两栏的对应关系。
- Cheatsheet 保留网格布局，代码沿用公共字体与高亮，使用较小内边距；命令允许折行并为复制按钮预留空间。交互工具保留自身的输出布局。

公共尺寸集中在 `assets/site.css` 的 CSS 变量中：`--post-content-max`、`--post-prose-max`、`--post-rail-width` 控制阅读布局，`--post-code-font`、`--post-code-size`、`--post-code-leading`、`--post-code-padding` 控制代码块，`--post-media-max`、`--post-block-gap`、`--post-caption-size` 控制插图与间距。新增文章应沿用公共规则，避免为 `main.content` 单独设固定宽度。交互工具可用 `data-post-format="off"` 保留内部布局。

## 功能

- KaTeX 渲染数学公式（CDN）
- ☀️ / 🌙 / 🌓 三态主题切换（localStorage 持久化）
- 📖 左侧目录导航（IntersectionObserver 高亮当前段）
- ⬇ 一键导出 Markdown 源
- 首页按系列分组并默认折叠，支持中英文搜索与系列筛选
- 💬 Giscus 评论（基于 GitHub Discussions）

## License

内容：CC BY 4.0 · 代码：MIT
