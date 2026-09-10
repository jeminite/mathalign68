#!/usr/bin/env python3
"""
Extract NYSED's "Map to the Standards" table from one released-items PDF.

  python3 tools/extract_item_map.py sources/2026-released-items-math-g7.pdf
  python3 tools/extract_item_map.py <pdf> --grade 7 --year 2026   # override the filename
  python3 tools/extract_item_map.py <pdf> --stdout                # print, write nothing

Reads  : one released-items PDF
Writes : provenance/itemmap_<testId>.json

This is the only place the item data comes from. The questions themselves are
vector artwork with no text layer, so this table is the dataset -- see README.

WHY THIS PARSES GEOMETRY AND NOT TEXT
Four properties of the table defeat string splitting, and each one produces a
plausible-looking wrong answer rather than a crash:

1. The Key column is EMPTY on constructed-response rows. Splitting a row on
   whitespace therefore shifts the credit value into the key column, and you get
   a dataset where every CR item has an answer key of "2".
2. Column positions move between years and grades. The Standard column's left
   edge is x=221 on 2026 grade 7, x=213 on 2026 grade 6 and x=192 on 2023
   grade 6, and the CCLS-era layout is different again. So boundaries are
   derived from each page's own header row, never hardcoded.
3. Cluster and Subscore are CENTRE-aligned. Two rows of the same column start at
   different x (one row's "Ratios" begins at x=293, the next row's "The" at
   x=312), so a word is assigned by its centre, not its left edge.
4. A single logical row spans up to three text baselines. The P-value sits 1-2pt
   below its own row against a ~10pt row pitch, and Cluster and Standard wrap
   unpredictably. Rows are therefore banded between item-number anchors rather
   than grouped on an exact y.

A fifth, for the CCLS era: the map spans two pages and the second has no header
row at all, so its columns are inherited from the first.

WHAT IT REFUSES TO DO
Repair a row it does not understand. A blank key on a multiple-choice row means
the columns shifted, and the only safe response is to fail loudly -- a repaired
guess here would be indistinguishable from real data downstream.
"""

import argparse
import datetime
import json
import os
import re
import statistics
import sys

try:
    import fitz
except ImportError:
    sys.exit("PyMuPDF is required (poppler is not installed on this machine).\n"
             "  python3 -m pip install --user pymupdf")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(ROOT, "provenance")

# Both standards eras. (?:NY-)* rather than (?:NY-)? deliberately: the 2024
# grade 8 map prints NGLS.Math.Content.NY-NY-8.EE.6, and a code the extractor
# cannot see is worse than one it repairs and records.
CODE_RE = re.compile(r"(?:NGLS|CCSS)\.Math\.Content\.((?:NY-)*\d[A-Za-z0-9.]*)")

TYPE_WORDS = ("Multiple Choice", "Constructed Response", "Constructed-Response")
KEY_RE = re.compile(r"^[A-D]$")
CREDIT_RE = re.compile(r"^[123]$")
ITEM_RE = re.compile(r"^\d{1,2}$")
SESSION_RE = re.compile(r"^Session\s+(\d)$")
# P-values print with one or two decimals ("0.5" on the 2022 maps, "0.53" on the
# 2023+ maps); average points earned can exceed 1 on a 2- or 3-credit item.
STAT_RE = re.compile(r"^\d?\.\d{1,2}$|^[0-3](?:\.\d{1,2})?$")

# The header vocabulary is not constant across years, so each column is
# declared as (internal name, accepted header words, required).
#
#   2023, 2025, 2026 : Question Type Key Points Standard Cluster Subscore Secondary
#   2024             : Question Type Key Points Standard Domain            Secondary
#   2022 (CCLS)      : Question Type Key Points Standard Cluster
#
# "Cluster" and "Domain" are the same column, and 2024's name for it is the
# accurate one: in every year the values are domain names -- "Expressions and
# Equations", "The Number System" -- not cluster descriptions. That is why the
# extracted field is called domainLabel. A standard's actual cluster description
# comes from data/standards.json, which reads it from the educator guide.
COLUMN_SPEC = (
    ("Question",  ("Question",),           True),
    ("Type",      ("Type",),               True),
    ("Key",       ("Key",),                True),
    ("Points",    ("Points",),             True),
    ("Standard",  ("Standard",),           True),
    ("Domain",    ("Cluster", "Domain"),   True),
    ("Subscore",  ("Subscore",),           False),
    ("Secondary", ("Secondary",),          False),
)

