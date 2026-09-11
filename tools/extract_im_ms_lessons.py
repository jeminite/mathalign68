#!/usr/bin/env python3
"""
Build data/im_ms_reference.json from the Imagine IM New York Teacher Course Guides.

  python3 tools/extract_im_ms_lessons.py
  python3 tools/extract_im_ms_lessons.py --grade 7 --stdout

Reads  : sources/ImagineIM_NY_{6,7,8}__TCG_NA_V2_EN_DIG.pdf
Writes : data/im_ms_reference.json

Three tables in each guide, and each is used for what it is best at:

  Scope and Sequence           unit, section and lesson TITLES
  NYSNGMLS Standards by Lesson the authoritative list of which lessons EXIST
  NYSNGMLS Lessons by Standard standard -> lessons, for aligning an item

Lesson counts come from Standards by Lesson rather than from the Scope and
Sequence boxes: it is one clean row per lesson, whereas the boxes are set in a
narrow column inside pages of unit narrative and their titles wrap.

TWO CODE FORMATS FOR THE SAME STANDARD
The guides write NY-7.RP.2.a, with a dot before the sub-letter. NYSED's own item
maps write NY-7.RP.2a, without. Nothing joins unless one is normalised to the
other, so `standard` here is always the NYSED form and `standardAsPrinted` keeps
what the guide said.

NEW YORK NUMBERING, WHICH IS NOT THE NATIONAL NUMBERING
Everything in this file is the Imagine IM New York sequence, and for grades 7
and 8 that is NOT the national one: New York swaps Units 7 and 8. Grade 7's
Unit 7 is Probability and Sampling and its Unit 8 is Angles, Triangles, and
Prisms; nationally they are the other way round. Every unit-numbered structure
therefore carries `numbering: "newYork"`, because the NYCPS workbooks in
sources/nycps/ use national numbering on one sheet and New York numbering on its
siblings, in the same file. Resolve a lesson BY TITLE, never by number.
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
    sys.exit("PyMuPDF is required (poppler is not installed on this machine).")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCES = os.path.join(ROOT, "sources")
OUT = os.path.join(ROOT, "data", "im_ms_reference.json")

GRADES = (6, 7, 8)
GUIDE = "ImagineIM_NY_%d__TCG_NA_V2_EN_DIG.pdf"

# Section headings, matched against a page's running header. Every page of a
# section repeats it, which is what makes the ranges contiguous and means the
# page numbers never have to be hardcoded.
SCOPE = "Scope and Sequence for Grade"
REFERENCE = "NYSNGMLS for Mathematics Reference"
BY_LESSON = "NYSNGMLS Standards by Lesson"
BY_STANDARD = "NYSNGMLS Lessons by Standard"
PACING = "Pacing Guide"

# A capital letter, a space, then a lowercase letter at the start of a line is a
# kerning artifact in the text stream, not a word boundary: grade 8's Unit 4
# heading is set as "U nit 4: Linear Equations and Linear Systems". Missing that
# heading did not merely lose Unit 4 -- because a section box precedes the NEXT
# unit's heading in the reading order, all 16 of Unit 4's lessons were filed
# under Unit 3 and silently overwrote its lessons 1 to 16.
KERNED_WORD_RE = re.compile(r"^([A-Z])\s(?=[a-z])")


def unkern(line):
    return KERNED_WORD_RE.sub(r"\1", line)


UNIT_RE = re.compile(r"^Unit (\d+):\s*(.+)$")
SECTION_RE = re.compile(r"^Section ([A-H]):\s*(.+)$")
LESSON_RE = re.compile(r"^[••]?\s*Lesson (\d+):\s*(.+)$")
CODE_RE = re.compile(r"^(NY-\d\.[A-Z]{1,3}\.(?:Cluster-\d+|\d+(?:\.[a-z])?))$")
LESSON_REF_RE = re.compile(r"Unit (\d+),\s*Lesson (\d+)")
UNIT_LESSON_LINE = re.compile(r"^Unit (\d+),\s*Lesson (\d+)$")


def normalize_code(printed):
    """'NY-7.RP.2.a' -> 'NY-7.RP.2a', the form NYSED's item maps use.

    Cluster pseudo-codes are left alone: they name a cluster, not a standard,
    and no item map cites them.
    """
    if "Cluster" in printed:
        return printed
    return re.sub(r"\.(\d+)\.([a-z])$", r".\1\2", printed)


def pages_for(doc, heading):
    """Every page whose text contains this section heading, as a contiguous run."""
    hits = [i for i, p in enumerate(doc) if heading in p.get_text()]
    if not hits:
        return []
    # The contents page mentions every heading, so drop anything far from the
    # main run.
    runs, current = [], [hits[0]]
    for i in hits[1:]:
        if i - current[-1] <= 2:
            current.append(i)
        else:
            runs.append(current)
            current = [i]
    runs.append(current)
    return max(runs, key=len)


def lines_of(doc, page_indexes):
    out = []
    for i in page_indexes:
        for raw in doc[i].get_text().split("\n"):
            out.append((i + 1, raw.rstrip()))
    return out


# ------------------------------------------------------------ scope and sequence

def scope_markers(doc, grade):
    """Every unit/section/lesson marker in the Scope and Sequence, in the order a
    reader would meet them, with wrapped titles rejoined.

    Ordering cannot come from the text stream, and it cannot come from y alone.
    Grade 8's page 85 puts the Unit 9 heading at the top of the page (y=90) but
    LAST in the stream, while its page 71 puts the Unit 4 heading BELOW the box
    for Unit 3. And each box is set in two columns -- the left at x=81, the
    right at x=333 -- so sorting by y alone interleaves Section A with Section
    C and every lesson lands under the wrong section.

    So: markers are grouped by column and read down each column in turn, which
    is how the box is meant to be read.
    """
    out = []
    for page_index in pages_for(doc, SCOPE):
        page = doc[page_index]
        mid = page.rect.width / 2.0
        found = []
        for blk in page.get_text("dict")["blocks"]:
            for line in blk.get("lines", []):
                text = unkern("".join(sp["text"] for sp in line["spans"]).strip())
                if not text:
                    continue
                x0, y0 = line["bbox"][0], line["bbox"][1]
                found.append((0 if x0 < mid else 1, round(y0, 1), round(x0, 1), text))
        found.sort()

        # Rejoin a title that wrapped onto the next line of the same column.
        merged = []
        for col, y, x, text in found:
            if merged:
                pcol, py, px, ptext = merged[-1]
                is_marker = (UNIT_RE.match(ptext) or SECTION_RE.match(ptext)
                             or LESSON_RE.match(ptext))
                new_marker = (UNIT_RE.match(text) or SECTION_RE.match(text)
                              or LESSON_RE.match(text))
                if (is_marker and not new_marker and col == pcol
                        and 0 < y - py < 20 and len(text) < 60
                        and not text.endswith(".")):
                    merged[-1] = (pcol, py, px, ptext + " " + text)
                    continue
            merged.append((col, y, x, text))

        for col, y, x, text in merged:
            for kind, pattern in (("unit", UNIT_RE), ("section", SECTION_RE),
                                  ("lesson", LESSON_RE)):
                m = pattern.match(text)
                if m:
                    out.append((kind, m.group(1), m.group(2).strip()))
                    break
    return out


def parse_scope(doc, grade):
    """Units, sections and lesson titles.

    Unit boundaries are taken from the LESSON NUMBERING, not from where the
    heading sits: lessons run 1..N within a unit and restart at 1 in the next
    one, so a second Lesson 1 is a new unit. Titles come from the headings
    collected separately, which means a heading whose position is odd -- or
    whose text is kerned as "U nit 4" -- cannot misfile 16 lessons.
    """
    markers = scope_markers(doc, grade)
    titles = {num: title for kind, num, title in markers if kind == "unit"}

    units, order = {}, sorted(titles, key=int)
    idx = -1
    unit = section = None
    pending_section = None

    for kind, num, title in markers:
        if kind == "unit":
            continue                      # titles already collected
        if kind == "section":
            # Held, not filed. A unit's Section A is met BEFORE its first
            # lesson, which is what advances the unit -- so filing it straight
            # away put it in the previous unit and overwrote that unit's own
            # Section A. Grade 7 Unit 2's Section A came out as "Circumference
            # of a Circle", which belongs to Unit 3.
            pending_section = (num, title)
            continue

        # kind == "lesson"
        if num == "1" and (unit is None or "1" in units[unit]["lessons"]):
            idx += 1
            if idx >= len(order):
                sys.exit("grade %d: found a Lesson 1 after the last unit (%s). The "
                         "lesson-restart rule has broken down." % (grade, order))
            unit = order[idx]
            units.setdefault(unit, {"title": titles[unit], "sections": {},
                                    "lessons": {}})
            section = None
        if unit is None:
            continue
        if pending_section is not None:
            letter, stitle = pending_section
            units[unit]["sections"][letter] = stitle
            section = letter
            pending_section = None
        if num in units[unit]["lessons"]:
            sys.exit("grade %d: Unit %s already has a Lesson %s (%r) and the guide "
                     "offers another (%r). Filing it here would overwrite a real "
                     "title." % (grade, unit, num,
                                 units[unit]["lessons"][num]["title"], title))
        units[unit]["lessons"][num] = {
            "title": title,
            "sectionLetter": section,
            "sectionTitle": units[unit]["sections"].get(section) if section else None,
        }

    return units


# --------------------------------------------------------- standards by lesson

def parse_by_lesson(doc, grade):
    """{"7.1.1": ["NY-7.G.1"]} -- and the authoritative list of lessons."""
    out = {}
    current = None
    for _, raw in lines_of(doc, pages_for(doc, BY_LESSON)):
        line = raw.strip()
        m = UNIT_LESSON_LINE.match(line)
        if m:
            current = "%d.%s.%s" % (grade, m.group(1), m.group(2))
            out.setdefault(current, [])
            continue
        if current and line and not line.startswith(BY_LESSON):
            codes = re.findall(r"NY-\d\.[A-Z]{1,3}\.(?:Cluster-\d+|\d+(?:\.[a-z])?)", line)
            if codes:
                out[current].extend(normalize_code(c) for c in codes)
            elif not re.match(r"^(Lesson|Standards Addressed|Grade \d|\d+)$", line):
                current = None          # left the table
    return {k: sorted(set(v)) for k, v in out.items()}


# --------------------------------------------------------- lessons by standard

def parse_by_standard(doc, grade):
    """{"NY-7.EE.1": {"printed": "...", "lessons": ["7.6.18", ...]}}

    THE ALIGNED LESSONS CELL MUST BE JOINED BEFORE IT IS MATCHED. "Unit 1,
    Lesson 6" wraps as "... Unit 1," at the end of one line and "Lesson 6, ..."
    at the start of the next, so matching line by line silently drops every pair
    that straddles a break -- 40 of them, including eight of NY-7.G.1's
    thirteen Unit 1 lessons. Nothing about the result looked wrong: the standard
    still had lessons, just fewer. It surfaced only because the validator
    requires this table and Standards by Lesson to be exact inverses, and they
    are parsed from different pages by different code."""
    out, current, buf = {}, None, []

    def flush():
        if not current:
            return
        refs = LESSON_REF_RE.findall(" ".join(buf))
        out[current]["lessons"].extend("%d.%s.%s" % (grade, u, l) for u, l in refs)

    for _, raw in lines_of(doc, pages_for(doc, BY_STANDARD)):
        line = raw.strip()
        m = CODE_RE.match(line)
        if m:
            flush()
            printed = m.group(1)
            current = normalize_code(printed)
            out.setdefault(current, {"standardAsPrinted": printed, "lessons": []})
            buf = []
            continue
        if current:
            buf.append(line)
    flush()

    for v in out.values():
        v["lessons"] = sorted(set(v["lessons"]),
                              key=lambda s: [int(x) for x in s.split(".")])
    return out


# ------------------------------------------------------------------------ build

def build_grade(grade):
    path = os.path.join(SOURCES, GUIDE % grade)
    if not os.path.exists(path):
        sys.exit("missing %s" % os.path.relpath(path, ROOT))
    doc = fitz.open(path)

    units = parse_scope(doc, grade)
    by_lesson = parse_by_lesson(doc, grade)
    by_standard = parse_by_standard(doc, grade)

    # A CLUSTER CITATION IS NOT A STANDARD. Both tables cite whole clusters
    # alongside individual standards, in the guide's own literal printed form
    # ("NY-7.EE.Cluster-1"). Left in with the standards they would join to
    # nothing in data/standards.json, so they get their own maps.
    #
    # Their numbers are NOT resolved to cluster wording, deliberately. The
    # numbering is Imagine Learning's, not NYSED's, and it does not line up:
    # NY-7.SP.Cluster-2 is the second SP cluster in NGMLS but the first that
    # NYSED's chart prints, and the grade 7 guide cites NY-6.SP.Cluster-5 when
    # the grade 6 guide's own SP clusters stop at 2. Guessing which cluster is
    # meant would be inventing an alignment.
    def is_cluster(code):
        return "Cluster" in code

    lesson_standards, lesson_clusters = {}, {}
    for lesson_id, codes in by_lesson.items():
        std = [c for c in codes if not is_cluster(c)]
        clu = [c for c in codes if is_cluster(c)]
        lesson_standards[lesson_id] = std
        if clu:
            lesson_clusters[lesson_id] = clu

    standard_lessons = {c: v for c, v in by_standard.items() if not is_cluster(c)}
    cluster_lessons = {c: v["lessons"] for c, v in by_standard.items() if is_cluster(c)}

    # Standards by Lesson is authoritative for which lessons exist, so any
    # lesson it lists that the Scope and Sequence boxes missed is recorded as a
    # gap rather than silently dropped.
    titled = {"%d.%s.%s" % (grade, u, n)
              for u, spec in units.items() for n in spec["lessons"]}
    listed = set(by_lesson)

    # WHERE THE GUIDE'S TWO TABLES DISAGREE, recorded rather than reconciled.
    # Standards by Lesson and Lessons by Standard are authored separately and
    # are not exact inverses of each other. Six pairs differ in grade 7, all in
    # or beside Unit 7 -- the probability unit New York moved down from grade 8 --
    # and one of them, NY-7.NS.2d, is placed at Unit 7 Lesson 16 by one table and
    # Unit 8 Lesson 16 by the other, which is the swapped-unit hazard showing up
    # inside the guide itself. Neither table is authoritative over the other, so
    # both readings are published and the conflict is named.
    forward = {(lid, c) for lid, cs in lesson_standards.items() for c in cs}
    forward |= {(lid, c) for lid, cs in lesson_clusters.items() for c in cs}
    back = {(lid, c) for c, v in standard_lessons.items() for lid in v["lessons"]}
    back |= {(lid, c) for c, lids in cluster_lessons.items() for lid in lids}
    disagreements = (
        [{"lesson": lid, "standard": c, "citedBy": "Standards by Lesson only"}
         for lid, c in sorted(forward - back)]
        + [{"lesson": lid, "standard": c, "citedBy": "Lessons by Standard only"}
           for lid, c in sorted(back - forward)])

    return {
        "numbering": "newYork",
        "source": os.path.relpath(path, ROOT),
        "units": dict(sorted(units.items(), key=lambda kv: int(kv[0]))),
        "standardToLessons": dict(sorted(standard_lessons.items())),
        "lessonToStandards": dict(sorted(lesson_standards.items(),
                                         key=lambda kv: [int(x) for x in kv[0].split(".")])),
        "clusterToLessons": dict(sorted(cluster_lessons.items())),
        "lessonToClusters": dict(sorted(lesson_clusters.items(),
                                        key=lambda kv: [int(x) for x in kv[0].split(".")])),
        "tableDisagreements": disagreements,
        # LESSONS THE GUIDE CITES NO STANDARD FOR, recorded so an empty cell on
        # the site reads as "the guide lists none" rather than "we failed to
        # extract it". Almost all are a unit's Lesson 1 -- IM opens a unit with
        # an invitation to the mathematics that deliberately addresses no
        # standard, and the guide's Standards Addressed cell for it is blank.
        "lessonsWithoutStandards": sorted(
            (lid for lid in by_lesson
             if not lesson_standards.get(lid) and not lesson_clusters.get(lid)),
            key=lambda s: [int(x) for x in s.split(".")]),
        "counts": {
            "units": len(units),
            "sections": sum(len(u["sections"]) for u in units.values()),
            "lessonsTitled": len(titled),
            "lessonsListed": len(listed),
            "lessonsPerUnit": {u: len(spec["lessons"])
                               for u, spec in sorted(units.items(), key=lambda kv: int(kv[0]))},
            "standards": len(standard_lessons),
            "clustersCited": len(cluster_lessons),
            "tableDisagreements": len(disagreements),
            "lessonsWithoutStandards": len(
                [lid for lid in by_lesson
                 if not lesson_standards.get(lid) and not lesson_clusters.get(lid)]),
        },
        "lessonsListedWithoutTitle": sorted(listed - titled,
                                            key=lambda s: [int(x) for x in s.split(".")]),
        "lessonsTitledNotListed": sorted(titled - listed,
                                         key=lambda s: [int(x) for x in s.split(".")]),
    }


def main():
    ap = argparse.ArgumentParser(description="Build the IM 6-8 curriculum index.")
    ap.add_argument("--grade", type=int, choices=GRADES)
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    grades = [args.grade] if args.grade else list(GRADES)
    payload = {
        "meta": {
            "schemaVersion": "1.0",
            "generatedBy": "tools/extract_im_ms_lessons.py",
            "generated": datetime.date.today().isoformat(),
            "edition": "Imagine IM New York, 6-8",
            "note": "GENERATED from the Teacher Course Guides. Re-run the extractor rather "
                    "than hand-editing.",
            "lessonCodeFormat": "<grade>.<unit>.<lesson>, e.g. 7.6.18 -- the same shape the "
                                "NYCPS workbooks use.",
            "codeShape": "Standards are stored in NYSED's own form (NY-7.RP.2a). The guides "
                         "print them with a dot before the sub-letter (NY-7.RP.2.a); the "
                         "printed form is kept in standardAsPrinted. Nothing joins to "
                         "data/items.json without that normalisation.",
            "unitNumberingByTable": {
                "TCG Scope and Sequence": "newYork",
                "TCG Standards by Lesson": "newYork",
                "TCG Lessons by Standard": "newYork",
                "NYCPS pacing workbook, Pacing at a Glance and Unit N sheets": "newYork",
                "NYCPS pacing workbook, NGMLS Readiness sheet": "national",
                "NYCPS NYS Exam IM Alignment sheets (sources/nycps/)": "national",
            },
            "hazards": [
                "Grades 7 and 8 SWAP Units 7 and 8 between the New York and national "
                "editions. Grade 7's Unit 7 is Probability and Sampling and its Unit 8 is "
                "Angles, Triangles, and Prisms; nationally they are reversed. Grade 6 is not "
                "swapped.",
                "The NYCPS workbooks use national numbering on their NGMLS Readiness sheet "
                "and New York numbering on sibling sheets in the same file.",
                "Grade 8's own guide contradicts itself on Unit 6: Standards by Lesson lists "
                "11 lessons while the Scope and Sequence box, the language table and the "
                "pacing guide all stop at 9, because NY-8.SP.4 (categorical data) was removed "
                "under NGMLS and that table was not regenerated.",
                "The guide's two alignment tables are not exact inverses. Standards by "
                "Lesson and Lessons by Standard disagree on six pairs in grade 7, all in or "
                "beside Unit 7; NY-7.NS.2d is placed at Unit 7 Lesson 16 by one and Unit 8 "
                "Lesson 16 by the other. Both readings are kept, in tableDisagreements.",
                "Cluster citations ('NY-7.EE.Cluster-1') are the guide's own literal form and "
                "live in clusterToLessons / lessonToClusters, never mixed in with standards. "
                "Their numbers are Imagine Learning's and are NOT resolvable to NYSED's "
                "cluster order: NY-6.SP.Cluster-5 is cited by the grade 7 guide although the "
                "grade 6 guide's own SP clusters stop at 2.",
                "Resolve a lesson BY TITLE, never by number. This is the rule RegentsAlign "
                "lost a week to.",
                "Match titles CASE-INSENSITIVELY. The grade 6 guide prints its Unit 9 as "
                "'Putting it All Together' in the Scope and Sequence box and 'Putting It All "
                "Together' in the pacing table, so an exact-string title match fails against "
                "the guide's own other table. Grades 7 and 8 use only the capitalised form.",
            ],
        },
        "grades": {},
    }
    for g in grades:
        payload["grades"][str(g)] = build_grade(g)

    if args.stdout:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return

    with open(OUT, "w") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    for g in grades:
        c = payload["grades"][str(g)]["counts"]
        print("  grade %d: %d units, %d sections, %d lessons titled, %d listed, "
              "%d standards, %d clusters" % (g, c["units"], c["sections"],
                                             c["lessonsTitled"], c["lessonsListed"],
                                             c["standards"], c["clustersCited"]))
        if c["tableDisagreements"]:
            print("    %d pair(s) where the guide's two tables disagree"
                  % c["tableDisagreements"])
        gaps = payload["grades"][str(g)]["lessonsListedWithoutTitle"]
        extra = payload["grades"][str(g)]["lessonsTitledNotListed"]
        if gaps:
            print("    %d listed lesson(s) have no title: %s"
                  % (len(gaps), ", ".join(gaps[:8])))
        if extra:
            print("    %d titled lesson(s) are not in Standards by Lesson: %s"
                  % (len(extra), ", ".join(extra[:8])))


if __name__ == "__main__":
    main()
