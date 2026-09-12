#!/usr/bin/env python3
"""Compare an independent second pass against what data/alignment.json says.

WHY THIS EXISTS
tools/measure_alignment_agreement.py compares this project's placements against
NYCPS's independent citations, but it can only speak for grades 6 and 7 in
2023-2025: grade 8's NYCPS sheet carries no lesson citations and no sheet covers
2026. That leaves every grade 8 item and every 2026 item with no external
opinion at all.

The project's own convention supplies the substitute:

    "A second pass RE-DERIVES the placement from the lessons rather than
     reviewing the first pass's prose. Reviewing prose finds typos;
     re-deriving finds wrong answers."

This turns that into a number, and it is the house rule -- cross-implementation
agreement is tested, not assumed -- applied to judgement instead of to parsing.

THE PROTOCOL, WHICH HAS TO BE FOLLOWED OR THE NUMBER MEANS NOTHING
A second pass reads the items and the lesson index and NOT data/alignment.json,
and writes its answers to provenance/second_pass/<name>.json. Nothing in data/
is touched, so the first pass cannot be contaminated by the second or the second
by the first. A disagreement is then settled by re-reading the lesson -- not by
the first pass winning because it got there first.

Usage:
    python3 tools/measure_second_pass.py            # every file in second_pass/
    python3 tools/measure_second_pass.py ns_g1      # one of them
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASSDIR = os.path.join(ROOT, "provenance", "second_pass")


def norm(t):
    t = (t or "").lower().replace("’", "'").replace("‘", "'")
    t = t.replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def grade_of(entry, item_id):
    m = re.search(r"Grade\s+([678])", entry.get("course") or "")
    return m.group(1) if m else (item_id[1] if item_id.startswith("g") else None)


def main():
    align = json.load(open(os.path.join(ROOT, "data", "alignment.json")))["byItem"]
    ref = json.load(open(os.path.join(ROOT, "data", "im_ms_reference.json")))["grades"]

    files = sorted(glob.glob(os.path.join(PASSDIR, "*.json")))
    if len(sys.argv) > 1:
        files = [f for f in files
                 if os.path.splitext(os.path.basename(f))[0] in sys.argv[1:]]
    if not files:
        print("no second-pass files in provenance/second_pass/")
        return 0

    same_lesson = same_unit = diff_unit = missing = 0
    differences, unplaceable = [], []

    for path in files:
        doc = json.load(open(path))
        name = os.path.splitext(os.path.basename(path))[0]
        print("\n%s  -- %s" % (name, doc.get("scope", "")))
        n = 0
        for item_id, second in sorted(doc.get("items", {}).items()):
            first = align.get(item_id)
            if not first:
                missing += 1
                unplaceable.append("%s: no entry in data/alignment.json" % item_id)
                continue
            n += 1
            fg, sg = grade_of(first, item_id), grade_of(second, item_id)
            fu, su = first.get("unit"), second.get("unit")
            fl, sl = first.get("primaryLesson"), second.get("primaryLesson")
            if (fg, fu) != (sg, su):
                diff_unit += 1
                differences.append("%s: ours %s.%s.%s, second pass %s.%s.%s"
                                   " <-- DIFFERENT UNIT"
                                   % (item_id, fg, fu, fl, sg, su, sl))
            elif fl == sl:
                same_lesson += 1
            else:
                same_unit += 1
                # Name both lessons: a bare pair of numbers hides whether the
                # two passes landed a lesson apart or a section apart.
                def title(g, u, l):
                    try:
                        return ref[str(g)]["units"][str(u)]["lessons"][str(l)]["title"]
                    except (KeyError, TypeError):
                        return "?"
                differences.append(
                    "%s: ours %s.%s.%s %r, second pass %s.%s.%s %r"
                    % (item_id, fg, fu, fl, title(fg, fu, fl),
                       sg, su, sl, title(sg, su, sl)))
        print("   %d items compared" % n)

    total = same_lesson + same_unit + diff_unit
    print("\n" + "-" * 68)
    print("compared: %d" % total)
    if not total:
        return 0
    print()
    print("   %4d   same primary lesson" % same_lesson)
    print("   %4d   same unit, different lesson" % same_unit)
    print("   %4d   different unit" % diff_unit)
    print()
    print("two independent readings chose the same lesson: %d of %d (%.1f%%)"
          % (same_lesson, total, 100.0 * same_lesson / total))
    print()
    # This is not a score to maximise. A second pass that merely agreed would
    # prove only that both passes share a bias; what the number is for is
    # making sure every disagreement gets LOOKED AT rather than accumulating.
    print("Every line below is a placement two readings of the same lesson text")
    print("disagreed on. Settle each by re-reading the lesson, not by seniority.")
    print()
    for d in differences:
        print("   " + d)
    for u in unplaceable:
        print("   " + u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
