#!/usr/bin/env python3
"""Build data/im_ms_pacing.json -- days per unit, optional lessons, mid-unit
assessments -- from the 35-week pacing table in the Teacher Course Guides.

WHY THIS IS VERIFIABLE IN A WAY MOST PDF EXTRACTION IS NOT
The table covers all three grades side by side, and each of the three guides
prints the WHOLE table. So grade 7's pacing can be read from the grade 6 guide,
the grade 7 guide and the grade 8 guide independently, and the three readings
must be identical. That is a genuine triple check on the parse, not a
restatement of it: three separate PDFs, three separate page layouts, one answer.
The build fails if they disagree.

THE LAYOUT
Three columns, headed "Grade 6" / "Grade 7" / "Grade 8", with 35 "week N"
labels down the left margin. Each unit is a block of lines in one column:

    Unit 1
    Area and Surface Area          <- title, wraps over up to two lines
    (20-22 days) (MA)              <- day range; (MA) = has a Mid-Unit Assessment
    Optional Lessons: 16, 19       <- or "none", or "all"

Reading order does not follow the columns, so the columns are separated by x
and the lines within each ordered by y -- the same approach the Scope and
Sequence boxes needed.

"Unit" IS ALSO A WORD IN A TITLE. Grade 6 Unit 3 is "Unit Rates and
Percentages", so a block boundary is a line that is EXACTLY "Unit <n>", never a
line that merely starts with the token.
"""

import argparse
import datetime
import json
import os
import re
import sys
from collections import defaultdict

import fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "sources")
GUIDE = "ImagineIM_NY_%d__TCG_NA_V2_EN_DIG.pdf"
OUT = os.path.join(ROOT, "data", "im_ms_pacing.json")
REF = os.path.join(ROOT, "data", "im_ms_reference.json")

GRADES = (6, 7, 8)
EXPECTED_WEEKS = 35
EXPECTED_UNITS = 9

UNIT_LINE = re.compile(r"^Unit (\d)$")
# En dash in the source, and a lone number for a fixed-length unit.
DAYS_LINE = re.compile(r"^\((\d+)(?:[–—-](\d+))?\s*days?\)\s*(\(MA\))?\s*$")
OPTIONAL_LINE = re.compile(r"^Optional Lessons?:\s*(.+?)\s*$")
LEGEND = "(MA) = Unit"


def page_lines(page, band, y_lo, y_hi):
    """Lines of one column, as (y, text), ordered down the page."""
    lo, hi = band
    rows = defaultdict(list)
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        if lo <= x0 < hi and y_lo < y0 < y_hi:
            rows[round(y0, 1)].append((x0, text))
    return [(y, " ".join(t for _, t in sorted(rows[y]))) for y in sorted(rows)]


def find_pacing_page(doc):
    for i, page in enumerate(doc):
        text = page.get_text()
        if "week 1" in text and LEGEND in text:
            return i
    return None


def table_geometry(page):
    """Column bands from the three grade headings, week rows from the margin."""
    heads = {}
    words = page.get_text("words")
    for i, w in enumerate(words):
        if w[4] == "Grade" and i + 1 < len(words):
            nxt = words[i + 1]
            if nxt[4] in ("6", "7", "8") and abs(nxt[1] - w[1]) < 2.0:
                heads.setdefault(int(nxt[4]), []).append((w[1], w[0]))
    if sorted(heads) != list(GRADES):
        return None
    # The running footer repeats "Grade N"; the table heading is the one all
    # three share a y with.
    ys = defaultdict(list)
    for g, hits in heads.items():
        for y, x in hits:
            ys[round(y, 0)].append((g, x))
    row = [v for v in ys.values() if len(v) == 3]
    if not row:
        return None
    xs = dict(sorted(row[0]))
    header_y = [k for k, v in ys.items() if len(v) == 3][0]

    weeks = sorted(y for x0, y, x1, y1, t, *_ in page.get_text("words")
                   if t == "week" and x0 < xs[6] - 20.0 and y > header_y)
    if len(weeks) != EXPECTED_WEEKS:
        return None

    edges = sorted(xs.values())
    bands = {}
    for g in GRADES:
        left = xs[g] - 8.0
        after = [e for e in edges if e > xs[g]]
        bands[g] = (left, (after[0] - 8.0) if after else 10_000.0)
    return {"bands": bands, "weeks": weeks, "headerY": header_y}


