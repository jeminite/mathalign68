#!/usr/bin/env python3
"""
Extract the questions from one released-items PDF -- a FIRST PASS, for review.

  python3 tools/extract_items.py sources/2026-released-items-math-g7.pdf
  python3 tools/extract_items.py <pdf> --item 48        # one item, to stdout
  python3 tools/extract_items.py <pdf> --stdout

Reads  : one released-items PDF, provenance/pagemap_<testId>.json, data/glyphs.json
Writes : provenance/content_<testId>_raw.json
         assets/<TAG>/qNN[_i].png        figures
         assets/<TAG>/qNN_holeN.png      crops of anything that would not decode

NOTHING HERE IS PUBLISHABLE AS-IS. The output is a draft for a human to review
against the rendered pages; the reviewed decisions go in
provenance/merge_<testId>.json and only that reaches the site.

HOW A QUESTION IS RECOVERED
The prose is real text and extracts exactly. Only the mathematics is missing --
drawn as vector outlines with no text layer -- so a stem is a template with
holes:

    'charged Nicholas a one time fee of ' ... ' to rent shoes and ' ...

So: take the prose from the text layer, find the holes geometrically, decode
them from glyph shapes (tools/glyphs.py), and interleave the two by x position.
The prose is therefore never retyped or OCR'd, which is what makes the result
checkable: strip the decoded values back out and what remains must equal the
PDF's own text, character for character. `prose` is emitted for exactly that.

WHY OCCUPANCY IS TESTED PER CHARACTER AND NOT PER SPAN
A span's bbox can straddle a hole. PyMuPDF reports
'determine the number of games, , that Nicholas played if he spent a total of '
as ONE span whose box covers the gap where the italic x is drawn, so a
span-level test discards that variable and publishes "the number of games, ,
that" -- a sentence that still reads like a sentence. Character boxes cannot
straddle anything.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys

try:
    import fitz
except ImportError:
    sys.exit("PyMuPDF is required (poppler is not installed on this machine).")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from glyphs import GlyphTable, shape_of              # noqa: E402

PROV = os.path.join(ROOT, "provenance")
ASSETS = os.path.join(ROOT, "assets")

PROSE_FONT = "Frutiger"
LABEL_FONT = "LucidaSans"
CREDIT_RE = re.compile(r"^This question is worth (\d) credits?\.$")
# "Answer" is followed by the blank and its unit, so the line reads
# "Answer   games" rather than "Answer" -- an exact match left it in the stem,
# which then ended "...on shoes and games. Answer games".
INSTRUCTION_RE = re.compile(r"^(Show your work\.|Explain .*|Answer\b.*|Be sure to .*)$")
CHOICE_RE = re.compile(r"^[A-D]$")

# NYSED's PDFs encode the fi and fl ligatures as U+0100 and U+0101, so the text
# layer yields "ofĀce", "Ālling", "āuid", "coefĀcient", "reāection". Across all
# twelve released-items PDFs the damage is drawn from this small set, so a
# substitution table fixes it completely. Applied to the prose AND to the
# fidelity-check copy, so the two still compare equal.
LIGATURES = {
    "\u0100": "fi",     # Ā
    "\u0101": "fl",     # ā
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\u2009": "",       # thin space: kerning, not a gap
    "\u200a": "",       # hair space -- NYSED kerns "f (x)" with one, and
                         # widening it publishes "f (x)", which reads as a typo
    "\u00a0": " ",
}


def repair(text):
    for bad, good in LIGATURES.items():
        text = text.replace(bad, good)
    return text

MARGIN_X = 70.0         # prose and vector content start right of this
TOP = 55.0              # above: the running header
# The last answer choice can sit at y=701.4 -- grade 6 2023 item 3's choice D
# does -- while the lowest in-column footer across all twelve PDFs is "STOP" at
# y=702.6. A boundary at 700 silently dropped that choice and published a
# three-choice multiple-choice item. The band is widened and the footer is
# excluded by what it SAYS instead, which does not depend on a 1pt margin.
FOOT = 704.0            # below: "Page N / GO ON / STOP / Session N"
FOOTER_RE = re.compile(r"^(GO ON|STOP|Session \d+|Page \d+)\s*$")
LINE_TOL = 2.0          # chars within this y are one line
# NYSED prints the item number level with the item's SECOND line, so the anchor
# sits 5-6pt below the first line of prose (the first item on a page anchors at
# y=65.0 while its prose starts at y=59.0). Reaching back 12pt captures the
# opening line; without it every item lost its first sentence and still read
# like a sentence -- item 3 began "between the price, p," instead of "A farm
# sells blueberries by the pound to customers."
ANCHOR_LEAD = 12.0
# How far above or below its bar a fraction's content can sit. This is
# glyphs.py's own window, and it must stay the same: at 22pt the reach spanned
# the gap between two bullets, and the minus of grade 8 item 41's "C (-9,3)" was
# pulled up into "B (-3,8)".
FRACTION_REACH = 14.0
HOLE_GAP = 6.0          # vector paths closer than this are one hole
INLINE_MAX_H = 20.0     # taller than this is not inline maths
FIGURE_MIN_AREA = 2000.0
CROP_ZOOM = 3           # 3x ~ 216 dpi, so gridlines survive zooming
CROP_PAD = 8.0
HOLE_ZOOM = 8           # a hole crop is tiny; render it big for review


# ------------------------------------------------------------------ geometry

def released_items(test_id):
    path = os.path.join(PROV, "pagemap_%s.json" % test_id)
    if not os.path.exists(path):
        sys.exit("missing %s -- run tools/build_pagemap.py first"
                 % os.path.relpath(path, ROOT))
    recs = json.load(open(path))["items"]
    return {int(k): v["pdfPage"] for k, v in recs.items()}


def anchors_on(page, wanted):
    """(item number, y) for every item number printed in this page's margin."""
    found = []
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        t = text.strip()
        if t.isdigit() and x0 < MARGIN_X and TOP < y0 < FOOT and int(t) in wanted:
            found.append((int(t), y0))
    return sorted(found, key=lambda a: a[1])


