#!/usr/bin/env python3
"""How well does Imagine Learning's own standard-to-lesson table predict where a
released item is actually taught?

NYCPS published its own item-by-item IM alignment for 2023-2025 (sources/nycps/).
For grades 6 and 7 its Curriculum Notes name a specific lesson AND quote a
parallel activity -- 84 of 87 grade 6 rows and 93 of 93 grade 7 rows. That is an
independent expert reading of the same items, authored without reference to this
project, which makes it the only external check available on a curriculum
placement.

This script joins the two and reports agreement. It writes nothing. Run it
before trusting any lesson-level alignment, and again after, to see whether the
judgement pass moved toward the independent source or away from it.

RESOLVE BY TITLE, NEVER BY NUMBER. NYCPS records NATIONAL unit numbers; this
project uses the Imagine IM New York edition, and grades 7 and 8 swap Units 7
and 8 between them. Every citation here is resolved through the lesson title, so
the swap is handled by construction rather than by a correction table -- and the
ten grade 7 rows whose resolved unit differs from the cited number are the swap
showing up as evidence that the rule works.
"""
import collections
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "data", "im_ms_reference.json")
ITEMS = os.path.join(ROOT, "data", "items.json")
NYCPS = os.path.join(ROOT, "sources", "nycps")

CITE = re.compile(r"Grade\s+(\d),\s*Unit\s+(\d+),\s*Lesson\s+(\d+)\s*:?\s*[\"“]?([^\"”\n]*)")


def norm(t):
    t = (t or "").lower().replace("’", "'").replace("‘", "'")
    t = t.replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def candidates(ref, grade, standard):
    """The lessons Imagine Learning's Lessons by Standard table names, with the
    parent-code fallback items need (an item cites NY-7.EE.4a; the table may
    only carry NY-7.EE.4)."""
    s2l = ref[grade]["standardToLessons"]
    entry = s2l.get(standard)
    if not entry:
        for code, val in s2l.items():
            if standard.startswith(code) or code.startswith(standard):
                entry = val
                break
    return entry["lessons"] if entry else []


def main():
    ref = json.load(open(REF))["grades"]
    doc = json.load(open(ITEMS))
    items = doc["items"] if "items" in doc else doc
    by_key = {(str(i["grade"]), i["year"], i["item"]): i for i in items}

    titles = {}
    for g, spec in ref.items():
        idx = collections.defaultdict(list)
        for u, unit in spec["units"].items():
            for n, lesson in unit["lessons"].items():
                idx[norm(lesson["title"])].append("%s.%s.%s" % (g, u, n))
        titles[g] = idx

    stats = collections.Counter()
    swaps, outside_unit, unresolved = [], [], []

    for g in ("6", "7", "8"):
        path = os.path.join(NYCPS, "nycps-exam-im-alignment-g%s.csv" % g)
        if not os.path.exists(path):
            continue
        for row in csv.DictReader(open(path)):
            notes = next((v for k, v in row.items() if k and "Notes" in k), "") or ""
            stats["rows read"] += 1
            m = CITE.search(notes)
            if not m:
                stats["row cites no lesson"] += 1
                continue
            year = int(re.sub(r"\D", "", row["Exam"]))
            item = by_key.get((g, year, int(row["Q#"])))
            if not item:
                stats["row matches no item"] += 1
                continue
            cited_grade, cited_unit, title = m.group(1), m.group(2), m.group(4).strip()
            if cited_grade not in titles:
                stats["cites a grade outside the 6-8 index"] += 1
                continue
            hits = titles[cited_grade].get(norm(title), [])
            if len(hits) != 1:
                stats["title not uniquely resolvable"] += 1
                unresolved.append("%s: %r -> %d matches" % (item["id"], title, len(hits)))
                continue
            resolved = hits[0]
            stats["citation resolved by title"] += 1
            if resolved.split(".")[1] != cited_unit:
                swaps.append("%s: cited %s.%s.%s, resolved %s (%s)"
                             % (item["id"], cited_grade, cited_unit, m.group(3),
                                resolved, title))
            if cited_grade != g:
                stats["cites a prior grade (not comparable)"] += 1
                continue
            cand = candidates(ref, g, item["standard"])
            if not cand:
                stats["standard absent from the table entirely"] += 1
                continue
            stats["comparable"] += 1
            if resolved in cand:
                stats["  lesson INSIDE the candidate set"] += 1
            elif resolved.split(".")[1] in {c.split(".")[1] for c in cand}:
                stats["  lesson outside the set but inside a candidate UNIT"] += 1
            else:
                stats["  lesson in a unit the candidates never name"] += 1
                outside_unit.append("%s %s: NYCPS %s %r, candidates %s"
                                    % (item["id"], item["standard"], resolved,
                                       title, sorted(cand)))

    width = max(len(k) for k in stats)
    for k, v in stats.most_common():
        print("%5d  %s" % (v, k.ljust(width)))

    comparable = stats["comparable"]
    if comparable:
        inside = stats["  lesson INSIDE the candidate set"]
        unit_ok = inside + stats["  lesson outside the set but inside a candidate UNIT"]
        print("\nlesson-level agreement: %d of %d (%.1f%%)"
              % (inside, comparable, 100.0 * inside / comparable))
        print("unit-level agreement:   %d of %d (%.1f%%)"
              % (unit_ok, comparable, 100.0 * unit_ok / comparable))

    print("\nunit number differs from the cited number (the edition swap, "
          "resolved by title): %d" % len(swaps))
    for s in swaps:
        print("   %s" % s)
    print("\nNYCPS names a unit the candidate set never mentions: %d" % len(outside_unit))
    for s in outside_unit:
        print("   %s" % s)
    if unresolved:
        print("\ntitles that did not resolve: %d" % len(unresolved))
        for s in unresolved:
            print("   %s" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