BAND_LEAD = 4.0        # pt above an anchor that still belongs to its row


# --------------------------------------------------------------------- reading

def page_words(page):
    """[(centre_x, left_x, right_x, y, text)] for every non-blank word."""
    out = []
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        if text.strip():
            out.append(((x0 + x1) / 2.0, x0, x1, round(y0, 1), text))
    return out


def rows_of(words):
    """Words grouped by exact y, each row sorted left to right."""
    rows = {}
    for cx, x0, x1, y, text in words:
        rows.setdefault(y, []).append((cx, x0, x1, text))
    return {y: sorted(v) for y, v in sorted(rows.items())}


FOOTNOTE_RE = re.compile(r"^\*|item map is intended")


def trim_footnote(rows):
    """Drop the table's footnote and anything below it.

    Every map ends with "*This item map is intended to identify the primary
    analytic skills...". The last item's row band extends past its anchor to
    catch a wrapped line, which also swallows the footnote -- and the footnote
    contains the word "Constructed", so it parsed as part of item 48's type.
    Cutting it before banding is cheaper than making the band cleverer."""
    cut = None
    for y, cells in rows.items():
        joined = " ".join(t for cx, x0, x1, t in cells).strip()
        if FOOTNOTE_RE.search(joined):
            cut = y if cut is None else min(cut, y)
    if cut is None:
        return rows
    return {y: v for y, v in rows.items() if y < cut}


def find_map_pages(doc):
    """The contiguous run of pages holding the item map.

    A page qualifies on the table's title OR on carrying three or more standard
    codes. The second test is what finds the CCLS-era continuation page, which
    has no title, no header row, and nothing else to identify it. The map is not
    always the last page: on the 2022 maps it is pages 33-34 of 34."""
    hits = []
    for i, page in enumerate(doc):
        text = page.get_text()
        titled = re.search(r"Map to the (?:Learning )?Standards", text) is not None
        codes = len(CODE_RE.findall(text))
        if titled or codes >= 3:
            hits.append(i)
    if not hits:
        return []
    run = [hits[0]]
    for i in hits[1:]:
        if i == run[-1] + 1:
            run.append(i)
        else:
            break
    return run


# --------------------------------------------------------------------- columns

def header_columns(rows):
    """Column boundaries from the page's own header row.

    Returns {name: (lo, hi)} covering the labelled columns, plus a 'stats' band
    for everything to their right. The three statistics columns are deliberately
    NOT split here: which one a number belongs to follows from the row's item
    type, which is a stronger signal than any x boundary (see split_stats)."""
    for y, cells in rows.items():
        seen = {}
        for cx, x0, x1, text in cells:
            seen.setdefault(text, (cx, x0, x1))

        found = {}
        for name, accepted, required in COLUMN_SPEC:
            for word in accepted:
                if word in seen:
                    found[name] = seen[word]
                    break
        if any(required and name not in found for name, _, required in COLUMN_SPEC):
            continue

        present = [name for name, _, _ in COLUMN_SPEC if name in found]
        present.sort(key=lambda n: found[n][0])

        # "Secondary Standard(s)" is one column printed as two words. Its label
        # is matched on "Secondary"; the trailing "Standard(s)" matters only for
        # working out where the labelled columns stop and the statistics begin.
        label_right = max(x1 for cx, x0, x1, text in cells
                          if x0 <= found[present[-1]][1] + 200)
        centres = [found[n][0] for n in present]
        bands = {}
        for idx, name in enumerate(present):
            lo = 0.0 if idx == 0 else (centres[idx - 1] + centres[idx]) / 2.0
            hi = (label_right + 8.0 if idx + 1 == len(present)
                  else (centres[idx] + centres[idx + 1]) / 2.0)
            bands[name] = (lo, hi)

        # Everything right of the labelled columns is the three-column
        # statistics region, left unsplit on purpose -- see split_stats.
        bands["stats"] = (label_right + 8.0, 10_000.0)
        return {"headerY": y, "bands": bands, "columns": present}
    return None