def parse_optional(text):
    """'16, 19' -> [16, 19]; 'none' -> []; 'all' -> the string 'all'."""
    body = text.strip().rstrip(".")
    if body.lower() == "none":
        return []
    if body.lower() == "all":
        return "all"
    nums = [int(n) for n in re.findall(r"\d+", body)]
    if not nums:
        sys.exit("pacing: unreadable optional-lesson list %r" % text)
    return nums


def parse_column(lines, weeks, grade):
    """One grade's column -> {unit number: {...}}."""
    blocks, current = [], None
    for y, text in lines:
        m = UNIT_LINE.match(text)
        if m:
            current = {"unit": int(m.group(1)), "y": y, "lines": []}
            blocks.append(current)
        elif current is not None:
            current["lines"].append(text)

    units = {}
    for block in blocks:
        title_parts, days, ma, optional = [], None, False, None
        for text in block["lines"]:
            dm = DAYS_LINE.match(text)
            if dm:
                lo = int(dm.group(1))
                days = [lo, int(dm.group(2)) if dm.group(2) else lo]
                ma = bool(dm.group(3))
                continue
            om = OPTIONAL_LINE.match(text)
            if om:
                optional = parse_optional(om.group(1))
                continue
            if days is None:
                title_parts.append(text)
        if days is None or optional is None:
            sys.exit("pacing: grade %d unit %d is missing its day range or "
                     "optional-lesson line: %r" % (grade, block["unit"], block["lines"]))
        # A wrapped title's halves join with a single space; the guide prints a
        # trailing period on one of them (grade 7 Unit 8) which is not part of
        # the title anywhere else it appears.
        title = " ".join(" ".join(title_parts).split()).rstrip(".")
        start = min(range(len(weeks)), key=lambda i: abs(weeks[i] - block["y"])) + 1
        units[block["unit"]] = {
            "title": title,
            "days": days,
            "midUnitAssessment": ma,
            "optionalLessons": optional,
            "startWeek": start,
        }
    return units


def parse_guide(grade_of_guide):
    path = os.path.join(SOURCES, GUIDE % grade_of_guide)
    if not os.path.exists(path):
        sys.exit("missing %s" % os.path.relpath(path, ROOT))
    doc = fitz.open(path)
    pno = find_pacing_page(doc)
    if pno is None:
        sys.exit("grade %d guide: no pacing page found" % grade_of_guide)
    page = doc[pno]
    geo = table_geometry(page)
    if geo is None:
        sys.exit("grade %d guide: could not read the pacing table's geometry "
                 "on page %d" % (grade_of_guide, pno))

    # The legend and the day-count formula sit below the last week row.
    floor = geo["weeks"][-1] + 10.0
    out = {}
    for g in GRADES:
        lines = page_lines(page, geo["bands"][g], geo["headerY"] + 5.0, floor)
        units = parse_column(lines, geo["weeks"], g)
        if sorted(units) != list(range(1, EXPECTED_UNITS + 1)):
            sys.exit("grade %d guide, grade %d column: found units %s"
                     % (grade_of_guide, g, sorted(units)))
        out[g] = units
    return os.path.relpath(path, ROOT), pno, out


