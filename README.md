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

- 普通表格和代码块按内容占宽并居中，内部文字左对齐；超出可用宽度时在组件内横向滚动。
- 静态 SVG 根据 `viewBox` 限制放大，窄屏缩小适配；图示已有的缩放控件继续可用。
- 并排代码用内容决定列宽，整组居中；窄屏滚动整个对照组，保持两栏的对应关系。
- Cheatsheet 和交互工具保留各自的网格布局。

公共尺寸集中在 `--post-content-max`、`--post-prose-max`、`--post-rail-width` 等 CSS 变量中。新增文章应沿用公共规则，避免为 `main.content` 单独设固定宽度或强制所有组件铺满。

## 功能

- KaTeX 渲染数学公式（CDN）
- ☀️ / 🌙 / 🌓 三态主题切换（localStorage 持久化）
- 📖 左侧目录导航（IntersectionObserver 高亮当前段）
- ⬇ 一键导出 Markdown 源
- 首页按系列分组并默认折叠，支持中英文搜索与系列筛选
- 💬 Giscus 评论（基于 GitHub Discussions）

## License

内容：CC BY 4.0 · 代码：MIT
