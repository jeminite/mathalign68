#!/usr/bin/env python3
"""
Build data/standards.json from the NYSED Grades 3-8 Mathematics Educator Guide.

  python3 tools/extract_standards.py

Reads  : sources/3-8-educator-guide-math.pdf
Writes : data/standards.json

WHAT IT PRODUCES
One entry per atomic standard code for grades 5-8, carrying its grade, domain
abbreviation and full name, the official cluster description, a fluency note
where the guide gives one, and whether it is a post-test standard -- taught in
this grade, tested in the next. Grade 5 is included because NY-5.OA.3 and its
neighbours are post-test standards that appear on the grade 6 test: an item map
can legitimately cite them, so the registry has to know them.

TWO INDEPENDENT SOURCES FOR THE POST-TEST FLAG, AND THEY ARE CHECKED AGAINST
EACH OTHER
The grade-level standards charts carry a "Post-Test Standard" column marked with
a literal X, and the guide separately publishes "Grade N Post-Test Standards
Assessed in Grade N+1" tables. Both are read; a disagreement is a hard failure.
Two sources agreeing is the only reason to trust a flag that decides which
grade's test may cite a standard.

WHAT IS NOT HERE
The full standard statement. This guide publishes cluster-level descriptions
only; per-standard wording lives in the NYSED Next Generation Learning Standards
document, a separate source. `statement` is null on every entry and
`clusterText` is what the site displays. Do not paper over that by copying the
cluster text into `statement` -- a reader needs to know which one they have.
"""

import argparse
import datetime
import json
import os
import re
import sys

try:
    import fitz
except ImportError:
    sys.exit("PyMuPDF is required (poppler is not installed on this machine).\n"
             "  python3 -m pip install --user pymupdf")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GUIDE = os.path.join(ROOT, "sources", "3-8-educator-guide-math.pdf")
OUT = os.path.join(ROOT, "data", "standards.json")

# The Imagine IM New York Teacher Course Guides carry the full wording of every
# standard, which the educator guide does not -- it gives cluster descriptions
# only. Grades 6-8 are covered; grade 5's post-test standards are not, because
# no grade 6-8 guide lists them.
TCG = os.path.join(ROOT, "sources", "ImagineIM_NY_%d__TCG_NA_V2_EN_DIG.pdf")
TCG_GRADES = (6, 7, 8)
REFERENCE_HEADING = "NYSNGMLS for Mathematics Reference"
TCG_CODE_RE = re.compile(
    r"^(NY-\d\.[A-Z]{1,3}\.(?:Cluster-\d+|\d+(?:\.[a-z])?))$")
DOMAIN_HEADER_RE = re.compile(r"^NY-\d\.[A-Z]{1,3}:\s")

# Grades whose charts are parsed. 5 is here only to hold the post-test codes
# that the grade 6 test cites; 3 and 4 are out of scope.
CHART_GRADES = (5, 6, 7, 8)

# Domain abbreviation -> full name as the standards charts spell it.
DOMAINS = {
    "OA": "Operations and Algebraic Thinking",
    "NBT": "Number and Operations in Base Ten",
    "NF": "Number and Operations - Fractions",
    "MD": "Measurement and Data",
    "RP": "Ratios and Proportional Relationships",
    "NS": "The Number System",
    "EE": "Expressions, Equations, and Inequalities",
    "F": "Functions",
    "G": "Geometry",
    "SP": "Statistics and Probability",
}

# The released-items item maps spell one domain differently from the standards
# charts. Recorded rather than normalised away: the site shows the map's wording
# in the item table and the guide's wording on the standard card.
MAP_DOMAIN_ALIASES = {
    "EE": "Expressions and Equations",
}

# One cell of the Standard(s) column. The sub-letter list may continue onto the
# next line (grade 7: "NY-7.EE.4a (Fluency)," then "4b" alone below it), which
# CONTINUATION handles.
CODE_LINE = re.compile(
    r"NY-(?P<grade>\d)\.(?P<domain>[A-Z]{1,3})\.(?P<first>\d+[a-z]?)"
    r"(?P<rest>(?:\s*,\s*\d*[a-z]?)*)"
)
CONTINUATION = re.compile(r"^\s*\d*[a-z]?(?:\s*,\s*\d*[a-z]?)*\s*,?\s*$")
ANNOTATION = re.compile(r"\(([^)]+)\)")