def chars_in(page, y_lo, y_hi):
    """[(bbox, char, line_y, font)] for prose, whitespace kept.

    Whitespace is kept deliberately: dropping it and rejoining the characters
    produced "Thisquestionisworth3credits."
    """
    out = []
    for blk in page.get_text("rawdict")["blocks"]:
        for line in blk.get("lines", []):
            for sp in line["spans"]:
                if PROSE_FONT not in sp["font"]:
                    continue
                ly = round(sp["bbox"][1], 1)
                for ch in sp.get("chars", []):
                    if y_lo <= ch["bbox"][1] < y_hi and ch["bbox"][0] > MARGIN_X - 20:
                        out.append((ch["bbox"], ch["c"], ly, sp["font"]))
    return out


def labels_in(page, y_lo, y_hi):
    """Answer-choice letters: (letter, x, y)."""
    out = []
    for blk in page.get_text("dict")["blocks"]:
        for line in blk.get("lines", []):
            for sp in line["spans"]:
                t = sp["text"].strip()
                if LABEL_FONT in sp["font"] and CHOICE_RE.match(t) \
                        and y_lo <= sp["bbox"][1] < y_hi:
                    out.append((t, sp["bbox"][0], sp["bbox"][1]))
    return sorted(out, key=lambda c: (c[2], c[1]))


def group_x(drawings, gap=HOLE_GAP):
    """Adjacent drawings on one line collapse into one hole."""
    groups = []
    for dr in sorted(drawings, key=lambda dr: dr["rect"].x0):
        if groups and dr["rect"].x0 - groups[-1][-1]["rect"].x1 < gap:
            groups[-1].append(dr)
        else:
            groups.append([dr])
    return groups


def bbox_of(group):
    r = fitz.Rect(group[0]["rect"])
    for dr in group[1:]:
        r = r | dr["rect"]
    return r


# ------------------------------------------------------------------ the item

