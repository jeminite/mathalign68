#!/usr/bin/env python3
"""
Decode the mathematics in a released-items PDF from its vector glyph geometry.

Shared library. `tools/label_glyphs.py` builds and labels the table;
`tools/extract_items.py` uses it to decode.

WHY THIS EXISTS
Every numeral, variable and operator in the NYSED grades 3-8 released-items
PDFs is drawn as vector outlines with no text layer. The prose IS text, so a
stem extracts as a template with holes where its mathematics should be:

    'charged Nicholas a one time fee of ' ... ' to rent shoes and ' ...

The obvious fix is to render the page and read it with a vision model, but a
model reading a page can silently drop or invent a term, and there is no way to
tell from the output that it did. So instead: because each character is drawn as
a path, two instances of the same character have the SAME path geometry.
Normalise a path's points into its own bounding box, and you get a stable
fingerprint per character shape. Label each distinct shape once and the whole
document decodes deterministically -- and an unlabelled shape is a loud,
locatable failure rather than a plausible guess.

Measured on the 2026 grade 7 test: 2,001 glyph-sized paths reduce to a few dozen
distinct shapes, and the twenty most common cover more than half of all
instances.

WHY CLUSTERING IS BY DISTANCE AND NOT BY HASH
Exact hashing of rounded coordinates leaves about a quarter of fingerprints as
singletons -- sub-pixel placement differences split one shape across two keys.
On item 48 the dollar sign split in exactly that way while every digit hashed
consistently. So a fingerprint is a coarse bucket key and matching inside a
bucket is by geometric distance with a tolerance.

WHAT IT REFUSES TO DO
Guess. An unmatched shape decodes as None, the hole carries a crop path instead
of a value, and preflight blocks the deploy. A wrong number that looks right is
the only outcome worse than no number at all.
"""

import hashlib
import json
import os

try:
    import fitz
except ImportError:  # pragma: no cover
    raise SystemExit("PyMuPDF is required (poppler is not installed on this machine).")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TABLE = os.path.join(ROOT, "data", "glyphs.json")

# A glyph on an 11pt line. Anything bigger is artwork, anything smaller is a
# rule, a tick or a stray sub-pixel rectangle.
MIN_W, MAX_W = 0.5, 14.0
MIN_H, MAX_H = 0.5, 16.0

# A fraction bar is a glyph but not a letter shape, and it is as wide as
# whatever it divides. Capping every candidate at MAX_W dropped the bar over
# item 34's "-45" (about 17pt) before decoding, so three of that item's four
# choices -- which differ only by where the minus sits -- collapsed into the
# same text. Thin rules get their own, much wider allowance.
RULE_MAX_W = 90.0
RULE_MAX_H = 2.2
# A rule gets its own floor. MIN_H is 0.5pt, and the minus of a SUPERSCRIPT is
# drawn at about 70% of a full-size one: 0.48pt against 0.68pt. It failed the
# general test by two hundredths of a point and was discarded, so grade 8's
# (5^2)(7^-2)(5^4) published as (5^2)(7^2)(5^4) -- a different expression, and
# the negative exponent is the whole point of the item.
RULE_MIN_H = 0.2

# Points are normalised into the glyph's own bounding box, so distance is in
# fractions of the glyph. 0.04 is four percent of a glyph's width.
TOLERANCE = 0.04

# A horizontal rule is the same shape whether it is a minus sign, a fraction
# bar or an answer blank, so it cannot be labelled as a character. Label it
# RULE and the decoder decides from what sits above and below it -- the same
# rule RegentsAlign's build_fractions() uses, and for the same reason: without
# it every stacked pair of glyphs becomes a fraction, or every fraction becomes
# a subtraction.
RULE = "@rule"

# Characters that are SMALL AND RAISED BY DESIGN. A degree sign and a prime sit
# high and short exactly like an exponent does, so the superscript test would
# wrap them and publish 60<sup>deg</sup>F. They are already the character they
# mean; nothing goes above the line.
INTRINSICALLY_RAISED = set("\u00b0\u2032\u2033")