# Within one merged cell, lines sit ~14.4pt apart; the next cell starts ~17-25pt
# later. Those ranges overlap, so a gap alone cannot separate cells -- see
# group_blocks.
# A table rule is a filled rectangle wide enough to span a column and only a
# point or two tall. 2.5pt clears the thickest rule in these charts (1.0) with
# room to spare while excluding anything that is really a box.
RULE_MAX_H = 2.5
RULE_MIN_W = 40.0
# A code line's recorded y is the top of its text, which can sit a fraction of a
# point ABOVE its cell's top rule (grade 7 prints NY-7.SP.1 at y=405.9 under a
# rule at y=406.0). Probing 2pt lower lands inside the cell without reaching the
# next one, since consecutive code lines are 16.3pt apart.
CELL_PROBE = 2.0

SAME_CELL_GAP = 15.5
SENTENCE_END_GAP = 13.5


def words_by_row(page):
    rows = {}
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        if text.strip():
            rows.setdefault(round(y0, 1), []).append((x0, text))
    return {y: sorted(v) for y, v in sorted(rows.items())}


def column_bands(rows):
    """Derive the four column bands from the page's own geometry.

    Header word positions alone are not enough: "Standard(s)" is left-aligned at
    x=393 while the codes beneath it start at x=364 and the cluster text above
    runs out to x=330. Taking the header midpoint would put the tail of every
    wrapped cluster line into the Standard(s) column, which silently truncated
    "real-world and mathematical problems" to "real-world mathematical
    problems". So the Cluster/Standard boundary comes from where the codes
    actually are, and the Standard/Post-Test boundary from where the X marks
    actually are."""
    header_y = None
    dom_x = clu_x = None
    for y, cells in rows.items():
        labels = {t: x for x, t in cells}
        if "Domain" in labels and "Cluster" in labels and "Standard(s)" in labels:
            header_y, dom_x, clu_x = y, labels["Domain"], labels["Cluster"]
            break
    if header_y is None:
        return None

    code_xs = [x for y, cells in rows.items() if y > header_y
               for x, text in cells if re.match(r"^NY-\d\.", text)]
    if not code_xs:
        return None
    std_left = min(code_xs) - 12.0

    # Post-Test marks are literal X glyphs far to the right of the codes. The
    # x > std_left + 80 guard is not cosmetic: these pages also contain a stray
    # "X" at x=48 in the left margin, and taking min() over every X collapsed
    # the Standard(s) band to nothing.
    mark_xs = [x for y, cells in rows.items() if y > header_y
               for x, text in cells
               if text.strip() == "X" and x > std_left + 80.0]
    post_left = (min(mark_xs) - 12.0) if mark_xs else std_left + 120.0
    return {
        "headerY": header_y,
        "domain": (0.0, (dom_x + clu_x) / 2.0),
        "cluster": ((dom_x + clu_x) / 2.0, std_left),
        "standard": (std_left, post_left),
        "posttest": (post_left, 10_000.0),
    }


def cells_in(rows, band, below):
    lo, hi = band
    out = []
    for y, cells in rows.items():
        if y <= below:
            continue
        text = " ".join(t for x, t in cells if lo <= x < hi)
        if text.strip():
            out.append((y, text.strip()))
    return out


def group_blocks(cells):
    """Merge the lines of one merged table cell into a block (start_y, end_y, text).

    A gap alone cannot decide where a cell ends: within a cell lines are ~14.4pt
    apart, and the next cell can start only 17.3pt later (grade 5's two
    Operations and Algebraic Thinking clusters). So a new cell starts when the
    gap is clearly large, OR when the text so far ends in a full stop and the gap
    is at least a line height. Cluster descriptions are complete sentences, which
    is what makes the second test reliable."""
    blocks = []
    for y, text in cells:
        if blocks:
            gap = y - blocks[-1][1]
            ends_sentence = blocks[-1][2][-1].endswith(".")
            same_cell = gap < SAME_CELL_GAP and not (ends_sentence and gap > SENTENCE_END_GAP)
            if same_cell:
                blocks[-1][1] = y
                blocks[-1][2].append(text)
                continue
        blocks.append([y, y, [text]])
    return [(b[0], b[1], " ".join(b[2])) for b in blocks]


