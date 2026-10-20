#!/usr/bin/env python3
"""Build the compact, native Matplotlib reference from the archived 3.5 PDF.

Requires PyMuPDF (tested with 2.0). Run from any directory:
    python scripts/build-matplotlib-cheatsheet.py

The PDF remains the content source. Native HTML headings and code surround
inline SVG figures; no full-page screenshot, object, iframe or PDF viewer is
used. Original clipping paths, hyperlinks, and the two five-column layouts
are retained. Only the small pcolormesh illustration is rendered as a bitmap:
its PDF mesh otherwise expands to ~70,000 SVG paths.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from html import escape
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets/cheatsheets/matplotlib-cheat/matplotlib-cheat.pdf"
POST = ROOT / "posts/cheatsheet-matplotlib.html"
SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)

CODE = {
    "Quick start": """import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

X = np.linspace(0, 2*np.pi, 100)
Y = np.cos(X)

fig, ax = plt.subplots()
ax.plot(X, Y, color='green')

fig.savefig("figure.pdf")
fig.show()""",
    "Animation": """import matplotlib.animation as mpla

T = np.linspace(0, 2*np.pi, 100)
S = np.sin(T)
line, = plt.plot(T, S)
def animate(i):
    line.set_ydata(np.sin(T+i/50))
anim = mpla.FuncAnimation(
    plt.gcf(), animate, interval=5)
plt.show()""",
    "Quick reminder": """ax.grid()
ax.set_[xy]lim(vmin, vmax)
ax.set_[xy]label(label)
ax.set_[xy]ticks(list)
ax.set_[xy]ticklabels(list)
ax.set_title(title)
ax.tick_params(width=10, …)
ax.set_axis_[on|off]()

fig.suptitle(title)
fig.tight_layout()
plt.gcf(), plt.gca()
mpl.rc('axes', linewidth=1, …)
[fig|ax].patch.set_alpha(0)
text=r'$\\frac{-e^{i\\pi}}{2^n}$'""",
    "Event handling": """fig, ax = plt.subplots()
def on_click(event):
    print(event)