def cell(row_cells, band):
    lo, hi = band
    return " ".join(t for cx, x0, x1, t in row_cells if lo <= cx < hi).strip()


# ------------------------------------------------------------------------ rows

def band_rows(rows, bands, header_y):
    """Split a page into logical rows, banded between item-number anchors.

    An anchor is a bare 1-2 digit number in the Question column. A row's band
    runs from just above its anchor to just above the next one, which is what
    collects the P-value sitting a point or two below its own baseline. The last
    row is capped at one median row pitch so the table's footnote does not get
    swept into it."""
    anchors = []
    for y, cells in rows.items():
        if y <= header_y:
            continue
        text = cell(cells, bands["Question"])
        if ITEM_RE.match(text):
            anchors.append((y, int(text)))

    sessions = {}
    for y, cells in rows.items():
        if y <= header_y:
            continue
        joined = " ".join(t for cx, x0, x1, t in cells).strip()
        m = SESSION_RE.match(joined)
        if m:
            sessions[y] = int(m.group(1))

    if not anchors:
        return [], sessions

    pitch = 12.0
    if len(anchors) > 2:
        gaps = [b[0] - a[0] for a, b in zip(anchors, anchors[1:]) if b[0] - a[0] > 0]
        if gaps:
            pitch = statistics.median(gaps)

    banded = []
    for idx, (y, item) in enumerate(anchors):
        lo = y - BAND_LEAD
        hi = (anchors[idx + 1][0] - BAND_LEAD if idx + 1 < len(anchors)
              else y + pitch * 1.5)
        collected = []
        for ry, cells in rows.items():
            if lo <= ry < hi:
                collected.extend(cells)
        banded.append({"item": item, "anchorY": y, "words": sorted(collected)})
    return banded, sessions


def split_stats(text, item_type, credits, where):
    """The statistics cells of one row -> (pValue, avgPointsEarned).

    Assignment is by ROW TYPE, not by x. The three statistics columns are
    'Percentage of Students Who Answered Correctly (P-Value)', 'Average Points
    Earned' and 'P-Value (Average Points Earned / Total Possible Points)', and
    they are mutually exclusive: a multiple-choice row fills only the first, a
    constructed-response row only the last two. Reading them positionally means
    parsing a three-deep multi-line header; reading them by type needs nothing
    but the count, and the count is checkable."""
    numbers = [t for t in text.split() if STAT_RE.match(t)]
    if item_type == "Multiple Choice":
        if len(numbers) != 1:
            sys.exit("%s: expected one statistic on a multiple-choice row, got %r"
                     % (where, numbers))
        return float(numbers[0]), None
    if len(numbers) != 2:
        sys.exit("%s: expected two statistics on a constructed-response row "
                 "(average points earned, then P-value), got %r" % (where, numbers))
    avg, pvalue = float(numbers[0]), float(numbers[1])
    if avg > credits:
        sys.exit("%s: average points earned %s exceeds the item's %d credits -- "
                 "the statistics columns are the wrong way round" % (where, avg, credits))
    return pvalue, avg


def normalize_code(raw):
    """('NY-7.EE.4a', 'nextgen', repair) or ('7.RP.A.1', 'ccls', repair)."""
    code = raw.strip()
    repair = None
    doubled = re.match(r"^(?:NY-){2,}", code)
    if doubled:
        code = re.sub(r"^(?:NY-)+", "NY-", code)
        repair = "collapsed a duplicated NY- prefix printed in the source (%r)" % raw.strip()
    if raw != code and repair is None:
        repair = "stripped surrounding whitespace"
    era = "nextgen" if code.startswith("NY-") else "ccls"
    return code, era, repair