def cells_by_rule(page, rows, band, below):
    """The merged cells of one column, as (top, bottom, text), from the RULES.

    This is the exact answer where `group_blocks` plus `owner_of` below is only
    a good guess. These charts draw every cell boundary as a horizontal rule,
    and a merged cell is drawn by simply omitting the interior ones: grade 7's
    Standard(s) column has a rule every 16.3pt from 340.8 to 455.0, while its
    Cluster column over the same span has rules at 357.1, 406.0 and 455.0 only
    -- so the cell from 406.0 to 455.0 is one merged cell covering three codes.
    Reading the rules therefore recovers NYSED's own cell structure instead of
    inferring it from where the text happens to sit.

    Inference was not good enough. Boundary-midpoint assignment put grade 8's
    NY-8.G.1a/1b/1c (rigid transformations) under "Use functions to model
    relationships between quantities" and gave NY-5.NBT.4, NY-6.EE.8 and
    NY-8.EE.4 the neighbouring cluster's description -- seven wrong cluster
    descriptions on a field the site displays.

    Returns [] if the page draws no rules across this band, which is the signal
    to fall back."""
    lo, hi = band
    edges = set()
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if (rect.height <= RULE_MAX_H and rect.width >= RULE_MIN_W
                and rect.x0 < hi - 10.0 and rect.x1 > lo + 10.0):
            edges.add(round(rect.y0, 1))
    edges = sorted(y for y in edges if y > below - 12.0)
    if len(edges) < 2:
        return []

    lines = cells_in(rows, band, below)
    cells = []
    for top, bottom in zip(edges, edges[1:]):
        text = " ".join(t for y, t in lines if top <= y + CELL_PROBE < bottom)
        cells.append((top, bottom, text.strip() or None))
    return cells


def owner_by_rule(y, cells):
    """The text of the rule-delimited cell a code at height y falls in."""
    for top, bottom, text in cells:
        if top <= y + CELL_PROBE < bottom:
            return text
    return None


def owner_index_of(y, blocks):
    """The index of the merged cell a code at height y belongs to."""
    if not blocks:
        return None
    for i, (start, end, text) in enumerate(blocks):
        if i + 1 == len(blocks):
            return i
        if y < (end + blocks[i + 1][0]) / 2.0:
            return i
    return len(blocks) - 1


def owner_of(y, blocks):
    """The merged cell a code at height y belongs to.

    By BOUNDARY, not proximity, and this is load-bearing. A merged cell is
    vertically centred over the codes it governs, so it can start below its own
    first code (grade 6: the RP cluster starts at y=96.3, NY-6.RP.1 sits at
    y=87.0) and end above its last (grade 7: the RP cluster ends at y=134.8,
    NY-7.RP.3 sits at y=136.5). Nearest-start is wrong in the first case,
    nearest-anything in the second. Splitting at the midpoint between one
    block's end and the next block's start is right in both."""
    if not blocks:
        return None
    for i, (start, end, text) in enumerate(blocks):
        if i + 1 == len(blocks):
            return text
        if y < (end + blocks[i + 1][0]) / 2.0:
            return text
    return blocks[-1][2]


def join_continuations(cells):
    """Fold a bare sub-letter line into the code line above it.

    Grade 7 prints "NY-7.EE.4a (Fluency)," on one line and "4b" alone on the
    next. Without this, NY-7.EE.4b is absent from the registry -- and it is a
    real standard, cited by all four grade 7 item maps."""
    out = []
    for y, text in cells:
        if out and CONTINUATION.match(text) and re.search(r"[a-z]", text):
            prev_y, prev_text = out[-1]
            out[-1] = (prev_y, prev_text.rstrip().rstrip(",") + ", " + text.strip().rstrip(","))
            continue
        out.append((y, text))
    return out


