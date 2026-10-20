# 可视化工具 / Visualization Tools

The series entries are `posts/bottleneck-visualizer.html` (order 1) and
`posts/roofline-visualizer.html` (order 2). Run `python3.11 -B scripts/build-index.py`
after changing their metadata. The home-page series filter and article series
links are generated from `posts.json`.

Each entry embeds one local tool document; language changes keep that instance
alive. Both tools also work as standalone pages. `embed.js` applies the article's
theme and language to the frame. `tool-shell.js` reports content height back to
the article, with source/origin checks on the receiving side.

## Sources and adaptations

- `bottleneck/index.html`: migrated from the user-provided
  `/tmp/bottleneck-analyzer.html` on 2026-10-19. Keeps the SVG barrel, stage
  controls, and SVG export. Uses normalized capacity instead of utilization,
  handles tied bottlenecks, adds reset/download controls, escapes stage names,
  and preserves the active range input while dragging.
- `roofline/index.html`: migrated from
  <https://jacocheung.github.io/visualization/roofline/index.html> on 2026-10-19.
  Keeps hardware presets, workload formulas, editing/visibility controls,
  tooltips, axis selection, fitting, and browser persistence. Adds an adaptive
  article embed, light theme, keyboard/touch point details, and escaped names.
  The storage key is `notes-roofline-studio-v1`; it does not overwrite the
  original tool's saved configuration. The default B200 uses FP16 to match the
  default workloads. Preset values are a snapshot, not automatically updated
  hardware specifications.

## Local dependencies

No tool functionality depends on a CDN.

- `vendor/d3-7.9.0.min.js`: D3 7.9.0, from the `d3@7.9.0` npm distribution.
  ISC license: `vendor/D3-LICENSE`.
- `vendor/katex-0.16.11/`: KaTeX 0.16.11, from the `katex@0.16.11` npm
  distribution. MIT license: `vendor/katex-0.16.11/LICENSE`. CSS retains the
  original WOFF2 font sources; unused WOFF and TTF fallbacks were removed.

These third-party files retain their own licenses. No build step is needed to
serve the tools: they are regular static HTML, CSS, JavaScript, and font assets.