def parse_row(band, bands, session, where, grade):
    words = band["words"]
    raw = " | ".join(t for cx, x0, x1, t in words)

    type_text = cell(words, bands["Type"])
    item_type = next((t for t in TYPE_WORDS if type_text.startswith(t)), None)
    if item_type is None:
        sys.exit("%s: unrecognised item type %r" % (where, type_text))
    item_type = "Constructed Response" if item_type.startswith("Constructed") else item_type

    key_text = cell(words, bands["Key"])
    credit_text = cell(words, bands["Points"])
    if not CREDIT_RE.match(credit_text):
        sys.exit("%s: credits column holds %r, expected 1, 2 or 3" % (where, credit_text))
    credits = int(credit_text)

    if item_type == "Multiple Choice":
        # Load-bearing. An empty key here means the columns shifted, and a
        # shifted parse is not a parse -- never fill this in from the blueprint.
        if not KEY_RE.match(key_text):
            sys.exit("%s: multiple-choice row has no answer key in A-D (found %r). "
                     "The columns have shifted; do not repair, fix the parse."
                     % (where, key_text))
        if credits != 1:
            sys.exit("%s: multiple-choice item carries %d credits, expected 1"
                     % (where, credits))
        key = key_text
    else:
        if key_text and key_text.lower() not in ("n/a", "na", "-"):
            sys.exit("%s: constructed-response row has %r in the Key column"
                     % (where, key_text))
        key = None

    codes = [normalize_code(c) for c in CODE_RE.findall(
        cell(words, bands["Standard"]) + " " +
        (cell(words, bands["Secondary"]) if "Secondary" in bands else ""))]
    if not codes:
        sys.exit("%s: no standard code found" % where)

    primary, era, repair = codes[0]
    secondary = [c for c, _, _ in codes[1:]]
    repairs = [r for _, _, r in codes if r]

    pvalue, avg = split_stats(cell(words, bands["stats"]), item_type, credits, where)

    return {
        "item": band["item"],
        "session": session,
        "type": item_type,
        "key": key,
        "credits": credits,
        "standard": primary,
        "standardsEra": era,
        "secondaryStandards": secondary,
        "domainLabel": cell(words, bands["Domain"]) or None,
        "subscore": (cell(words, bands["Subscore"]) or None) if "Subscore" in bands else None,
        "pValue": pvalue,
        "avgPointsEarned": avg,
        "extraction": {
            "anchorY": band["anchorY"],
            "raw": raw,
            "repairs": repairs,
        },
    }


# ------------------------------------------------------------------- assertions

def check(items, grade, where):
    """Every check here catches a specific way the parse can go wrong quietly."""
    numbers = [i["item"] for i in items]
    if len(set(numbers)) != len(numbers):
        dupes = sorted({n for n in numbers if numbers.count(n) > 1})
        sys.exit("%s: duplicate item numbers %s" % (where, dupes))
    if numbers != sorted(numbers):
        sys.exit("%s: item numbers are not increasing -- rows were mis-banded" % where)

    mc = [i for i in items if i["type"] == "Multiple Choice"]
    cr = [i for i in items if i["type"] == "Constructed Response"]

    # A shifted Key column reads as a constant, so a degenerate key distribution
    # is evidence of a bad parse even when every individual row looked fine.
    if mc:
        counts = {}
        for i in mc:
            counts[i["key"]] = counts.get(i["key"], 0) + 1
        top, n = max(counts.items(), key=lambda kv: kv[1])
        if n / len(mc) > 0.6:
            sys.exit("%s: %d of %d multiple-choice keys are %r -- the Key column "
                     "is probably not being read" % (where, n, len(mc), top))

    for i in cr:
        if i["credits"] not in (1, 2, 3):
            sys.exit("%s item %d: constructed-response credits %d" % (where, i["item"], i["credits"]))
        if i["avgPointsEarned"] is None:
            sys.exit("%s item %d: constructed-response row has no average points earned"
                     % (where, i["item"]))
    for i in items:
        if not (0.0 < i["pValue"] <= 1.0):
            sys.exit("%s item %d: P-value %s outside (0, 1]" % (where, i["item"], i["pValue"]))
    return {"multipleChoice": len(mc), "constructedResponse": len(cr)}