fig.canvas.mpl_connect(
  'button_press_event', on_click)""",
}


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def numbers(value: str) -> list[float]:
    return [float(x) for x in re.findall(r"[-+]?(?:\d*\.)?\d+(?:[eE][-+]?\d+)?", value)]


def header_geometry(background: ET.Element) -> tuple[float, float, float, float, float]:
    """Get the original column bounds, header bottom and panel bottom."""
    gray = next(n for n in background if n.get("fill") == "#f2f2f2")
    _, _, _, _, tx, ty = numbers(gray.get("transform", ""))
    x0, y0, y1, x1, _ = numbers(gray.get("d", ""))
    return tx + x0, ty - y1, tx + x1, ty - y0, ty - 0.44832


def local_name(node: ET.Element) -> str:
    return node.tag.split("}")[-1]


def readable_spaces(node: ET.Element) -> None:
    """Restore omitted spaces in monospaced TeX text without moving glyphs."""
    if local_name(node) != "text" or "SourceCodePro" not in node.get("font-family", "").replace(" ", ""):
        return
    size = float(node.get("font-size", "0"))
    advance = size * 0.6
    if not advance:
        return
    for span in node:
        chars = span.text or ""
        xs = numbers(span.get("x", ""))
        if len(chars) != len(xs):
            continue
        new_chars, new_xs = [], []
        for index, (char, x) in enumerate(zip(chars, xs)):
            if index:
                missing = max(0, round((x - xs[index - 1]) / advance) - 1)
                for offset in range(1, min(missing, 12) + 1):
                    new_chars.append(" ")
                    new_xs.append(xs[index - 1] + offset * advance)
            new_chars.append(char)
            new_xs.append(x)
        span.text = "".join(new_chars)
        span.set("x", " ".join(f"{x:.5f}" for x in new_xs))


def inline_svg(
    nodes: list[ET.Element],
    definitions: dict[str, ET.Element],
    bounds: tuple[float, float, float, float],
    prefix: str,
    links: list[dict],
    label: str,
) -> str:
    x0, y0, x1, y1 = bounds
    svg = ET.Element(f"{{{SVG}}}svg", {
        "viewBox": f"{x0:.5f} {y0:.5f} {x1-x0:.5f} {y1-y0:.5f}",
        "class": "mpl-figure",
        "aria-label": label,
    })
    defs = ET.SubElement(svg, f"{{{SVG}}}defs")
    group = ET.SubElement(svg, f"{{{SVG}}}g")
    group.extend(deepcopy(nodes))
    # SVG font fallbacks keep the original per-glyph positions and clipping.
    for node in group.iter():
        if local_name(node) == "text":
            readable_spaces(node)
            family = node.get("font-family", "")
            if "SourceCode" in family.replace(" ", "") or "Mono" in family:
                node.set("font-family", "DejaVu Sans Mono, monospace")
            elif "Serif" in family or "Slab" in family:
                node.set("font-family", "Georgia, serif")
            else:
                node.set("font-family", "DejaVu Sans, Arial, sans-serif")
    present = {node.get("id") for node in group.iter() if node.get("id")}
    scanned = set()
    while True:
        refs = set()
        for node in svg.iter():
            for name, value in node.attrib.items():
                refs.update(re.findall(r"url\(#([^)]*)\)", value))
                if (name == "href" or name.endswith("}href")) and value.startswith("#"):
                    refs.add(value[1:])
        needed = refs - present - scanned
        if not needed:
            break
        for name in sorted(needed):
            if name not in definitions:
                raise ValueError(f"Missing SVG definition: {name}")
            defs.append(deepcopy(definitions[name]))
            scanned.add(name)
    for node in svg.iter():
        if node.get("id"):
            node.set("id", prefix + node.get("id"))
        for name, value in list(node.attrib.items()):
            value = re.sub(r"url\(#([^)]*)\)", lambda m: f"url(#{prefix}{m[1]})", value)
            if (name == "href" or name.endswith("}href")) and value.startswith("#"):
                value = "#" + prefix + value[1:]
            node.set(name, value)
    for link in links:
        rect = link["from"]
        if not link.get("uri"):
            continue
        a = ET.SubElement(svg, f"{{{SVG}}}a", {
            "href": link["uri"], "target": "_blank", "rel": "noopener",
            "class": "mpl-reference", "aria-label": f"{label}: {link['uri']}",
        })
        ET.SubElement(a, f"{{{SVG}}}title").text = link["uri"]
        ET.SubElement(a, f"{{{SVG}}}rect", {
            "x": str(rect.x0), "y": str(rect.y0),
            "width": str(rect.width), "height": str(rect.height),
            "fill": "transparent",
        })
    # Avoid base64 line breaks in embedded source images.
    for node in svg.iter():
        key = f"{{{XLINK}}}href"
        if node.get(key, "").startswith("data:"):
            node.set(key, re.sub(r"\s+", "", node.get(key)))
    return ET.tostring(svg, encoding="unicode")


def build() -> None:
    doc = fitz.open(SOURCE)
    pages = []
    section_count = 0
    link_count = 0
    for page_index, page in enumerate(doc):
        source = ET.fromstring(page.get_svg_image(text_as_path=False))
        definitions = {n.get("id"): n for n in source.iter() if n.get("id")}
        nodes = list(source[-1])
        credits_start = len(nodes)
        font_demo = None
        if page_index == 1:
            credits_start = next(i for i, n in enumerate(nodes)
                                 if compact("".join(n.itertext())) == "MatplotlibCheatsheets")
            # Font-family samples are the subject of this diagram. Preserve
            # their exact glyph outlines instead of substituting browser fonts.
            outlined = ET.fromstring(page.get_svg_image(text_as_path=True))
            outline_defs = {n.get("id"): n for n in outlined.iter() if n.get("id")}
            original_demo = next(n for n in outlined[-1]
                                 if compact("".join(x.get("data-text", "") for x in n.iter()))
                                 .count("Thequickbrownfox") > 3)
            demo_svg = ET.fromstring(inline_svg(
                [original_demo], outline_defs, (0, 0, 841.89, 595.28),
                "mpl-type-samples-", [], "Original font sizes, weights, families and styles"))
            font_demo = ET.Element(f"{{{SVG}}}g")
            font_demo.extend(list(demo_svg))
        headings = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if span["font"] == "RobotoSlab-Regular" and span["size"] > 7.8:
                        headings.append(span)
        starts = []
        for heading in headings:
            indices = [
                i for i, n in enumerate(nodes)
                if local_name(n) == "text"
                and n.get("font-family") == "Roboto Slab"
                and compact("".join(n.itertext())) == compact(heading["text"])
            ]
            if len(indices) != 1:
                raise ValueError(f"Ambiguous heading {heading['text']}")
            starts.append((indices[0] - 1, heading))
        starts.sort()
        columns = [[] for _ in range(5)]
        if page_index == 0:
            columns[0].append('<div class="mpl-brand">' + inline_svg(
                nodes[:starts[0][0]], definitions, (7, 0, 168, 48),
                "mpl-brand-", [], "Matplotlib cheat sheet, version 3.5.0"
            ) + "</div>")

        links = [link for link in page.get_links() if link.get("uri")]
        assigned_links = set()
        for pos, (start, heading) in enumerate(starts):
            stop = starts[pos + 1][0] if pos + 1 < len(starts) else credits_start
            title = heading["text"]
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            slug = f"mpl-{slug}"
            x0, top, x1, body_top, bottom = header_geometry(nodes[start])
            column = round((heading["bbox"][0] - 13.202) / 166.54)
            body_nodes = nodes[start + 2:stop]
            header_links, body_links = [], []
            for index, link in enumerate(links):
                rect = link["from"]
                cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
                if x0 <= cx <= x1 and top <= cy <= bottom:
                    (header_links if cy < body_top else body_links).append(link)
                    assigned_links.add(index)
            api = "".join(
                f'<a class="mpl-api" href="{escape(link["uri"], quote=True)}" '
                f'target="_blank" rel="noopener" aria-label="{escape(title)} API">'
                f'{"READ" if title == "Ten simple rules" else "API"} ↗</a>'
                for link in header_links
            )
            # Plotting this one PDF mesh as vectors is disproportionate for its
            # ~28-point square. Preserve its source rendering at 6 px/point.
            if title == "Basic plots":
                body_nodes = deepcopy(body_nodes)
                heavy = next((n for n in body_nodes if len(ET.tostring(n)) > 5_000_000), None)
                if heavy is None:
                    raise ValueError("Expected original pcolormesh illustration")
                rect = fitz.Rect(177.76107, 202.24678 - .95145 * 29,
                                 177.76107 + .95145 * 29, 202.24678)
                image_data = page.get_pixmap(matrix=fitz.Matrix(6, 6), clip=rect, alpha=False).tobytes("png")
                image = ET.Element(f"{{{SVG}}}image", {
                    "x": str(rect.x0), "y": str(rect.y0),
                    "width": str(rect.width), "height": str(rect.height),
                    f"{{{XLINK}}}href": "data:image/png;base64," + base64.b64encode(image_data).decode(),
                })
                body_nodes[body_nodes.index(heavy)] = image
            if title == "Text parameters":
                body_nodes = deepcopy(body_nodes)
                demo = next(n for n in body_nodes
                            if compact("".join(n.itertext())).count("Thequickbrownfox") > 3)
                body_nodes[body_nodes.index(demo)] = font_demo
            if title in CODE:
                original_code = page.get_text("text", clip=fitz.Rect(x0, body_top, x1, bottom))
                quote_map = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
                assert compact(original_code.translate(quote_map)) == compact(CODE[title]), title
                body = '<div class="mpl-code"><pre><code>' + escape(CODE[title]) + "</code></pre></div>"
            elif title == "Getting help":
                labels = [
                    "matplotlib.org", "github.com/matplotlib/matplotlib/issues",
                    "discourse.matplotlib.org", "stackoverflow.com/questions/tagged/matplotlib",
                    "gitter.im/matplotlib", "twitter.com/matplotlib", "Matplotlib users mailing list",
                ]
                assert len(body_links) == len(labels)
                body = '<ul class="mpl-help">' + "".join(
                    f'<li><a class="mpl-reference" href="{escape(link["uri"], quote=True)}" '
                    f'target="_blank" rel="noopener">{escape(label)}</a></li>'
                    for label, link in zip(labels, sorted(body_links, key=lambda x: x["from"].y0))
                ) + "</ul>"
            else:
                body = inline_svg(body_nodes, definitions, (x0, body_top, x1, bottom),
                                  slug + "-", body_links, title)
            columns[column].append(
                f'<section class="mpl-panel" aria-labelledby="{slug}">'
                f'<div class="mpl-panel-heading"><h3 id="{slug}">{escape(title)}</h3>{api}</div>'
                + body + "</section>"
            )
            section_count += 1
        if page_index == 1:
            # The source credits and NumFOCUS logo sit below the last panel.
            footer_links = []
            for index, link in enumerate(links):
                rect = link["from"]
                if 674 <= rect.x0 <= 835 and 500 <= rect.y0 <= 589:
                    footer_links.append(link)
                    assigned_links.add(index)
            columns[4].append('<div class="mpl-credits-art">' + inline_svg(
                nodes[credits_start:], definitions, (674, 500, 835, 589),
                "mpl-credits-", footer_links, "Matplotlib Development Team · CC BY 4.0 · NumFOCUS"
            ) + "</div>")
        if len(assigned_links) != len(links):
            raise ValueError(f"Unassigned links on page {page_index+1}: {set(range(len(links)))-assigned_links}")
        link_count += len(links)
        pages.append('<div class="mpl-grid">' + "".join(
            '<div class="mpl-column">' + "\n".join(column) + "</div>" for column in columns
        ) + "</div>")
    assert section_count == 38, section_count
    assert link_count == 63, link_count

    zh = "Matplotlib 绘图、配色、坐标轴与标注速查，保留 3.5.0 版的紧凑分栏、代码和图例。"
    en = "A compact reference for plots, colors, axes, and annotations, preserving the code and visual examples from the Matplotlib 3.5.0 cheatsheet."
    # Keep the article metadata stable; the body is deterministic from the PDF.
    head = POST.read_text().split("<body>")[0]
    for field, value in [("summary", zh), ("summary_en", en)]:
        head = re.sub(rf'(<meta name="post:{field}" content=")[^"]*(">)',
                      lambda m: m[1] + value + m[2], head)
    head = re.sub(r'  <link rel="stylesheet" href="../assets/cheatsheets/matplotlib-cheat.css[^"]*">\n', "", head)
    head = head.replace('  <script src="../assets/cheatsheets/cheatsheets.js" defer></script>\n', "")
    head = head.replace('  <script src="../lang-toggle.js',
                        '  <link rel="stylesheet" href="../assets/cheatsheets/matplotlib-cheat.css?v=inline-1">\n'
                        '  <script src="../lang-toggle.js')
    POST.write_text(head + f"""<body>