def expand(line):
    """'NY-7.RP.2a, 2b, 2c, 2d' -> four codes. Returns (codes, annotation).

    The annotation is lifted out BEFORE the codes are matched, because it can
    sit in the middle of the sub-letter list: grade 7 prints
    "NY-7.EE.4a (Fluency)," and then "4b" on the line below. Matching the list
    around the parenthetical loses 4b entirely -- a real standard that all four
    grade 7 item maps cite."""
    annot = ANNOTATION.search(line)
    bare = re.sub(r",\s*,", ",", ANNOTATION.sub("", line))
    m = CODE_LINE.search(bare)
    if not m:
        return [], None, None
    prefix = "NY-%s.%s." % (m.group("grade"), m.group("domain"))
    codes = [prefix + m.group("first")]
    for token in (m.group("rest") or "").split(","):
        token = token.strip()
        if token:
            codes.append(prefix + token)
    if not annot:
        return codes, None, None

    # An annotation belongs to the one code it follows, not to the whole cell.
    # "NY-7.EE.4a (Fluency), 4b" designates 4a for fluency and says nothing
    # about 4b; carrying the note to both would publish a claim the guide does
    # not make.
    before = re.sub(r",\s*,", ",", line[:annot.start()])
    owner = 0
    bm = CODE_LINE.search(before)
    if bm:
        owner = len([t for t in (bm.group("rest") or "").split(",") if t.strip()])
    return codes, annot.group(1).strip(), min(owner, len(codes) - 1)


def parse_chart(page, grade):
    rows = words_by_row(page)
    bands = column_bands(rows)
    if not bands:
        sys.exit("grade %d: could not locate the chart columns" % grade)
    y0 = bands["headerY"]
    # Rules first, text-geometry only if a page draws none. Both columns hold
    # merged cells, and both were mis-assigned by the geometric method.
    domain_cells = cells_by_rule(page, rows, bands["domain"], y0)
    cluster_cells = cells_by_rule(page, rows, bands["cluster"], y0)
    domains = group_blocks(cells_in(rows, bands["domain"], y0))
    clusters = group_blocks(cells_in(rows, bands["cluster"], y0))
    marks = [y for y, t in cells_in(rows, bands["posttest"], y0) if t.strip() == "X"]
    code_lines = join_continuations(cells_in(rows, bands["standard"], y0))

    # An X is vertically centred on the cell it marks, so it can sit several
    # points below its code line -- grade 8 prints "NY-8.EE.8a, 8b" at y=261.7
    # and its X at y=268.9. Assign each mark to the nearest code line instead of
    # testing a fixed window, or that standard silently loses its flag.
    marked_ys = set()
    for my in marks:
        candidates = [(abs(y - my), y) for y, text in code_lines if expand(text)[0]]
        if candidates:
            gap, y = min(candidates)
            if gap < 12.0:
                marked_ys.add(y)

    entries, chart_post = {}, set()
    for y, line in code_lines:
        codes, annot, annot_for = expand(line)
        if not codes:
            continue
        if cluster_cells:
            cluster_text = owner_by_rule(y, cluster_cells)
            if cluster_text is None:
                sys.exit("grade %d: %r at y=%.1f falls in no ruled cluster cell"
                         % (grade, codes[0], y))
        else:
            cluster_text = owner_of(y, clusters)
        if domain_cells:
            guide_domain = owner_by_rule(y, domain_cells)
        else:
            guide_domain = owner_of(y, domains)
        marked = y in marked_ys
        for position, code in enumerate(codes):
            dm = re.match(r"NY-(\d)\.([A-Z]{1,3})\.", code)
            if not dm:
                sys.exit("grade %d: unparseable expanded code %r from %r" % (grade, code, line))
            if marked:
                chart_post.add(code)
            entries[code] = {
                "code": code,
                "grade": int(dm.group(1)),
                "domain": dm.group(2),
                "domainName": DOMAINS.get(dm.group(2)),
                "domainNameInGuide": guide_domain,
                "clusterText": cluster_text,
                "statement": None,
                "note": annot if position == annot_for else None,
                "postTest": False,
                "testedInGrade": None,
                "assessedOnGrades": [],
            }
    return entries, chart_post


