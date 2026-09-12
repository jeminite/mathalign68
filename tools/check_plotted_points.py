#!/usr/bin/env python3
"""Check a figure's written coordinates against the points the PDF actually plots.

Every other fidelity check in this project compares a published field against an
independent source: a stem against the PDF's text layer, an answer against
NYSED's item map. A figure's `longDescription` had no such source. It is written
by hand from the artwork, it is what a screen-reader user is given INSTEAD of the
picture, and nothing could contradict it.

So it drifted. An audit of the twelve coordinate-plane figures in the corpus
found NINE whose stated coordinates disagreed with the drawing -- including
g8-2026-029, where the description put B one unit off and C four units off, so
the segment it describes is 5 units long and the item's own answer key says 6;
and g8-2026-001, where all three vertices were wrong and the translated vertex
the item asks for was not among the answer choices. Errors of one unit dominate,
which is what reading a grid by eye produces.

A coordinate plane is vector artwork, so the drawing can be read back. The grid
gives the spacing, the axes are the two lines long enough to carry an arrowhead
at each end, and a plotted point is a small filled circle. Divide and the
coordinates fall out. What this CANNOT do is read the axis tick labels -- they
are drawn as glyph outlines, not text -- so the units per grid square are
unknown, and the checker tries 1 and 2 and reports which fits. Where the drawing
cannot be read confidently the item is reported as unchecked, never as passing:
a plot with no negative quadrant draws its axis on top of the box edge, and
there the origin genuinely cannot be told apart from the corner.

Run it directly for a report, or import `plotted()` -- preflight does.
"""
import collections
import json
import os
import re
import sys

try:
    import fitz
except ImportError:                                  # pragma: no cover
    fitz = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "sources")

# "at negative 4, 3", "at 7, negative 3", "J at 1, 8"
COORD_RE = re.compile(r"\b(?:at|to)\s+(negative\s+)?(\d+)\s*,\s*(negative\s+)?(\d+)\b",
                      re.I)
# A dot is a filled circle a few points across. Below 2.5pt it is a decimal
# point or the tittle of an "i"; above 8pt it is not a plotted point.
DOT_MIN, DOT_MAX = 2.5, 8.0


def stated(text):
    """The coordinate pairs a description claims, as a set."""
    out = set()
    for neg_x, x, neg_y, y in COORD_RE.findall(text or ""):
        out.add(((-1 if neg_x else 1) * int(x), (-1 if neg_y else 1) * int(y)))
    return out


def plotted(pdf_path, page_no):
    """The points the artwork plots, or None if the plane cannot be read.

    Returns (points, units_per_square_is_unknown) -- the caller decides the
    scale, because the tick labels are outlines and cannot be read here.
    """
    if fitz is None:
        return None
    doc = fitz.open(pdf_path)
    page = doc[page_no - 1]
    V, H, dots = [], [], []
    for dr in page.get_drawings():
        r = dr["rect"]
        if r.height > 30 and r.width < 1.5:
            V.append((r.x0 + r.width / 2, r.y0, r.y1))
        if r.width > 30 and r.height < 1.5:
            H.append((r.y0 + r.height / 2, r.x0, r.x1))
        w, h = r.width, r.height
        if DOT_MIN < w < DOT_MAX and DOT_MIN < h < DOT_MAX \
                and abs(w - h) < 1.2 and dr.get("fill"):
            dots.append((r.x0 + w / 2, r.y0 + h / 2))
    doc.close()
    if not V or not H or not dots:
        return None

    vx = sorted({round(x, 1) for x, _, _ in V})
    hy = sorted({round(y, 1) for y, _, _ in H})
    if len(vx) < 4:
        return None
    gaps = collections.Counter(round(b - a, 1) for a, b in zip(vx, vx[1:]))
    sp = gaps.most_common(1)[0][0]
    if sp < 4:
        return None

    def cluster(vals):
        """The longest run of lines one grid-space apart: the plot's own grid,
        with any stray rule on the page left outside it."""
        best = run = [vals[0]]
        for a, b in zip(vals, vals[1:]):
            if abs((b - a) - sp) < 0.6:
                run = run + [b]
            else:
                if len(run) > len(best):
                    best = run
                run = [b]
        return best if len(best) >= len(run) else run

    gx, gy = cluster(vx), cluster(hy)

    def axis(lines, within):
        # Grid lines are drawn in two halves, split where the axis crosses them,
        # so one coordinate carries several segments; merge before measuring.
        # Then the axis is the longest line in the plot area, because it is the
        # one with an arrowhead at each end. Restricting to the plot area first
        # matters: the page's footer rule is longer than any axis.
        span = {}
        for c, a, b in lines:
            c = round(c, 1)
            if not (within[0] - 2 * sp <= c <= within[-1] + 2 * sp):
                continue
            lo, hi = span.get(c, (a, b))
            span[c] = (min(lo, a), max(hi, b))
        if not span:
            return None
        ranked = sorted(span.items(), key=lambda kv: kv[1][1] - kv[1][0], reverse=True)
        best = ranked[0][1][1] - ranked[0][1][0]
        runner = (ranked[1][1][1] - ranked[1][1][0]) if len(ranked) > 1 else 0
        # A plot with no negative quadrant draws its axis along the box edge, so
        # nothing stands out and the origin cannot be told from the corner.
        # Refuse rather than answer confidently one square out.
        return ranked[0][0] if best - runner >= 2 else None

    yax, xax = axis(V, gx), axis(H, gy)
    if yax is None or xax is None:
        return None

    out = set()
    for dx, dy in dots:
        if not (gx[0] - sp <= dx <= gx[-1] + sp and gy[0] - sp <= dy <= gy[-1] + sp):
            continue
        a, b = (dx - yax) / sp, -(dy - xax) / sp
        # Letter labels sit beside the dots and contribute round fragments of
        # their own; only a point landing on a lattice intersection is a plot.
        if abs(a - round(a)) < 0.12 and abs(b - round(b)) < 0.12:
            out.add((int(round(a)), int(round(b))))
    return out or None


def compare(said, drawn):
    """Does the description agree with the drawing, at 1 or 2 units per square?"""
    for scale in (1, 2):
        if said == {(x * scale, y * scale) for x, y in drawn}:
            return True, scale
    return False, None


def main():
    items = {i["id"]: i for i in
             json.load(open(os.path.join(ROOT, "data", "items.json")))["items"]}
    content = json.load(open(os.path.join(ROOT, "data", "content.json")))
    box = content["items"] if "items" in content else content

    ok = bad = unchecked = 0
    problems, skipped = [], []
    for item_id, entry in sorted(box.items()):
        for fig in entry.get("figures") or []:
            said = stated(fig.get("longDescription"))
            if len(said) < 2:
                continue
            item = items.get(item_id)
            if not item:
                continue
            grade, year, _ = item_id.split("-")
            pdf = os.path.join(SOURCES, "%s-released-items-math-%s.pdf" % (year, grade))
            if not os.path.exists(pdf):
                continue
            drawn = plotted(pdf, item["pdfPage"])
            if not drawn:
                unchecked += 1
                skipped.append("%s (page %s): plane could not be read"
                               % (item_id, item["pdfPage"]))
                continue
            agree, scale = compare(said, drawn)
            if agree:
                ok += 1
            else:
                bad += 1
                problems.append("%s: description says %s, artwork plots %s"
                                % (item_id, sorted(said), sorted(drawn)))
    print("%d figure descriptions agree with the artwork" % ok)
    print("%d disagree" % bad)
    for p in problems:
        print("   %s" % p)
    print("%d could not be checked" % unchecked)
    for s in skipped:
        print("   %s" % s)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