def extract_item(page, number, y_lo, y_hi, table, tag, adir, meta):
    chars = chars_in(page, y_lo, y_hi)
    labels = labels_in(page, y_lo, y_hi)
    # ONE call. page.get_drawings() builds fresh dicts on every call, so calling
    # it twice and tracking consumption by id() never matches: every glyph
    # already used as an inline hole reappeared as leftover artwork, which is
    # how 42 items produced 173 phantom "displayed expressions".
    # The LAST item on a page may have maths hanging below the text bound. Grade
    # 6 2023 item 3's choice D is drawn at y=704 to 713 where the bound is 704,
    # so the choice was found but came out empty and the item published with
    # three options. The footer is text, never vector art, so the drawing bound
    # can reach past it -- but only for the last item on the page, or this would
    # pull the next item's first line up into this one.
    draw_hi = y_hi + 14.0 if y_hi >= FOOT else y_hi
    drawings = [dr for dr in page.get_drawings()
                if y_lo - 2 <= dr["rect"].y0 < draw_hi and dr["rect"].x0 > MARGIN_X - 25]
    glyph_draws = [dr for dr in drawings
                   if dr["rect"].x0 > MARGIN_X - 20 and shape_of(dr) is not None]
    all_draws = drawings

    # Candidate figure regions, computed BEFORE inline holes so a figure's own
    # labels cannot be mistaken for maths in the stem. Item 27's graph has a `y`
    # axis label that happens to sit level with a line of prose, and without
    # this it was published inside the sentence: "made from x apples. y".
    # RegentsAlign solves the same problem with furniture() and the
    # shares_line_with_prose flag.
    figure_zones = []
    dense = [dr for dr in all_draws if not is_furniture(dr, all_draws)]
    for blk in block_rows(dense, gap=14.0):
        r = bbox_of(blk)
        # A figure zone must contain STRUCTURE, not just many glyphs: axis
        # lines, table borders, plot marks -- paths that are not letter shapes.
        #
        # Counting paths alone was wrong and cost nine items their maths. An
        # item with three money values spread over three lines of prose has ~17
        # glyph paths within 14pt of each other, so it looked exactly as dense
        # as a table, the whole stem became a "figure zone", every inline hole
        # inside it was skipped, and the stem published as "a one time fee of
        # to rent shoes and  for each game". Worse, the prose-fidelity check
        # still passed: it proves nothing was invented, not that nothing was
        # lost.
        # A FRACTION BAR is type, not structure. It is a thin horizontal wider
        # than the glyph limit, so counting every non-glyph path as structure
        # turned clean displayed expressions into images: item 20's
        # "4(x + 2) = 12/-0.25" and item 47's "(1/2)(-0.4) / (1/3)" both
        # decoded perfectly and were published as pictures. A table border runs
        # the width of the table; a fraction bar spans one expression.
        structure = sum(1 for dr in blk
                        if shape_of(dr) is None
                        and not (dr["rect"].height < 2.0 and dr["rect"].width < 40))
        if structure >= 2 and len(blk) >= 6 and r.width * r.height >= FIGURE_MIN_AREA:
            figure_zones.append(r)

    def in_figure(rect):
        cx, cy = (rect.x0 + rect.x1) / 2.0, (rect.y0 + rect.y1) / 2.0
        return any(z.x0 - 4 <= cx <= z.x1 + 4 and z.y0 - 4 <= cy <= z.y1 + 4
                   for z in figure_zones)

    # LINE_TOL EXISTS FOR THIS, and was not being applied. A line's key is the
    # top of its text span rounded to a tenth of a point, and a span set in a
    # different face sits a hair off its neighbours: the italic c in grade 6
    # item 41's "how many baseball cards, c, Dan has" is at y=109.3 where the
    # prose either side of it is at 109.2. An exact key made it a line of its
    # own, and it was published at the END of the stem -- "baseball cards, ,
    # Dan has. c" -- which reads as a typo rather than as a missing variable.
    lines = {}
    for bbox, ch, ly, font in chars:
        key = next((k for k in lines if abs(k - ly) <= LINE_TOL), ly)
        lines.setdefault(key, []).append((bbox, ch, font))

    consumed, unresolved = set(), []
    choice_extra = {}
    rendered_lines = []

    # How wide this item's prose actually runs, used as the right bound for a
    # line that carries no text of its own.
    column_x1 = max([b[2] for row in lines.values() for b, c, _ in row if c.strip()]
                    or [MARGIN_X + 400.0])

    for ly in sorted(lines):
        row = sorted(lines[ly], key=lambda t: t[0][0])
        # WHITESPACE DOES NOT OCCUPY THE LINE. Where maths was lifted out of a
        # sentence the text layer leaves a space, and that space's box is as
        # wide as the value that is missing -- so treating it as occupied hid
        # the very glyph that belongs there. Grade 8 item 31 published "line a
        # is parallel to line , and lines q and t", and grade 7 item 27 lost the
        # y in "the amount of juice, y, that can be made" and had been carrying
        # it as a known gap since launch. The other three variables on item 31's
        # line fell in gaps BETWEEN spans and were found all along, which is
        # what made the one missing letter look arbitrary.
        occupied = [(b[0], b[2]) for b, c, _ in row if c.strip()]
        band = [dr for dr in glyph_draws
                if dr["rect"].y0 < ly + 11 and dr["rect"].y1 > ly - LINE_TOL]
        # Only the RIGHT edge needs bounding. A graph's axis label can share a
        # prose line's y-band while sitting far out to the right of the text
        # column, and item 27 published its y-axis label inside the sentence:
        # "made from x apples. y".
        #
        # The left edge must NOT be bounded by the line's first character: a
        # value that wraps to the start of the next line sits to the LEFT of
        # that line's text. Constraining both sides cost item 48 its $3.75 --
        # which is the very hole that first showed this approach works.
        # The right bound must come from REAL TEXT, not from whitespace. Each
        # bullet of item 41's vertex list -- "A (6, -4)" -- is drawn entirely as
        # artwork, and its whole text layer is one space character at x=130. The
        # bound was therefore x=143, which cut each bullet in half: "A (6," was
        # pulled into the sentence and "-4)" was left behind to be published as
        # a stray displayed expression, so the stem read "A (6, . B (- . C (-".
        # A line with no real text has no sentence to protect, so the bound
        # falls back to the width of the item's own text column.
        line_x1 = max(hi for lo, hi in occupied) if occupied else column_x1
        # A GLYPH WITH PROSE ON BOTH SIDES OF IT IS PART OF THE SENTENCE, even
        # when it falls inside a figure's bounding box. A variable set in the
        # middle of a line -- "line a is parallel to line b", "represents y as a
        # linear function of x" -- is drawn as artwork like any other maths, and
        # the figure-zone exclusion was swallowing it, so those sentences
        # published with a hole in them. An axis label sitting in the same
        # y-band has prose only to its left, which is what keeps it out.
        def bracketed(r):
            return (any(hi <= r.x0 + 0.4 for lo, hi in occupied)
                    and any(lo >= r.x1 - 0.4 for lo, hi in occupied))

        free = [dr for dr in band
                if not any(dr["rect"].x0 < hi - 0.4 and dr["rect"].x1 > lo + 0.4
                           for lo, hi in occupied)
                and MARGIN_X - 6 <= dr["rect"].x0 <= line_x1 + 12
                and (not in_figure(dr["rect"]) or bracketed(dr["rect"]))]

        # A STACKED FRACTION CAN BE TALLER THAN THE LINE BAND, and one with
        # exponents is taller still: grade 8's 12^20 over 12^4 spans 28pt where
        # the band allows about 15. The numerator's exponent and the
        # denominator's base fell outside it, so the fraction decoded as 12 over
        # 4 -- a different number -- and the two missing pieces were published
        # as stray expressions beside it. Whatever completes a bar already in
        # the band is pulled in, however far above or below it sits.
        # GROW EACH ACCEPTED RUN RIGHTWARDS. The bound above is deliberately
        # tight, because a graph's axis label can share a prose line's y-band
        # from far out in the margin -- items 27 and 33 gain a stray "y" and "p"
        # the moment it is relaxed. But a tight bound also cuts a value in half:
        # item 43's price list published "$1" where the page says "$12.50",
        # leaving "2.50" to be shown as a stray expression beside it.
        #
        # Adjacency separates the two. A digit that continues a value sits hard
        # against the run already accepted; an axis label sits alone in white
        # space. So the bound decides what may START a run, and anything
        # touching that run joins it however far right it reaches.
        in_free = {id(dr) for dr in free}
        growing = True
        while growing:
            growing = False
            for dr in band:
                if id(dr) in in_free or id(dr) in consumed or in_figure(dr["rect"]):
                    continue
                r = dr["rect"]
                for other in free:
                    o = other["rect"]
                    if (r.y0 < o.y1 and r.y1 > o.y0
                            and -1.0 <= r.x0 - o.x1 <= 6.0):
                        free.append(dr)
                        in_free.add(id(dr))
                        growing = True
                        break

        # A BAR IS A RULE WITH CONTENT ON BOTH SIDES OF IT. Testing only "thin
        # and not too wide" also matched every decimal point and every minus
        # sign, and then this pulled a neighbour in through them: $5.00 gained a
        # stray 0, $176.32 a stray full stop, and -45 over 9 became -45 over -9,
        # which is a different number. That both-sides test is the same one
        # glyphs.py uses to tell a fraction from a minus.
        def is_bar(r):
            if not (r.height < 2.2 and 3.0 < r.width < 90):
                return False
            above = below = False
            for other in glyph_draws:
                o = other["rect"]
                if o is r:
                    continue
                cx, cy = (o.x0 + o.x1) / 2.0, (o.y0 + o.y1) / 2.0
                if not (r.x0 - 1.5 <= cx <= r.x1 + 1.5):
                    continue
                if 0 < r.y0 - cy < FRACTION_REACH:
                    above = True
                elif 0 < cy - r.y1 < FRACTION_REACH:
                    below = True
            return above and below

        bars = [dr["rect"] for dr in free if is_bar(dr["rect"])]
        for dr in glyph_draws:
            if id(dr) in in_free or id(dr) in consumed or in_figure(dr["rect"]):
                continue
            r = dr["rect"]
            cx, cy = (r.x0 + r.x1) / 2.0, (r.y0 + r.y1) / 2.0
            for bar in bars:
                if (bar.x0 - 1.5 <= cx <= bar.x1 + 1.5
                        and abs(cy - (bar.y0 + bar.y1) / 2.0) < FRACTION_REACH):
                    free.append(dr)
                    in_free.add(id(dr))
                    break

        pieces = [(b[0], c) for b, c, f in row]

        for grp in group_x(free):
            r = bbox_of(grp)
            if r.height >= INLINE_MAX_H:
                # A stacked fraction is taller than a line of type, so it lands
                # here. Skipping it SILENTLY DROPPED content: item 25 published
                # "He spends  of his money" and item 40 "buys 3 pounds of
                # grapes,  pound of turkey" -- sentences that still read as
                # sentences, which is the one failure this whole approach is
                # meant to make impossible. Anything too tall for inline is
                # recorded, never discarded.
                text, unknown = table.decode(grp)
                if unknown:
                    name = "q%02d_tall%d.png" % (number, len(unresolved) + 1)
                    save_crop(page, r, os.path.join(adir, name), HOLE_ZOOM, pad=2)
                    unresolved.append({
                        "kind": "maths too tall for one line, and it would not decode",
                        "rect": [round(v, 2) for v in (r.x0, r.y0, r.x1, r.y1)],
                        "partial": text,
                        "crop": "%s/%s" % (tag, name),
                    })
                    pieces.append((r.x0, "⟦?⟧"))
                else:
                    pieces.append((r.x0, '<span class="math">%s</span>' % text))
                for dr in grp:
                    consumed.add(id(dr))
                continue
            text, unknown = table.decode(grp)
            for dr in grp:
                consumed.add(id(dr))
            if unknown:
                name = "q%02d_hole%d.png" % (number, len(unresolved) + 1)
                save_crop(page, r, os.path.join(adir, name), HOLE_ZOOM, pad=1.5)
                unresolved.append({
                    "kind": "inline maths that would not decode",
                    "rect": [round(v, 2) for v in (r.x0, r.y0, r.x1, r.y1)],
                    "partial": text,
                    "crop": "%s/%s" % (tag, name),
                })
                pieces.append((r.x0, "⟦?⟧"))
            else:
                pieces.append((r.x0, '<span class="math">%s</span>' % text))

        pieces.sort(key=lambda p: p[0])
        # The PDF's prose has no spaces where the maths was lifted out -- the
        # text layer literally reads "Ms. Morgan earnsper hour" -- so inserting
        # a value between two word characters needs a space on each side, or the
        # published sentence reads "earns$15.50per hour".
        spaced = []
        for idx, (px, text) in enumerate(pieces):
            is_math = text.startswith("<span") or text == "⟦?⟧"
            if is_math:
                prev = spaced[-1] if spaced else ""
                if prev and not prev[-1].isspace():
                    spaced.append(" ")
                spaced.append(text)
                nxt = pieces[idx + 1][1] if idx + 1 < len(pieces) else ""
                if nxt and not nxt[0].isspace() and nxt not in ".,;:?!)":
                    spaced.append(" ")
            else:
                spaced.append(text)
        rendered_lines.append({
            "y": ly,
            "font": row[0][2],
            "html": repair("".join(spaced)).strip(),
            "prose": repair("".join(c for _, c, _ in row)).strip(),
        })

    # ---- classify the lines -------------------------------------------
    credit_line, stem, instructions, choice_lines = None, [], [], {}

    for ln in rendered_lines:
        text = ln["prose"]
        m = CREDIT_RE.match(text)
        if m:
            credit_line = text
            continue
        if FOOTER_RE.match(text):
            continue
        if INSTRUCTION_RE.match(text):
            instructions.append(text)
            continue
        # A choice can run to several lines, and its LETTER IS VERTICALLY
        # CENTRED on them: item 18's label A sits at y=338.6 between its own
        # lines at 329.7 and 344.0. So neither "within a few points of a label"
        # (which kept one line per choice and dropped the rest) nor "the nearest
        # label at or above" (which shifted every choice by one line) is right.
        # The line belongs to the nearest label in either direction, and a line
        # further off than one choice's height belongs to the stem.
        if labels:
            nearest = min(range(len(labels)),
                          key=lambda ci: abs(ln["y"] - labels[ci][2]))
            if abs(ln["y"] - labels[nearest][2]) < 20:
                choice_lines.setdefault(nearest, []).append(ln["html"])
                continue
        stem.append(ln)

    choices = []
    for ci, (letter, lx, ly) in enumerate(labels):
        choices.append({"label": letter,
                        "html": " ".join(choice_lines.get(ci, [])).strip(),
                        "x": round(lx, 1), "y": round(ly, 1), "_ci": ci})

    # ---- whatever vector content is left is display maths or a figure --
    leftover = [dr for dr in all_draws
                if id(dr) not in consumed and not is_furniture(dr, all_draws)]
    blocks = block_rows(leftover)

    # A block sitting level with an answer-choice letter and to its right is
    # that choice's content, not a displayed expression. Most choices on these
    # tests ARE bare maths -- "10%", "$4.48", an expression -- so without this
    # every numeric choice was reported as a stray display expression and the
    # choice itself came out empty.
    figures, display = [], []
    remaining = []
    for blk in blocks:
        r = bbox_of(blk)
        owner = None
        for ci, (letter, lx, ly) in enumerate(labels):
            if abs(r.y0 - ly) < 9 and r.x0 > lx:
                owner = ci
                break
        if owner is not None and r.height < 34:
            text, unknown = table.decode(blk)
            piece = ('⟦?⟧' if unknown
                     else '<span class="math">%s</span>' % text)
            choice_extra.setdefault(owner, []).append((r.x0, piece))
            if unknown:
                name = "q%02d_choice%s.png" % (number, labels[owner][0])
                save_crop(page, r, os.path.join(adir, name), HOLE_ZOOM, pad=2)
                unresolved.append({
                    "kind": "answer choice %s would not decode" % labels[owner][0],
                    "rect": [round(v, 2) for v in (r.x0, r.y0, r.x1, r.y1)],
                    "partial": text,
                    "crop": "%s/%s" % (tag, name),
                })
            continue
        remaining.append(blk)

    # Decode first, then classify on the result. A block that decodes cleanly
    # and fits in a couple of lines is a displayed expression; ANYTHING that
    # does not decode cleanly is artwork.
    #
    # Deciding on shape alone did not work. A single row of a data table is the
    # same height and width as a displayed expression, so a geometric test
    # classified table rows as maths and then reported their letters -- E, A, S,
    # R, C, table headers -- as undecodable maths. 59 glyph clusters were
    # blocking 74 "expressions" that were really parts of six tables.
    #
    # Failing towards "figure" is the safe direction: a figure published as a
    # figure is merely unhelpful, while artwork published as text is wrong.
    figure_blocks = []
    for blk in remaining:
        r = bbox_of(blk)
        glyphs = [dr for dr in blk if shape_of(dr) is not None]
        # A row of numbers inside a data table decodes perfectly cleanly, so
        # "decodes cleanly" alone promoted table rows to displayed expressions
        # while their header rows stayed in the figure. Anything inside a figure
        # zone belongs to the figure.
        if in_figure(r):
            figure_blocks.append(blk)
            continue
        # One glyph on its own is a label, not an expression -- the y and x on
        # a graph's axes were being published as displayed maths.
        if (r.height < 34 and r.width < 380 and glyphs
                and len(glyphs) == len(blk) and len(glyphs) >= 2):
            text, unknown = table.decode(blk)
            if not unknown:
                display.append({
                    "rect": [round(v, 2) for v in (r.x0, r.y0, r.x1, r.y1)],
                    "html": '<span class="math">%s</span>' % text,
                })
                continue
        figure_blocks.append(blk)

    # Table rows arrive as separate blocks. Merge blocks that overlap
    # horizontally and sit within 30pt vertically, so one table becomes one
    # figure instead of one per row.
    merged = []
    for blk in sorted(figure_blocks, key=lambda b: bbox_of(b).y0):
        r = bbox_of(blk)
        joined = False
        for group in merged:
            gr = bbox_of(group)
            if r.y0 - gr.y1 < 30 and r.x1 > gr.x0 - 20 and r.x0 < gr.x1 + 20:
                group.extend(blk)
                joined = True
                break
        if not joined:
            merged.append(list(blk))

    for i, blk in enumerate(merged, 1):
        r = bbox_of(blk)
        if r.width * r.height < FIGURE_MIN_AREA:
            continue
        glyphs = [dr for dr in blk if shape_of(dr) is not None]
        grown = grow_for_labels(r, page, y_lo, y_hi)
        name = ("q%02d.png" % number if len(merged) == 1
                else "q%02d_%d.png" % (number, i))
        if not save_crop(page, grown, os.path.join(adir, name), CROP_ZOOM, pad=CROP_PAD):
            continue
        decoded, unknown = table.decode(glyphs) if glyphs else ("", 0)
        figures.append({
            "file": "%s/%s" % (tag, name),
            "rect": [round(v, 2) for v in (grown.x0, grown.y0, grown.x1, grown.y1)],
            "paths": len(blk),
            "decodedLabels": decoded[:400],
            "undecodedGlyphs": unknown,
            "alt": "",
            "longDescription": "",
        })

    # Fold each choice's decoded maths in at the right x position.
    for c in choices:
        extra = sorted(choice_extra.get(c.pop("_ci"), []))
        if extra:
            c["html"] = (c["html"] + " " + " ".join(t for _, t in extra)).strip()

    stem_html = " ".join(ln["html"] for ln in stem).strip()
    # The PDF's own prose for exactly the lines the stem is built from. The
    # fidelity check compares the published stem against this, so it must not
    # include the credit line, the instructions or the answer choices -- the
    # stem legitimately excludes those, and including them made three correct
    # items look like failures.
    stem_prose = " ".join(ln["prose"] for ln in stem).strip()
    prose_all = " ".join(ln["prose"] for ln in rendered_lines).strip()

    return {
        "item": number,
        "page": page.number + 1,
        "type": meta.get("type"),
        "credits": meta.get("credits"),
        "session": meta.get("session"),
        "creditLine": credit_line,
        "stemHtml": stem_html,
        "stemLines": [ln["html"] for ln in stem],
        "prose": stem_prose,
        "proseAllLines": prose_all,
        "instructions": instructions,
        "choices": choices,
        "choicesInImage": bool(labels) and all(not c["html"] for c in choices),
        "display": display,
        "figures": figures,
        "unresolved": unresolved,
    }