def parse_post_test_tables(doc):
    """{grade taught: (grade tested, [codes])} from the dedicated tables."""
    out = {}
    for page in doc:
        text = page.get_text()
        m = re.search(r"Grade (\d) Post-Test Standards Assessed in Grade (\d)", text)
        if not m:
            continue
        taught, tested = int(m.group(1)), int(m.group(2))
        if taught not in CHART_GRADES:
            continue          # grades 3-4 are out of scope; their charts are unparsed
        codes = []
        for line in join_continuations([(0, l) for l in text.split("\n")]):
            got = expand(line[1])[0]
            codes.extend(c for c in got if c.startswith("NY-%d." % taught))
        if codes:
            out[taught] = (tested, sorted(set(codes)))
    return out


def statements_from_tcg():
    """{code: full standard wording} from the Teacher Course Guides.

    The table is one code per line followed by its statement, which may wrap
    over several lines, until the next code. The guides print a sub-lettered
    code with a dot -- NY-7.RP.2.a -- where NYSED's item maps write NY-7.RP.2a,
    so the key is normalised to NYSED's form or nothing joins.
    """
    out = {}
    for grade in TCG_GRADES:
        path = TCG % grade
        if not os.path.exists(path):
            continue
        doc = fitz.open(path)
        pages = [i for i, p in enumerate(doc) if REFERENCE_HEADING in p.get_text()]
        if not pages:
            continue
        # Drop the contents-page mention: keep the longest contiguous run.
        runs, current = [], [pages[0]]
        for i in pages[1:]:
            if i - current[-1] <= 2:
                current.append(i)
            else:
                runs.append(current)
                current = [i]
        runs.append(current)
        pages = max(runs, key=len)

        code, parts = None, []
        for i in pages:
            for raw in doc[i].get_text().split("\n"):
                line = raw.strip()
                if not line or line == REFERENCE_HEADING or DOMAIN_HEADER_RE.match(line):
                    continue
                if re.match(r"^(Grade \d Teacher Course Guide|\d+)$", line):
                    continue          # running header and page number
                m = TCG_CODE_RE.match(line)
                if m:
                    if code and parts:
                        out.setdefault(normalise_tcg_code(code),
                                       " ".join(parts).strip())
                    code, parts = m.group(1), []
                elif code:
                    parts.append(line)
        if code and parts:
            out.setdefault(normalise_tcg_code(code), " ".join(parts).strip())
    return out


def normalise_tcg_code(printed):
    if "Cluster" in printed:
        return printed
    return re.sub(r"\.(\d+)\.([a-z])$", r".\1\2", printed)


