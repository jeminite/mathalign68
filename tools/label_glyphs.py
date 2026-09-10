#!/usr/bin/env python3
"""
Build and label the glyph table that decodes the mathematics in these PDFs.

  python3 tools/label_glyphs.py scan sources/2026-released-items-math-g7.pdf
  python3 tools/label_glyphs.py sheet            # contact sheet of unlabelled shapes
  python3 tools/label_glyphs.py sheet --all      # every shape, labelled or not
  python3 tools/label_glyphs.py set g001=3 g002=5 g003=. g004='$'
  python3 tools/label_glyphs.py status

`scan` clusters every glyph-shaped vector path in the item pages of one PDF and
records the new shapes in `data/glyphs.json`. `sheet` renders each unlabelled
cluster at 10x as a labelled tile so a person -- or a vision pass that is then
spot-checked -- can read them all in one look. `set` applies the labels.

The point of the two-step is that labelling is the only judgement in the whole
decode, it is a few dozen decisions per font rather than a few hundred per test,
and once made it is reused by every later test that embeds the same font.

Labels are single characters, or a short string for a multi-character shape.
Use `?` to mark a shape you could not identify: it stays unlabelled and any hole
containing it will refuse to decode.
"""

import argparse
import json
import os
import sys

try:
    import fitz
except ImportError:
    sys.exit("PyMuPDF is required (poppler is not installed on this machine).")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from glyphs import GlyphTable, shape_of          # noqa: E402

PROV = os.path.join(ROOT, "provenance")
SHEET = os.path.join(PROV, "glyph_sheet.png")

TILE_ZOOM = 10          # a 5pt glyph becomes 50px, comfortably readable
COLS = 10
CELL_W, CELL_H = 78, 62


def item_pages(pdf_path):
    """Pages holding items: everything except the front matter, the session
    covers and the item map. Derived from the pagemap when one exists, so the
    two never drift."""
    base = os.path.basename(pdf_path)
    import re
    m = re.search(r"(\d{4})-released-items-math-g(\d)", base)
    if m:
        test_id = "g%s-%s" % (m.group(2), m.group(1))
        pagemap = os.path.join(PROV, "pagemap_%s.json" % test_id)
        if os.path.exists(pagemap):
            recs = json.load(open(pagemap))["items"]
            return sorted({r["pdfPage"] for r in recs.values()}), test_id
    doc = fitz.open(pdf_path)
    return list(range(1, doc.page_count + 1)), None


def cmd_scan(args):
    table = GlyphTable()
    before = len(table.clusters)
    pages, test_id = item_pages(args.pdf)
    doc = fitz.open(args.pdf)

    seen = 0
    for page_no in pages:
        page = doc[page_no - 1]
        for dr in page.get_drawings():
            shape = shape_of(dr)
            if shape is None:
                continue
            seen += 1
            r = dr["rect"]
            table.observe(shape, {
                "source": os.path.relpath(os.path.abspath(args.pdf), ROOT),
                "page": page_no,
                "rect": [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)],
            })

    table.save()
    new = len(table.clusters) - before
    unlabelled = [c for c in table.clusters if c["label"] is None]
    print("scanned %s%s" % (os.path.basename(args.pdf),
                            " (%s)" % test_id if test_id else ""))
    print("  %d glyph-shaped paths across %d item pages" % (seen, len(pages)))
    print("  %d clusters total, %d new" % (len(table.clusters), new))
    print("  %d unlabelled, covering %d instances"
          % (len(unlabelled), sum(c["count"] for c in unlabelled)))
    if unlabelled:
        print("\n  next: python3 tools/label_glyphs.py sheet")