# Operators are centred on the maths axis, not rested on the baseline, and the
# thin ones are short. That is the same signature an exponent has, so "=" was
# swept into the superscript and 9^2 + 12^2 = 15^2 published as
# "9^2 + 12^(2 =) 15^2". An operator is never an exponent here; a superscript
# MINUS is drawn as a rule and handled before this test is reached.
CENTRED_OPERATORS = set("=+<>\u00d7\u00f7\u00b1\u2260\u2264\u2265\u2212")

# Inferring spaces from horizontal gaps works for digits and letters but not
# for narrow punctuation: a period is positioned with enough side bearing that
# the gap before it exceeds the threshold, publishing "$11 .98" and "1 .5".
# These characters never take a space before them, and these never take one
# after, regardless of the measured gap.
NO_SPACE_BEFORE = set(".,)%")
NO_SPACE_AFTER = set("($")
# An absolute-value bar is the same character opening and closing, so which
# side it hugs depends on how many have come before it. "|-5| < |-15|" needs no
# space after the opening bars and none before the closing ones, but a space on
# the outside of both -- putting "|" in either set flatly gave "| -5| < | -15|"
# or "|-5|<|-15|".
BAR = "|"

# A space never belongs inside a number. The digit 1 is narrow but advances a
# full tabular-figure width, so the measured gap after it exceeds the threshold
# and item 29's choice B published as "$1 12. 1 1" instead of "$112.11" -- the
# right digits, an unreadable number, and four choices no longer distinct.
NUMERIC = set("0123456789.,")

# decode() returns HTML (it emits <span class="frac"> for fractions), so a
# decoded character that is HTML-special has to be escaped or it corrupts the
# markup. This was not theoretical: item 21's choice B decoded correctly as
# "20x + 5 < 200" and published as "20x + 5", because the raw < opened a tag
# that swallowed the rest of the choice -- and the four choices of that item
# differ ONLY by their inequality symbol.
HTML_ESCAPE = {"<": "&lt;", ">": "&gt;", "&": "&amp;"}


def escape(label):
    return HTML_ESCAPE.get(label, label)

# Glyphs whose bounding box is tiny in one dimension carry almost no shape
# information -- a decimal point, a minus sign, a fraction bar. They are
# separated by aspect ratio and size instead, so the tolerance above does not
# collapse a period into a hyphen.
DEGENERATE_MAX = 2.5


def _points(drawing):
    pts = []
    for item in drawing["items"]:
        for value in item[1:]:
            if isinstance(value, fitz.Point):
                pts.append((value.x, value.y))
            elif isinstance(value, fitz.Rect):
                pts.extend([(value.x0, value.y0), (value.x1, value.y1)])
            elif isinstance(value, (int, float)):
                pass
    return pts


def shape_of(drawing):
    """A normalised shape descriptor, or None if this is not a glyph.

    Returns {bucket, points, width, height, items, degenerate}. `bucket` is a
    coarse hash used only to avoid comparing every shape against every other;
    equality is decided by `points` distance.
    """
    rect = drawing["rect"]
    w, h = rect.width, rect.height
    is_rule = h < RULE_MAX_H and w < RULE_MAX_W
    if not is_rule and not (MIN_W < w < MAX_W and MIN_H < h < MAX_H):
        return None
    if is_rule and not (MIN_W < w and RULE_MIN_H < h):
        return None
    pts = _points(drawing)
    if not pts:
        return None

    degenerate = w < DEGENERATE_MAX or h < DEGENERATE_MAX
    if degenerate:
        # Shape says little; size and proportion say everything.
        norm = ()
        bucket = "deg:%d:%.1f:%.1f" % (len(drawing["items"]), round(w, 1), round(h, 1))
    else:
        norm = tuple(sorted(((x - rect.x0) / w, (y - rect.y0) / h) for x, y in pts))
        # Bucket on the item count plus a very coarse point signature, so two
        # instances of one character land together even when their coordinates
        # differ in the third decimal place.
        coarse = tuple(sorted((round(a, 1), round(b, 1)) for a, b in norm))
        bucket = hashlib.md5(
            ("%d|%s" % (len(drawing["items"]), coarse)).encode()).hexdigest()[:10]

    return {
        "bucket": bucket,
        "points": norm,
        "width": round(w, 2),
        "height": round(h, 2),
        "items": len(drawing["items"]),
        "degenerate": degenerate,
    }