def main():
    ap = argparse.ArgumentParser(description="Build data/standards.json.")
    # preflight verifies this file still rebuilds from its source. It must be
    # able to do that WITHOUT writing: rewriting the file bumps its mtime past
    # the site build and trips the freshness check, which is a bug the gate
    # inflicted on itself once already.
    ap.add_argument("--stdout", action="store_true",
                    help="print the JSON and write nothing")
    args = ap.parse_args()

    if not os.path.exists(GUIDE):
        sys.exit("missing %s -- run: python3 tools/fetch_sources.py"
                 % os.path.relpath(GUIDE, ROOT))
    doc = fitz.open(GUIDE)

    chart_pages = {}
    for i, page in enumerate(doc):
        text = page.get_text()
        m = re.search(r"^Grade (\d)\s*$", text, re.M)
        if m and "Standard(s)" in text:
            chart_pages.setdefault(int(m.group(1)), i)

    standards, chart_post = {}, set()
    for grade in CHART_GRADES:
        if grade not in chart_pages:
            sys.exit("no standards chart found for grade %d" % grade)
        entries, marked = parse_chart(doc[chart_pages[grade]], grade)
        standards.update(entries)
        chart_post |= marked

    tables = parse_post_test_tables(doc)
    table_post = {c for _, codes in tables.values() for c in codes}

    # The two sources must agree. If they ever don't, the flag is deciding which
    # grade's test may cite a standard on evidence we no longer trust.
    only_chart = sorted(chart_post - table_post)
    only_table = sorted(table_post - chart_post)
    top = max(CHART_GRADES)
    unexplained = [c for c in only_chart if not c.startswith("NY-%d." % top)]
    if unexplained or only_table:
        sys.exit("post-test sources disagree.\n"
                 "  marked X in a chart but absent from the tables: %s\n"
                 "  listed in a table but not marked in its chart: %s\n"
                 "Only grade %d may appear in the first list -- it has no "
                 "next-grade table because there is no grade 9 State test."
                 % (unexplained or "none", only_table or "none", top))

    for taught, (tested, codes) in tables.items():
        for code in codes:
            if code not in standards:
                sys.exit("post-test table names %s, absent from every standards chart" % code)
            standards[code]["postTest"] = True
            standards[code]["testedInGrade"] = tested

    # Grade 8 is the top of this test program, so the guide publishes no
    # "Grade 8 Post-Test Standards Assessed in Grade 9" table -- there is no
    # grade 9 State mathematics test. Its X-marked standards are still post-test
    # (taught May-to-June) but are assessed on NO grades 3-8 test, which is why
    # assessedOnGrades is empty rather than pointing at grade 9. An item map
    # citing one of these would be a genuine anomaly worth investigating.
    for code in sorted(chart_post - table_post):
        rec = standards[code]
        rec["postTest"] = True
        rec["testedInGrade"] = None
        rec["postTestNote"] = ("taught May-to-June; no grades 3-8 test assesses it "
                               "(there is no grade 9 State mathematics test)")

    # Fill in the full wording where a Teacher Course Guide supplies it.
    wording = statements_from_tcg()
    filled = 0
    for code, rec in standards.items():
        if wording.get(code):
            rec["statement"] = wording[code]
            rec["statementSource"] = "Imagine IM New York Teacher Course Guide"
            filled += 1

    for rec in standards.values():
        if rec["postTest"]:
            rec["assessedOnGrades"] = [rec["testedInGrade"]] if rec["testedInGrade"] else []
        else:
            rec["assessedOnGrades"] = [rec["grade"]]

    payload = {
        "meta": {
            "schemaVersion": "1.0",
            "generatedBy": "tools/extract_standards.py",
            "generated": datetime.date.today().isoformat(),
            "source": "sources/3-8-educator-guide-math.pdf",
            "note": "GENERATED. Re-run the extractor rather than hand-editing. "
                    "`statement` is null throughout: the guide publishes cluster "
                    "descriptions, not per-standard wording. Use clusterText, and "
                    "do not copy it into statement.",
            "standardsEra": "nextgen",
            "codeShape": "NY-<grade>.<DOMAIN>.<number><optional letter> -- grade digit "
                         "first, no cluster letter. A different family from "
                         "RegentsAlign's AI-<DOMAIN>.<number> Algebra I codes.",
            "postTestFlagSources": ["grade-chart Post-Test Standard column (X marks)",
                                    "Grade N Post-Test Standards Assessed in Grade N+1 tables"],
            "postTestLegend": "The guide's own key for the X column: \"X = Standards "
                              "designated for instruction in May-to-June\". That is why "
                              "these standards are not assessed in their own grade -- "
                              "they are taught after the test is given.",
            "domains": DOMAINS,
            "mapDomainAliases": MAP_DOMAIN_ALIASES,
        },
        "postTestTables": {str(k): {"testedInGrade": v[0], "codes": v[1]}
                           for k, v in sorted(tables.items())},
        "standards": dict(sorted(standards.items())),
    }
    if args.stdout:
        json.dump(payload, sys.stdout, indent=2)
        print()
        return

    with open(OUT, "w") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    by_grade = {}
    for rec in standards.values():
        by_grade[rec["grade"]] = by_grade.get(rec["grade"], 0) + 1
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    print("  %d with full wording from the course guides, %d without"
          % (filled, len(standards) - filled))
    print("  %d standards -- %s" % (len(standards),
          ", ".join("grade %d: %d" % (g, n) for g, n in sorted(by_grade.items()))))
    print("  post-test flags agree across both sources (%d codes)" % len(table_post))
    for taught, (tested, codes) in sorted(tables.items()):
        print("    %2d grade-%d standards are assessed on the grade %d test"
              % (len(codes), taught, tested))
    for field in ("clusterText", "domainName", "domainNameInGuide"):
        bad = sorted(c for c, r in standards.items() if not r[field])
        if bad:
            print("  WARNING: %d codes have no %s: %s"
                  % (len(bad), field, ", ".join(bad[:8])))


if __name__ == "__main__":
    main()
