#!/usr/bin/env python3
"""
Map each released item to the PDF page it is printed on.

  python3 tools/build_pagemap.py sources/2026-released-items-math-g7.pdf
  python3 tools/build_pagemap.py <pdf> --stdout

Reads  : one released-items PDF, plus provenance/itemmap_<testId>.json
Writes : provenance/pagemap_<testId>.json

WHY THIS IS POSSIBLE AT ALL
The question text in these PDFs does not extract -- every numeral, variable and
figure is vector artwork. But the item NUMBERS do: each one is printed as a bare
digit in the left margin and is a real text glyph. So even though the site
cannot show a question, it can link to the exact page the question is on, which
is the whole reason the item-map-only design is not a compromise.

HOW IT VALIDATES ITSELF
Every item number found in a margin must be one the item map lists as released.
Two independent parts of the same document agreeing is the only reason to trust
a page link. Order is checked too: items must run increasing through the
booklet. A second, independent check confirms the item map's Type column from
the booklet side -- a multiple-choice page prints a column of four choice
letters and a constructed-response page does not.

WHY THE MAP IS ALLOWED TO BE INCOMPLETE
Some item numbers are vector artwork rather than text, and inconsistently so:
the 2023 grade 7 booklet has items 13 and 16 as real glyphs at x=42 and items
1, 2, 17 and 18 as artwork on identically laid-out pages. Refusing to write
anything unless all of them resolve would cost page links on four of the twelve
tests to protect against a risk that is not present -- nothing here interpolates
a page, so an item is either located by its own printed number or left without a
link. What IS fatal is finding a number the item map does not list as released,
because that means something other than an item number is being read.
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
OUTDIR = os.path.join(ROOT, "provenance")

ITEM_RE = re.compile(r"^\d{1,2}$")
CHOICE_RE = re.compile(r"^[A-D]$")
PRINTED_PAGE_RE = re.compile(r"^Page\s+(\d{1,3})$")

MARGIN_X = 60.0        # item numbers sit at x ~ 42-46; nothing else is this far left
TOP_MARGIN = 60.0      # above this is the running header
BOTTOM_MARGIN = 700.0  # below this is the "Page N / GO ON / Session N" footer


def margin_numbers(page):
    """The bare item numbers printed in this page's left margin, top to bottom."""
    found = []
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        t = text.strip()
        if not ITEM_RE.match(t):
            continue
        if x0 < MARGIN_X and TOP_MARGIN < y0 < BOTTOM_MARGIN:
            found.append((y0, int(t)))
    return [n for _, n in sorted(found)]


def printed_page(page):
    """The page number NYSED prints in the footer, which skips withheld items."""
    for line in page.get_text().split("\n"):
        m = PRINTED_PAGE_RE.match(line.strip())
        if m:
            return int(m.group(1))
    return None


def has_choice_column(page):
    """Whether this page prints a real multiple-choice answer list.

    The test is that all four of A, B, C and D appear as bare single-letter
    words. Two weaker rules were tried and both were wrong:

    - Counting bare A-D words: grade 8's 2024 item 48 is a 3-credit constructed
      response about "Store A and Store B" and yields six of them.
    - Requiring the four letters in one left-aligned column: choices are often
      laid out in a 2x2 grid when they are tables or graphs (grade 7 2025 item 2
      puts A and B at x=75 and C and D at x=310), so no single column holds all
      four.

    Requiring all four distinct letters handles both: the Store A/Store B page
    never produces a C or a D."""
    letters = set()
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        t = text.strip()
        if CHOICE_RE.match(t) and TOP_MARGIN < y0 < BOTTOM_MARGIN:
            letters.add(t)
    return letters >= {"A", "B", "C", "D"}