def is_furniture(dr, siblings):
    """Page furniture that must never become a figure.

    Two shapes matter here, each of which produced a phantom figure on every
    item before it was excluded:

    The ITEM FRAME -- a single-path rectangle enclosing the whole question.
    RegentsAlign excludes the equivalent with `width > 480 and height > 500`,
    but this one is 468 x 624, so an absolute threshold tuned to another
    document misses it. A single path that large is always a frame; a real
    figure that size is built from many paths.

    ANSWER BLANKS AND RULES -- a lone thin horizontal. A rule sits by itself; a
    dot-plot axis has ticks and dots on it, so company within 30pt vertically is
    what separates the two. That distinction is RegentsAlign's, and without it a
    dot plot is either dropped entirely or the answer blank becomes artwork.
    """
    r = dr["rect"]
    if len(dr["items"]) == 1 and r.width > 300 and r.height > 100:
        return True
    if r.height < 1.5 and r.width > 40:
        company = sum(1 for o in siblings
                      if o is not dr
                      and abs(o["rect"].y0 - r.y0) < 30
                      and o["rect"].x1 > r.x0 and o["rect"].x0 < r.x1)
        if company < 4:
            return True
    return False


def block_rows(drawings, gap=10.0):
    """Group leftover drawings into vertical blocks separated by clear gaps."""
    if not drawings:
        return []
    ordered = sorted(drawings, key=lambda dr: dr["rect"].y0)
    blocks, current, last = [], [ordered[0]], ordered[0]["rect"].y1
    for dr in ordered[1:]:
        if dr["rect"].y0 - last > gap:
            blocks.append(current)
            current = []
        current.append(dr)
        last = max(last, dr["rect"].y1)
    blocks.append(current)
    return blocks


