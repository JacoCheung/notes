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

## 功能

- KaTeX 渲染数学公式（CDN）
- ☀️ / 🌙 / 🌓 三态主题切换（localStorage 持久化）
- 📖 左侧目录导航（IntersectionObserver 高亮当前段）
- ⬇ 一键导出 Markdown 源
- 🏷️ 标签过滤（landing 页）
- 💬 Giscus 评论（基于 GitHub Discussions）

## License

内容：CC BY 4.0 · 代码：MIT
