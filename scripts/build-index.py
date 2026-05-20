#!/usr/bin/env python3
"""Scan posts/ and generate posts.json for the landing page.

Each post HTML is expected to contain:
    <meta name="post:title"   content="...">
    <meta name="post:slug"    content="...">
    <meta name="post:date"    content="YYYY-MM-DD">
    <meta name="post:tags"    content="tag1, tag2, ...">
    <meta name="post:reading" content="... 分钟">
    <meta name="post:summary" content="...">

Posts without metadata are skipped (with a warning).
Output is sorted by date descending (newest first).
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
OUT_FILE = ROOT / "posts.json"

META_RE = re.compile(
    r'<meta\s+name="post:(?P<key>[^"]+)"\s+content="(?P<val>[^"]*)"\s*/?>',
    re.IGNORECASE,
)


def extract_metadata(html_path: Path) -> dict | None:
    html = html_path.read_text(encoding="utf-8")
    head = html[: html.lower().find("</head>") if "</head>" in html.lower() else 8192]
    meta = {m.group("key"): m.group("val") for m in META_RE.finditer(head)}
    required = {"title", "slug", "date"}
    if not required.issubset(meta):
        print(
            f"  ⚠  {html_path.name}: missing required meta "
            f"({required - meta.keys()}), skipped",
            file=sys.stderr,
        )
        return None
    # normalize
    tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    tags_en = [t.strip() for t in meta.get("tags_en", "").split(",") if t.strip()]
    entry = {
        "title": meta["title"],
        "slug": meta["slug"],
        "date": meta["date"],
        "tags": tags,
        "reading": meta.get("reading", ""),
        "summary": meta.get("summary", ""),
    }
    # optional English fields — only included when present
    for k in ("title_en", "reading_en", "summary_en"):
        if meta.get(k):
            entry[k] = meta[k]
    if tags_en:
        entry["tags_en"] = tags_en
    # optional series fields
    if meta.get("series"):
        entry["series"] = meta["series"]
        if meta.get("series_title"):
            entry["series_title"] = meta["series_title"]
        if meta.get("series_title_en"):
            entry["series_title_en"] = meta["series_title_en"]
        try:
            entry["series_order"] = int(meta.get("series_order", "0"))
        except ValueError:
            entry["series_order"] = 0
    return entry


def main() -> int:
    if not POSTS_DIR.is_dir():
        print(f"posts/ dir not found at {POSTS_DIR}", file=sys.stderr)
        return 1

    entries = []
    for html in sorted(POSTS_DIR.glob("*.html")):
        meta = extract_metadata(html)
        if meta:
            entries.append(meta)
            print(f"  ✓  {html.name} → slug={meta['slug']}, {len(meta['tags'])} tag(s)")

    # newest first
    entries.sort(key=lambda e: e["date"], reverse=True)

    OUT_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {len(entries)} entries → {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