def grow_for_labels(rect, page, y_lo, y_hi):
    """Extend a figure's crop to enclose the text that belongs to it.

    Transplanted from RegentsAlign, where it exists because cropping to the
    artwork alone slices axis titles and tick labels in half -- they are
    stripped from the stem AND missing from the picture. Anything short sitting
    just outside the artwork is a label, not prose; the asymmetric vertical
    margin is because a caption sits below while the equation being graphed
    sits above.
    """
    grown = fitz.Rect(rect)
    for blk in page.get_text("dict")["blocks"]:
        for line in blk.get("lines", []):
            for sp in line["spans"]:
                b = sp["bbox"]
                if not (y_lo <= b[1] < y_hi):
                    continue
                if len(sp["text"].strip()) > 12:
                    continue                      # prose, not a label
                if b[0] < MARGIN_X:
                    continue                      # the item number in the margin
                cx = (b[0] + b[2]) / 2.0
                if rect.x0 - 40 <= cx <= rect.x1 + 40 and \
                   rect.y0 - 14 <= b[1] <= rect.y1 + 34:
                    grown = grown | fitz.Rect(b)
    return grown


def save_crop(page, rect, path, zoom, pad=CROP_PAD):
    """Write the crop. Returns False if it is blank, having written nothing."""
    clip = fitz.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad)
    clip = clip & page.rect
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    # A PICTURE OF NOTHING IS NOT A FIGURE. Grade 8 2023 item 3 has a single
    # 61 x 294pt path hard against the right margin that renders entirely white;
    # it is too narrow for the frame test in is_furniture, so it became a
    # figure, and the item published a blank image beside a question that
    # refers to no picture at all.
    if not any(b != 255 for b in pix.samples):
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pix.save(path)
    return True


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="First-pass question extraction.")
    ap.add_argument("pdf")
    ap.add_argument("--item", type=int, help="only this item, printed to stdout")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    base = os.path.basename(args.pdf)
    grade = int(re.search(r"-g(\d)\b", base).group(1))
    year = int(re.match(r"(\d{4})", base).group(1))
    test_id = "g%d-%d" % (grade, year)
    tag = "G%d-%d" % (grade, year)
    adir = os.path.join(ASSETS, tag)

    item_map = json.load(open(os.path.join(PROV, "itemmap_%s.json" % test_id)))
    meta_by_item = {i["item"]: i for i in item_map["items"]}
    pages_by_item = released_items(test_id)
    wanted = set(pages_by_item)

    table = GlyphTable()
    if not any(c["label"] for c in table.clusters):
        sys.exit("data/glyphs.json has no labels -- run tools/label_glyphs.py first")

    # Clear this test's crops first. Re-running the extractor after a fix
    # otherwise leaves the superseded ones behind -- one run left 200 files for
    # 16 figures -- and a stale crop that still matches a filename is worse than
    # a missing one, because it looks current.
    if not (args.item or args.stdout) and os.path.isdir(adir):
        shutil.rmtree(adir)

    doc = fitz.open(args.pdf)
    by_page = {}
    for item, pno in pages_by_item.items():
        by_page.setdefault(pno, []).append(item)

    items = []
    for pno in sorted(by_page):
        page = doc[pno - 1]
        anchors = anchors_on(page, wanted)
        for idx, (number, ay) in enumerate(anchors):
            if args.item and number != args.item:
                continue
            y_lo = ay - ANCHOR_LEAD
            y_hi = (anchors[idx + 1][1] - ANCHOR_LEAD
                    if idx + 1 < len(anchors) else FOOT)
            items.append(extract_item(page, number, y_lo, y_hi, table, tag, adir,
                                      meta_by_item.get(number, {})))

    payload = {
        "meta": {
            "schemaVersion": "1.0",
            "generatedBy": "tools/extract_items.py",
            "generated": datetime.date.today().isoformat(),
            "testId": test_id,
            "source": os.path.relpath(os.path.abspath(args.pdf), ROOT),
            "assetDir": tag,
            "status": "FIRST PASS -- review against the rendered pages before merging. "
                      "Nothing here is publishable until it is in "
                      "provenance/merge_%s.json." % test_id,
            "items": len(items),
            "itemsWithUnresolved": sum(1 for i in items if i["unresolved"]),
            "figures": sum(len(i["figures"]) for i in items),
            "displayExpressions": sum(len(i["display"]) for i in items),
        },
        "items": items,
    }

    if args.item or args.stdout:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return

    out = os.path.join(PROV, "content_%s_raw.json" % test_id)
    with open(out, "w") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    m = payload["meta"]
    print("%-46s -> %s" % (base, os.path.relpath(out, ROOT)))
    print("   %d items, %d figures, %d displayed expressions"
          % (m["items"], m["figures"], m["displayExpressions"]))
    print("   %d item(s) have something that would not decode" % m["itemsWithUnresolved"])
    for i in items:
        for u in i["unresolved"]:
            print("     q%-3d %s -> %s" % (i["item"], u["kind"], u["crop"]))
    print("\n   FIRST PASS ONLY -- review against the rendered pages before merging.")


if __name__ == "__main__":
    main()