def _is_overbar(rect, below, glyphs):
    """Is this rule a repeating-decimal overbar rather than a minus sign?

    An overbar sits almost on top of the digits it marks and spans them. A minus
    sign in a fraction's numerator also has content below it -- the denominator,
    a whole fraction bar away -- and reading that as an overbar turned item 34's
    (-45)/9 and 45/(-9) into the same thing.
    """
    gap = min((glyphs[j][0].y0 - rect.y1) for j in below)
    if not 0 <= gap < 5.0:
        return False
    span = max(glyphs[j][0].x1 for j in below) - min(glyphs[j][0].x0 for j in below)
    if span <= 0:
        return False
    overlap = (min(rect.x1, max(glyphs[j][0].x1 for j in below))
               - max(rect.x0, min(glyphs[j][0].x0 for j in below)))
    return overlap / span > 0.6


def _distance(a, b):
    """Mean point-to-point distance between two normalised shapes, or None if
    they are not comparable."""
    if a["degenerate"] != b["degenerate"]:
        return None
    if a["degenerate"]:
        # Compare proportion and size rather than outline.
        if a["items"] != b["items"]:
            return None
        dw = abs(a["width"] - b["width"])
        dh = abs(a["height"] - b["height"])
        return (dw + dh) / 2.0 if dw < 0.8 and dh < 0.8 else None
    if len(a["points"]) != len(b["points"]):
        return None
    total = sum(abs(ax - bx) + abs(ay - by)
                for (ax, ay), (bx, by) in zip(a["points"], b["points"]))
    return total / (2.0 * len(a["points"]))