def main():
    ap = argparse.ArgumentParser(description="Map released items to PDF pages.")
    ap.add_argument("pdf")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    base = os.path.basename(args.pdf)
    grade = int(re.search(r"-g(\d)\b", base).group(1))
    year = int(re.match(r"(\d{4})", base).group(1))
    test_id = "g%d-%d" % (grade, year)

    map_path = os.path.join(OUTDIR, "itemmap_%s.json" % test_id)
    if not os.path.exists(map_path):
        sys.exit("missing %s -- run tools/extract_item_map.py first"
                 % os.path.relpath(map_path, ROOT))
    item_map = json.load(open(map_path))
    released = {i["item"]: i for i in item_map["items"]}
    map_pages = set(item_map["meta"]["mapPages"])

    doc = fitz.open(args.pdf)
    pages, printed, choices = {}, {}, {}
    for index in range(doc.page_count):
        if index + 1 in map_pages:
            continue                        # the map itself is full of digits
        page = doc[index]
        for n in margin_numbers(page):
            if n in pages:
                sys.exit("%s: item %d appears in the margin of both page %d and page %d"
                         % (base, n, pages[n], index + 1))
            pages[n] = index + 1
        p = printed_page(page)
        if p is not None:
            printed[index + 1] = p
        choices[index + 1] = has_choice_column(page)

    found, expected = set(pages), set(released)
    stray = sorted(found - expected)
    if stray:
        sys.exit(
            "%s: found item number(s) %s in the margins that the item map does not list as "
            "released. Something other than an item number is being read; no page links "
            "written."
            % (base, stray))
    unlocated = sorted(expected - found)

    order = [n for n in sorted(pages, key=lambda n: (pages[n], n))]
    if order != sorted(order):
        sys.exit("%s: items are not in increasing order through the booklet: %s"
                 % (base, order))

    # Below this, a few vector-drawn numbers is no longer the explanation and the
    # page layout has probably changed.
    coverage = len(pages) / float(len(released))
    if coverage < 0.5:
        sys.exit("%s: only %d of %d released items could be located (%.0f%%). That is too few "
                 "to be explained by vector-drawn item numbers; check the booklet layout."
                 % (base, len(pages), len(released), coverage * 100))

    # Independent confirmation of the item map's Type column, from the booklet.
    disagree = []
    for n, page_no in sorted(pages.items()):
        same_page = [m for m, p in pages.items() if p == page_no]
        kinds = {released[m]["type"] for m in same_page}
        if len(kinds) != 1:
            continue                        # mixed page, nothing to conclude
        kind = kinds.pop()
        has_choices = choices.get(page_no, False)
        if (kind == "Multiple Choice") != has_choices:
            disagree.append((n, page_no, kind, has_choices))

    payload = {
        "meta": {
            "schemaVersion": "1.0",
            "generatedBy": "tools/build_pagemap.py",
            "generated": datetime.date.today().isoformat(),
            "testId": test_id,
            "grade": grade,
            "year": year,
            "source": os.path.relpath(os.path.abspath(args.pdf), ROOT),
            "pdfPageCount": doc.page_count,
            "itemsMapped": len(pages),
            "itemsReleased": len(released),
            "unlocatedItems": unlocated,
            "unlocatedReason": ("their item numbers are drawn as vector artwork rather than "
                                "text, so they carry no page link"
                                if unlocated else None),
            "typeCrossCheck": ("agrees with the item map on every single-type page"
                               if not disagree else
                               "DISAGREES on %d page(s)" % len(disagree)),
            "typeDisagreements": [
                {"item": n, "pdfPage": p, "itemMapType": k, "choiceColumnFound": c}
                for n, p, k, c in disagree],
        },
        "items": {str(n): {"pdfPage": p, "printedPage": printed.get(p)}
                  for n, p in sorted(pages.items())},
    }

    if args.stdout:
        json.dump(payload, sys.stdout, indent=2)
        print()
        return

    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, "pagemap_%s.json" % test_id)
    with open(out, "w") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print("%-46s -> %s" % (base, os.path.relpath(out, ROOT)))
    print("   %d of %d items mapped across %d pages; %s"
          % (len(pages), len(released), len({p for p in pages.values()}),
             payload["meta"]["typeCrossCheck"]))
    if unlocated:
        print("   no page link for %s (item number drawn as artwork, not text)"
              % ", ".join(str(n) for n in unlocated))
    for d in payload["meta"]["typeDisagreements"]:
        print("   item %(item)d on page %(pdfPage)d: map says %(itemMapType)s, "
              "booklet choice column found=%(choiceColumnFound)s" % d)


if __name__ == "__main__":
    main()