<div class="layout">
  <aside class="toc"><div class="toc-title">目录 · TOC</div></aside>
  <main class="content">
    <div class="cheatsheet-intro">
      <div class="lang-zh"><h1>Matplotlib 速查</h1><p class="lead">{zh}</p></div>
      <div class="lang-en"><h1>Matplotlib Cheatsheet</h1><p class="lead">{en}</p></div>
    </div>
    <div class="cheatsheet-sheet sheet-matplotlib-cheat">
      <p class="mpl-version">Matplotlib 3.5.0 · 2021</p>
      <h2 id="page-1">Plots &amp; essentials</h2>
      {pages[0]}
      <h2 id="page-2">Layout, colors &amp; annotations</h2>
      {pages[1]}
      <footer class="mpl-attribution">
        <p>© 2021 Matplotlib Development Team ·
        <a href="https://github.com/matplotlib/cheatsheets">Matplotlib Cheatsheets</a> ·
        <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a></p>
        <p class="lang-zh">依据原版两页速查表改编为网页分栏；保留原版内容与 API 链接，代码中的排版引号替换为普通引号。方括号、竖线和省略号表示速记选项。旧版 API、第三方样式名及链接沿用原版。</p>
        <p class="lang-en">Adapted from the original two-page reference into web columns. Original content and API links are retained; typographic code quotes are normalized. Brackets, pipes and ellipses denote shorthand. Historical APIs, third-party style names and links are unchanged.</p>
      </footer>
    </div>
  </main>
</div>
</body>
</html>
""")
    print(f"Built {section_count} sections, {link_count} source links; {POST.stat().st_size:,} bytes")


if __name__ == "__main__":
    build()