def cmd_sheet(args):
    table = GlyphTable()
    pool = table.clusters if args.all else [c for c in table.clusters if c["label"] is None]
    pool = sorted(pool, key=lambda c: -c["count"])
    if not pool:
        print("nothing to render -- every cluster is labelled")
        return

    rows = (len(pool) + COLS - 1) // COLS
    out = fitz.open()
    page = out.new_page(width=COLS * CELL_W + 20, height=rows * CELL_H + 40)
    page.insert_text((12, 22),
                     "%d %sglyph shapes, most frequent first"
                     % (len(pool), "" if args.all else "unlabelled "),
                     fontsize=11)

    for i, cluster in enumerate(pool):
        cx = 12 + (i % COLS) * CELL_W
        cy = 34 + (i // COLS) * CELL_H
        sample = cluster["samples"][0]
        src = os.path.join(ROOT, sample["source"])
        doc = fitz.open(src)
        x0, y0, x1, y1 = sample["rect"]
        pad = 1.0
        pix = doc[sample["page"] - 1].get_pixmap(
            matrix=fitz.Matrix(TILE_ZOOM, TILE_ZOOM),
            clip=fitz.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad))
        # Fit the tile into the cell, preserving aspect.
        max_w, max_h = CELL_W - 14, CELL_H - 26
        scale = min(max_w / pix.width, max_h / pix.height)
        w, h = pix.width * scale, pix.height * scale
        page.insert_image(fitz.Rect(cx + (max_w - w) / 2 + 7, cy, cx + (max_w - w) / 2 + 7 + w, cy + h),
                          pixmap=pix)
        page.insert_text((cx + 4, cy + CELL_H - 14),
                         "%s  x%d" % (cluster["id"], cluster["count"]), fontsize=6.5)
        doc.close()

    os.makedirs(PROV, exist_ok=True)
    pm = out[0].get_pixmap(matrix=fitz.Matrix(2, 2))
    pm.save(SHEET)
    print("wrote %s  (%dx%d)" % (os.path.relpath(SHEET, ROOT), pm.width, pm.height))
    print("  %d shapes; label them with:" % len(pool))
    print("  python3 tools/label_glyphs.py set %s=X %s=Y ..." % (pool[0]["id"], pool[1]["id"] if len(pool) > 1 else "g002"))


def cmd_set(args):
    table = GlyphTable()
    by_id = {c["id"]: c for c in table.clusters}
    applied, problems = 0, []
    for pair in args.pairs:
        if "=" not in pair:
            problems.append("%r is not id=label" % pair)
            continue
        gid, label = pair.split("=", 1)
        cluster = by_id.get(gid)
        if cluster is None:
            problems.append("no cluster %s" % gid)
            continue
        if label in ("?", ""):
            cluster["label"] = None
            applied += 1
            continue
        if cluster["label"] is not None and cluster["label"] != label:
            problems.append("%s is already labelled %r; refusing to change it to %r "
                            "(delete the label first if that is really intended)"
                            % (gid, cluster["label"], label))
            continue
        cluster["label"] = label
        applied += 1

    # One shape must never carry two meanings, and two shapes carrying the same
    # meaning is normal (a font has several dollar-sign placements). Only the
    # first direction is an error.
    if problems:
        for p in problems:
            print("  problem: %s" % p)
    table.save()
    unlabelled = sum(1 for c in table.clusters if c["label"] is None)
    print("applied %d label(s); %d cluster(s) still unlabelled" % (applied, unlabelled))
    if problems:
        sys.exit(1)


def cmd_status(args):
    table = GlyphTable()
    if not table.clusters:
        print("no glyph table yet -- run: python3 tools/label_glyphs.py scan <pdf>")
        return
    labelled = [c for c in table.clusters if c["label"] is not None]
    unlabelled = [c for c in table.clusters if c["label"] is None]
    total = sum(c["count"] for c in table.clusters)
    covered = sum(c["count"] for c in labelled)
    print("%d clusters, %d labelled, %d unlabelled"
          % (len(table.clusters), len(labelled), len(unlabelled)))
    print("%d instances, %d decodable (%.1f%%)"
          % (total, covered, 100.0 * covered / total if total else 0))
    by_label = {}
    for c in labelled:
        by_label.setdefault(c["label"], []).append(c)
    if by_label:
        print("\nlabels in use:")
        for label in sorted(by_label):
            cs = by_label[label]
            print("  %-4r %d shape(s), %d instances"
                  % (label, len(cs), sum(c["count"] for c in cs)))
    if unlabelled:
        print("\nunlabelled, most frequent first:")
        for c in sorted(unlabelled, key=lambda c: -c["count"])[:20]:
            print("  %s  x%-4d  %.1f x %.1f pt, %d path items%s"
                  % (c["id"], c["count"], c["shape"]["width"], c["shape"]["height"],
                     c["shape"]["items"], "  (thin)" if c["shape"]["degenerate"] else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("scan", help="cluster the glyphs in one PDF")
    p.add_argument("pdf")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("sheet", help="render a contact sheet of shapes to label")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_sheet)

    p = sub.add_parser("set", help="apply labels: g001=3 g002=5")
    p.add_argument("pairs", nargs="+")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("status", help="how much of the table is labelled")
    p.set_defaults(func=cmd_status)

    args = ap.parse_args()
    if not getattr(args, "func", None):
        args = ap.parse_args(["status"])
    args.func(args)


if __name__ == "__main__":
    main()