# ------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Extract one released-items item map.")
    ap.add_argument("pdf")
    ap.add_argument("--grade", type=int)
    ap.add_argument("--year", type=int)
    ap.add_argument("--stdout", action="store_true", help="print the JSON, write nothing")
    args = ap.parse_args()

    base = os.path.basename(args.pdf)
    grade = args.grade or int(re.search(r"-g(\d)\b", base).group(1))
    year = args.year or int(re.match(r"(\d{4})", base).group(1))
    test_id = "g%d-%d" % (grade, year)

    doc = fitz.open(args.pdf)
    pages = find_map_pages(doc)
    if not pages:
        sys.exit("%s: no item map page found" % base)

    items, bands, columns, header_page = [], None, None, None
    for page_index in pages:
        rows = trim_footnote(rows_of(page_words(doc[page_index])))
        found = header_columns(rows)
        if found:
            bands, columns, header_page = found["bands"], found["columns"], page_index
            header_y = found["headerY"]
        elif bands is None:
            continue          # a titled page before the header, e.g. the 2022 maps
        else:
            # A CCLS-era continuation page carries no header. Inherit the
            # previous page's columns, but only if item numbers still land in
            # the Question column -- otherwise the layout changed and inheriting
            # would produce confident nonsense.
            header_y = -1.0
            probe, _ = band_rows(rows, bands, header_y)
            if not probe:
                sys.exit("%s page %d: no header row, and inherited columns find no "
                         "item numbers in the Question column"
                         % (base, page_index + 1))

        banded, sessions = band_rows(rows, bands, header_y)
        session = None
        for band in banded:
            for sy, snum in sessions.items():
                if sy < band["anchorY"]:
                    session = snum
            where = "%s page %d item %d" % (base, page_index + 1, band["item"])
            row = parse_row(band, bands, session, where, grade)
            row["extraction"]["mapPage"] = page_index + 1
            items.append(row)

    if bands is None:
        sys.exit("%s: found map pages but no header row on any of them" % base)

    counts = check(items, grade, base)
    eras = sorted({i["standardsEra"] for i in items})
    repairs = [(i["item"], r) for i in items for r in i["extraction"]["repairs"]]

    payload = {
        "meta": {
            "schemaVersion": "1.0",
            "generatedBy": "tools/extract_item_map.py",
            "generated": datetime.date.today().isoformat(),
            "testId": test_id,
            "grade": grade,
            "year": year,
            "source": os.path.relpath(os.path.abspath(args.pdf), ROOT),
            "pdfPageCount": doc.page_count,
            "mapPages": [p + 1 for p in pages],
            "headerPage": header_page + 1,
            "columns": columns,
            "standardsEra": eras[0] if len(eras) == 1 else eras,
            "releasedItems": len(items),
            "multipleChoice": counts["multipleChoice"],
            "constructedResponse": counts["constructedResponse"],
            "creditsReleased": sum(i["credits"] for i in items),
            "repairs": [{"item": n, "what": r} for n, r in repairs],
        },
        "items": items,
    }

    if args.stdout:
        json.dump(payload, sys.stdout, indent=2)
        print()
        return

    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, "itemmap_%s.json" % test_id)
    with open(out, "w") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print("%-46s -> %s" % (base, os.path.relpath(out, ROOT)))
    print("   %d items (%d MC, %d CR), %d credits, era %s, map pages %s, columns %s"
          % (len(items), counts["multipleChoice"], counts["constructedResponse"],
             payload["meta"]["creditsReleased"], payload["meta"]["standardsEra"],
             payload["meta"]["mapPages"], ", ".join(columns)))
    for n, r in repairs:
        print("   repaired item %d: %s" % (n, r))


if __name__ == "__main__":
    main()