def main():
    ap = argparse.ArgumentParser(description="Build the IM 6-8 pacing index.")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    readings, sources = {}, {}
    for guide_grade in GRADES:
        rel, pno, table = parse_guide(guide_grade)
        readings[guide_grade] = table
        sources[str(guide_grade)] = {"file": rel, "pdfPage": pno,
                                     "printedPage": pno - 1}

    # THE TRIPLE CHECK. Every guide prints the whole table, so all three
    # readings must be identical. A disagreement means one parse is wrong, and
    # publishing either would be a guess.
    base = readings[GRADES[0]]
    for other in GRADES[1:]:
        if readings[other] != base:
            diffs = []
            for g in GRADES:
                for u in range(1, EXPECTED_UNITS + 1):
                    a, b = base[g].get(u), readings[other][g].get(u)
                    if a != b:
                        diffs.append("grade %d unit %d: guide %d says %s, "
                                     "guide %d says %s"
                                     % (g, u, GRADES[0], a, other, b))
            sys.exit("pacing: the guides disagree about the table they all print:\n  "
                     + "\n  ".join(diffs))

    # Cross-check against the numbering index: same unit titles, and no
    # optional lesson numbered past the end of its unit.
    notes = []
    if os.path.exists(REF):
        ref = json.load(open(REF))["grades"]
        for g in GRADES:
            spec = ref.get(str(g))
            if not spec:
                continue
            for u in range(1, EXPECTED_UNITS + 1):
                pacing = base[g][u]
                ref_unit = spec["units"].get(str(u))
                if not ref_unit:
                    continue
                if pacing["title"] != ref_unit["title"]:
                    notes.append("grade %d unit %d title: pacing table %r, "
                                 "scope and sequence %r"
                                 % (g, u, pacing["title"], ref_unit["title"]))
                count = len(ref_unit["lessons"])
                if isinstance(pacing["optionalLessons"], list):
                    past = [n for n in pacing["optionalLessons"] if n > count]
                    if past:
                        sys.exit("pacing: grade %d unit %d marks lesson(s) %s "
                                 "optional but the unit has only %d lessons"
                                 % (g, u, past, count))
    else:
        notes.append("data/im_ms_reference.json absent -- titles and optional "
                     "lesson numbers were not cross-checked")

    payload = {
        "meta": {
            "schemaVersion": "1.0",
            "generatedBy": "tools/extract_pacing.py",
            "generated": datetime.date.today().isoformat(),
            "edition": "Imagine IM New York, 6-8",
            "numbering": "newYork",
            "note": "GENERATED from the 35-week pacing table. Re-run the extractor "
                    "rather than hand-editing.",
            "weeks": EXPECTED_WEEKS,
            "readFrom": sources,
            "agreement": "All three Teacher Course Guides print this whole table for "
                         "all three grades. Every figure here was read from all three "
                         "independently and the three readings were identical; the "
                         "build fails if they are not.",
            "conventions": {
                "days": "[minimum, maximum]. Equal when the guide prints a single "
                        "number. The range includes two assessment days per unit; "
                        "the upper bound includes the optional lessons.",
                "midUnitAssessment": "The guide's (MA) mark -- 'Unit has Mid-Unit "
                                     "Assessment'.",
                "optionalLessons": "Lesson numbers within the unit, or [] for the "
                                   "guide's 'none', or the string 'all' for Unit 9, "
                                   "which is optional in its entirety.",
                "startWeek": "1-35, derived from the unit block's vertical position "
                             "against the 35 week labels in the table's left margin. "
                             "The guide does not print a start week per unit, so this "
                             "is read off the layout, not quoted.",
                "dayCountFormula": "The guide's own footnote: number of days for each "
                                   "course = Lessons + Assessments - Optional Lessons.",
            },
            "notes": notes,
        },
        "grades": {str(g): {str(u): base[g][u] for u in range(1, EXPECTED_UNITS + 1)}
                   for g in GRADES},
    }

    if args.stdout:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return
    with open(OUT, "w") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    print("  read from all three guides independently; the three readings agree")
    for g in GRADES:
        units = base[g]
        lo = sum(units[u]["days"][0] for u in units)
        hi = sum(units[u]["days"][1] for u in units)
        ma = sum(1 for u in units if units[u]["midUnitAssessment"])
        print("  grade %d: %d-%d days across 9 units, %d with a mid-unit assessment"
              % (g, lo, hi, ma))
    for line in notes:
        print("  note: %s" % line)


if __name__ == "__main__":
    main()
