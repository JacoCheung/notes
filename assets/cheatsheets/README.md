# Cheatsheets

Eight reference sheets were migrated from
<https://jacocheung.github.io/visualization/cheatsheets/> on 2026-10-19.
The published HTML was compared with the corresponding local source checkout;
all eight source documents matched.

| Order | Original directory | Notes article |
| --- | --- | --- |
| 1 | `typst-basic/` | `posts/cheatsheet-typst.html` |
| 2 | `matplotlib-cheat/` | `posts/cheatsheet-matplotlib.html` |
| 3 | `color-map/` | `posts/cheatsheet-colormaps.html` |
| 4 | `chrome-keyboard-shortcuts/` | `posts/cheatsheet-chrome-shortcuts.html` |
| 5 | `codex/` | `posts/cheatsheet-codex.html` |
| 6 | `claude-code/` | `posts/cheatsheet-claude-code.html` |
| 7 | `cupti/` | `posts/cheatsheet-cupti.html` |
| 8 | `nv-gpu-family/` | `posts/cheatsheet-nvidia-gpu.html` |

## Integration

The articles contain the full native HTML content, including the original
tables, code examples, search data, and source references. They do not iframe
the previous site. Metadata adds the `cheatsheets` series to the existing home
index and article navigation. Run `python3.11 -B scripts/build-index.py` after
changing metadata.

Per-sheet CSS is scoped to `.post-page main.content .cheatsheet-sheet` so the
original resets and print layouts do not replace the site's navigation styles.
`cheatsheets.css` handles article width, responsive tables, printable layouts,
and SVG viewers. The reference sheet colors are retained; the GPU reference's
existing light/dark palettes also follow the site theme.

`cheatsheets.js` adds SVG zoom controls and keeps headings stable across search
updates for TOC navigation. Hidden targets are restored before following a TOC
link. Dynamic section headings use stable IDs and participate in the shared
two-level, collapsible TOC.

## Preserved assets and behavior

- Matplotlib and Chrome retain both original SVGs, their referenced PNGs, and
  the PDF. These assets are copied byte for byte. The SVG files contain raster
  backgrounds and selectable text layers; they are not newly redrawn vectors.
- Codex retains search and browser printing.
- Claude Code retains fuzzy search, result highlighting, platform selection,
  and printing. Its script is scoped to avoid a global variable collision with
  Fuse. The original decorative language switch was removed; the site language
  control translates the article shell, while reference content retains its
  original language.
- CUPTI retains all 24 table definitions, field search, CPU/GPU/MIXED/META
  filters, the relationship diagram, and printing.
- Typst examples, GPU tables, and colormap definitions are preserved. Colormap
  strips are CSS approximations, as in the source.

This is a content migration, not a fresh review of every command or GPU
specification. Original version notes and reference links remain in the sheets.

`vendor/fuse-7.1.0.min.js` is the Fuse.js 7.1.0 npm distribution. Its Apache 2.0
license is retained in `vendor/Fuse-LICENSE`. Search does not require a CDN, and
the original fallback search implementation remains available.