class GlyphTable:
    """Shape clusters and their labels, persisted to data/glyphs.json."""

    def __init__(self, path=TABLE):
        self.path = path
        self.clusters = []          # [{id, bucket, shape, label, count, samples}]
        self._by_bucket = {}
        if os.path.exists(path):
            self.load()

    # ------------------------------------------------------------------ io

    def load(self):
        with open(self.path) as fh:
            doc = json.load(fh)
        self.clusters = doc["clusters"]
        for c in self.clusters:
            c["shape"]["points"] = tuple(tuple(p) for p in c["shape"]["points"])
            self._by_bucket.setdefault(c["bucket"], []).append(c)

    def save(self, note=None):
        labelled = sum(1 for c in self.clusters if c["label"] is not None)
        doc = {
            "meta": {
                "generatedBy": "tools/label_glyphs.py",
                "note": note or (
                    "Vector glyph shapes from the released-items PDFs, mapped to the "
                    "characters they draw. HAND-LABELLED: a script builds the clusters, "
                    "a person (or a vision pass that is then spot-checked) supplies the "
                    "`label`. An unlabelled cluster makes its item fail to decode rather "
                    "than decode wrongly."),
                "clusters": len(self.clusters),
                "labelled": labelled,
                "instances": sum(c["count"] for c in self.clusters),
                "tolerance": TOLERANCE,
            },
            "clusters": sorted(self.clusters, key=lambda c: -c["count"]),
        }
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as fh:
            json.dump(doc, fh, indent=2)
            fh.write("\n")

    # ------------------------------------------------------------- matching

    def find(self, shape):
        """The cluster this shape belongs to, or None."""
        best, best_d = None, None
        for cand in self._by_bucket.get(shape["bucket"], []):
            d = _distance(shape, cand["shape"])
            if d is not None and d < TOLERANCE and (best_d is None or d < best_d):
                best, best_d = cand, d
        if best is not None:
            return best
        # A bucket is only a speed-up, not a guarantee: fall back to a full
        # scan so a shape whose coarse signature drifted still matches.
        for cand in self.clusters:
            d = _distance(shape, cand["shape"])
            if d is not None and d < TOLERANCE and (best_d is None or d < best_d):
                best, best_d = cand, d
        return best

    def observe(self, shape, sample):
        """Record a sighting, creating a cluster if the shape is new."""
        found = self.find(shape)
        if found is None:
            found = {
                "id": "g%03d" % (len(self.clusters) + 1),
                "bucket": shape["bucket"],
                "shape": shape,
                "label": None,
                "count": 0,
                "samples": [],
            }
            self.clusters.append(found)
            self._by_bucket.setdefault(shape["bucket"], []).append(found)
        found["count"] += 1
        if len(found["samples"]) < 4:
            found["samples"].append(sample)
        return found

    def label_of(self, shape):
        found = self.find(shape)
        return found["label"] if found else None

    # -------------------------------------------------------------- decoding

    def decode(self, drawings):
        """Drawings in reading order -> (html, unknown_count).

        Whitespace is inferred from horizontal gaps: a gap wider than a third of
        the median glyph width becomes a space, so `450x` and `450 x` stay
        distinguishable. Rules are resolved into fractions or minus signs by
        what sits above and below them.
        """
        glyphs = []
        for dr in drawings:
            shape = shape_of(dr)
            if shape is None:
                continue
            glyphs.append([dr["rect"], shape, self.label_of(shape)])
        if not glyphs:
            return "", 0

        # ---- resolve rules before anything is emitted -------------------
        consumed = set()
        fractions = {}
        overbars = {}
        for i, (rect, shape, label) in enumerate(glyphs):
            if label != RULE:
                continue
            above, below = [], []
            for j, (r2, s2, l2) in enumerate(glyphs):
                if j == i:
                    continue
                cx = (r2.x0 + r2.x1) / 2.0
                if not (rect.x0 - 1.5 <= cx <= rect.x1 + 1.5):
                    continue
                if l2 == RULE:
                    # Another rule inside this bar's span, on a different line,
                    # is a SIGN in the numerator or denominator -- item 34's
                    # four choices are -(45/9), (-45)/9, 45/(-9) and 45/9, which
                    # differ only by where the minus sits. Skipping every rule
                    # here made three of them identical.
                    if not (r2.x0 > rect.x0 - 0.5 and r2.x1 < rect.x1 + 0.5):
                        continue
                mid = (r2.y0 + r2.y1) / 2.0
                if 0 < rect.y0 - mid < 14:
                    above.append(j)
                elif 0 < mid - rect.y1 < 14:
                    below.append(j)
            if above and below:
                # A bar with content on both sides is a fraction. Either side
                # empty means it is a minus sign, an overbar or an answer blank,
                # and treating it as a fraction is how a table of cell borders
                # dissolves into nonsense.
                fractions[i] = (above, below)
                consumed.update(above)
                consumed.update(below)
            elif below and not above and _is_overbar(rect, below, glyphs):
                # Content below and nothing above, directly over the digits: a
                # repeating-decimal overbar, not a minus sign. Item 7's choices
                # are 3.3-repeating, and reading the bar as a minus published
                # "- y = x + 3.3" -- a different number, and a leading minus
                # that is not in the question at all.
                #
                # The bar is attached to the FIRST digit it covers rather than
                # emitted at its own position: its rect sits above the digit
                # line, so it forms a line of its own and sorted ahead of
                # everything, giving ".3-repeating y = x + 3".
                first = min(below, key=lambda j: glyphs[j][0].x0)
                overbars[first] = sorted(below, key=lambda j: glyphs[j][0].x0)
                consumed.add(i)
                consumed.update(j for j in below if j != first)

        # ---- reading order ----------------------------------------------
        # Lines are found by VERTICAL OVERLAP, not by y0. A period sits on the
        # baseline and a digit starts at cap height, so their y0 values differ
        # by most of a glyph: keying the sort on y0 put every decimal point and
        # every operator in a row of its own after the digits, turning $540.00
        # into "$540 00 ." and 10% into "%10". Two glyphs belong to the same
        # line when their vertical extents overlap at all.
        lines = []
        for i in sorted(range(len(glyphs)), key=lambda i: glyphs[i][0].y0):
            rect = glyphs[i][0]
            placed = False
            for line in lines:
                if rect.y0 < line["y1"] - 0.5 and rect.y1 > line["y0"] + 0.5:
                    line["y0"] = min(line["y0"], rect.y0)
                    line["y1"] = max(line["y1"], rect.y1)
                    line["idx"].append(i)
                    placed = True
                    break
            if not placed:
                lines.append({"y0": rect.y0, "y1": rect.y1, "idx": [i]})

        # ---- exponents --------------------------------------------------
        # A superscript overlaps its base vertically, so the line grouper above
        # correctly puts them on one line -- and then the emitter ran them
        # together: 9 squared came out as "92", and 9^2 + 12^2 = 15^2 as
        # "92 + 122 = 152". Four of grade 8's answer choices differed only in
        # where the exponents sat, so the reader got four identical options.
        #
        # A superscript is SHORTER than the line's body text and its foot sits
        # clearly above the body's baseline. Both tests are needed: a comma is
        # short but sits low, and a parenthesis is tall but rises high.
        # ---- exponents --------------------------------------------------
        # A superscript overlaps its base vertically, so the line grouper above
        # correctly puts them on one line -- and then the emitter ran them
        # together: 9 squared came out as "92", and 9^2 + 12^2 = 15^2 as
        # "92 + 122 = 152". Four of grade 8's answer choices differed only in
        # where the exponents sat, so the reader got four identical options.
        #
        # THE COMPARISON MUST BE WITHIN ONE RUN OF TEXT, not one "line". A
        # stacked fraction overlaps its neighbours vertically, so 4(x + 2) = 12
        # over 0.25 is all one line here, and the denominator's feet dragged the
        # baseline down until the x in (x + 2) looked raised. A fraction's
        # numerator and denominator each sit on their own baseline and are
        # measured on their own.
        supers, middots = set(), set()

        def mark(indices):
            rects = [glyphs[i][0] for i in indices]
            if len(rects) < 2:
                return
            # The baseline is the foot of the TALLEST glyphs. A median over
            # every glyph made the PARENTHESES the body in (5^2)(7^-2)(5^4) --
            # they are half again as tall as the digits -- so the digits looked
            # raised and 5^2 lost its base. The most common foot instead broke
            # 1^16, where two superscript glyphs outnumber the single base.
            # Superscripts are always drawn smaller than the text they sit on,
            # so the tallest glyphs are body text by definition.
            sized = [glyphs[i][0] for i in indices if glyphs[i][2] != RULE]
            if not sized:
                return
            max_h = max(r.height for r in sized)
            tall = sorted((r.y1, r.height) for r in sized if r.height >= 0.85 * max_h)
            baseline = tall[len(tall) // 2][0]
            body_h = sorted(h for _, h in tall)[len(tall) // 2]
            if body_h <= 0:
                return

            # A '.' SITTING ABOVE THE BASELINE IS A MULTIPLICATION DOT. The
            # shapes are identical -- a tiny filled square -- so only its height
            # on the line tells them apart, exactly as a horizontal rule is told
            # from a minus by what sits around it. Grade 8 writes 16^8 . 16^12
            # for a product, and a full stop there reads as the end of a
            # sentence in the middle of an expression.
            raised = []
            for i in indices:
                rect, _, label = glyphs[i]
                if label == "." and rect.y1 < baseline - 0.2 * body_h:
                    middots.add(i)
                    continue
                if label in INTRINSICALLY_RAISED or label in CENTRED_OPERATORS:
                    continue
                # 0.35 of the body height separates a real exponent, raised by
                # about half its own height, from an operator centred on the
                # maths axis, raised by about a quarter.
                if (rect.height < 0.78 * body_h
                        and rect.y1 < baseline - 0.35 * body_h):
                    if label == RULE:
                        raised.append(i)
                    else:
                        supers.add(i)

            # A RULE ONLY COUNTS AS AN EXPONENT'S MINUS IF IT PREFIXES ONE.
            # The geometry alone is not enough: a lowercase x has no ascender,
            # so a run of "x -" measures its body at the x-height and an
            # ordinary minus looks raised by half of it. Grade 7 already
            # publishes "x -", and it briefly became "x ^-". A negative exponent
            # is never a lone sign -- something superscript always follows it.
            by_x = sorted(indices, key=lambda j: glyphs[j][0].x0)
            for i in raised:
                at = by_x.index(i)
                if at + 1 < len(by_x) and by_x[at + 1] in supers:
                    supers.add(i)

            # If everything in the run looks raised, nothing is: the run is
            # simply set in a smaller face than the test assumed.
            if len(supers & set(indices)) == len(indices):
                supers.difference_update(indices)

        for num, den in fractions.values():
            mark(num)
            mark(den)
        for group in overbars.values():
            mark(group)
        for line in lines:
            mark([i for i in line["idx"] if i not in consumed])

        order = []
        for line in sorted(lines, key=lambda l: l["y0"]):
            order.extend(sorted(line["idx"], key=lambda i: glyphs[i][0].x0))

        widths = sorted(g[0].width for g in glyphs)
        gap_threshold = max(1.0, widths[len(widths) // 2] / 3.0)

        def text_of(indices):
            """A run of glyphs as text -- exponents included.

            A numerator is a line of its own, so it has its own baseline and its
            own exponents: grade 8 asks for 5^6 over 7^2, and without this the
            fraction published as 56 over 72, which is a different number."""
            parts, sup = [], False
            for j in sorted(indices, key=lambda j: glyphs[j][0].x0):
                lab = glyphs[j][2]
                if (j in supers) != sup:
                    parts.append("<sup>" if j in supers else "</sup>")
                    sup = j in supers
                if lab == RULE:
                    parts.append("\u2212")      # a sign inside the fraction
                elif lab is None:
                    parts.append("\ufffd")
                else:
                    parts.append(escape(lab))
            if sup:
                parts.append("</sup>")
            return "".join(parts)

        out, unknown, prev = [], 0, None
        in_sup = False
        bars_seen, prev_opening_bar = 0, False

        def close_sup():
            if out and out[-1] == "<sup>":
                out.pop()                       # nothing landed inside it
            else:
                out.append("</sup>")

        for i in order:
            rect, shape, label = glyphs[i]
            if i in consumed and i not in overbars:
                continue
            want_sup = i in supers and i not in fractions and i not in overbars
            # Close before the spacing test and open after it, so a separating
            # space lands outside the tag: "(9 + 12) <sup>2</sup>", never
            # "(9 + 12)<sup> 2</sup>".
            if in_sup and not want_sup:
                close_sup()
                in_sup = False
            if prev is not None:
                same_line = rect.y0 < prev.y1 - 0.5 and rect.y1 > prev.y0 + 0.5
                if not same_line and i not in fractions:
                    out.append(" ")
                elif same_line and rect.x0 - prev.x1 > gap_threshold:
                    last = out[-1][-1] if out and out[-1] else ""
                    numeric_run = last in NUMERIC and label in NUMERIC
                    closing_bar = label == BAR and bars_seen % 2 == 1
                    if not (numeric_run
                            or label in NO_SPACE_BEFORE or closing_bar
                            or last in NO_SPACE_AFTER or prev_opening_bar):
                        out.append(" ")
            if want_sup and not in_sup:
                # An exponent binds tight to what it sits on. The gap test uses
                # the median glyph width, and a superscript is narrower than
                # that, so (16^5)^4 came out as "(16^5) ^4".
                if out and out[-1] == " ":
                    out.pop()
                out.append("<sup>")
                in_sup = True
            if i in fractions:
                num, den = fractions[i]
                n, d = text_of(num), text_of(den)
                unknown += n.count("\ufffd") + d.count("\ufffd")
                out.append('<span class="frac"><span>%s</span><span>%s</span></span>' % (n, d))
            elif i in overbars:
                digits = text_of(overbars[i])
                unknown += digits.count("\ufffd")
                out.append('<span class="repeat">%s</span>' % digits)
            elif i in middots:
                out.append("\u00b7")            # multiplication, not a full stop
            elif label == RULE:
                out.append("\u2212")            # a bare rule is a minus sign
            elif label is None:
                out.append("\ufffd")
                unknown += 1
            else:
                out.append(escape(label))
            prev = rect
            prev_opening_bar = (label == BAR and bars_seen % 2 == 0)
            if label == BAR:
                bars_seen += 1
        if in_sup:
            close_sup()
        return "".join(out).strip(), unknown
