#!/usr/bin/env python3
"""Compare this project's own alignment against NYCPS's independent citations.

tools/measure_nycps_agreement.py asks whether the PUBLISHER'S TABLE predicts
where an item is taught. This asks the harder question: whether the judgements
actually written into data/alignment.json land where an independent expert put
them.

Run it after every batch of entries. Agreement is not the goal -- NYCPS's own
PROVENANCE.md calls its notes "suggestive, not authoritative", and a disagreement
may well be this project finding a better lesson, which is the entire reason for
reading the task statements. What matters is that disagreements are SEEN and
decided, rather than accumulating unnoticed. A rate that drifts downward as more
entries are written is the signal to stop and re-read.

Reads all three sheets, but only grades 6 and 7 can ever produce a comparison:
grade 8's sheet carries a Curriculum Note on five of its 93 rows and all five
read "***in 7th grade", so there is no grade 8 lesson to compare against. Until
grade 6 is aligned, every number this prints is grade 7's alone -- the line the
docstring used to carry, that it "covers grades 6 and 7", described the files it
opened rather than the items it scored.

No sheet covers 2026, so a quarter of the corpus has no outside reading at all.

For grade 8 use tools/measure_g8_section_agreement.py, which compares against the
SECTION each row names -- coarser than a lesson, and the only outside signal that
grade might get.
"""
import collections
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NYCPS = os.path.join(ROOT, "sources", "nycps")
CITE = re.compile(r"Grade\s+(\d),\s*Unit\s+(\d+),\s*Lesson\s+(\d+)\s*:?\s*[\"“]?([^\"”\n]*)")


def norm(t):
    t = (t or "").lower().replace("’", "'").replace("‘", "'")
    t = t.replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def main():
    ref = json.load(open(os.path.join(ROOT, "data", "im_ms_reference.json")))["grades"]
    doc = json.load(open(os.path.join(ROOT, "data", "items.json")))
    items = doc["items"] if "items" in doc else doc
    align = json.load(open(os.path.join(ROOT, "data", "alignment.json")))["byItem"]
    by_key = {(str(i["grade"]), i["year"], i["item"]): i for i in items}

    titles = {}
    for g, spec in ref.items():
        idx = collections.defaultdict(list)
        for u, unit in spec["units"].items():
            for n, l in unit["lessons"].items():
                idx[norm(l["title"])].append("%s.%s.%s" % (g, u, n))
        titles[g] = idx

    stats = collections.Counter()
    differ = []
    for g in ("6", "7", "8"):
        path = os.path.join(NYCPS, "nycps-exam-im-alignment-g%s.csv" % g)
        if not os.path.exists(path):
            continue
        for row in csv.DictReader(open(path)):
            notes = next((v for k, v in row.items() if k and "Notes" in k), "") or ""
            m = CITE.search(notes)
            if not m or m.group(1) != g:
                continue
            item = by_key.get((g, int(re.sub(r"\D", "", row["Exam"])), int(row["Q#"])))
            if not item or item["id"] not in align:
                continue
            hit = titles[g].get(norm(m.group(4).strip()), [])
            if len(hit) != 1:
                continue
            want = hit[0]
            entry = align[item["id"]]
            # An entry that deliberately makes NO lesson claim cannot agree or
            # disagree about a lesson, and counting it as a miss punishes the
            # honesty. The six grade 7 items whose PDF page is undetermined are
            # in this state: no stem was ever extracted, so there is nothing to
            # judge a lesson against and the entry stops at the unit. Before
            # this they scored as "7.5.None" against NYCPS and dragged the rate
            # from 72.8% to 67.8% without a single placement having changed.
            if entry.get("primaryLesson") is None:
                stats["no lesson claimed (not scored)"] += 1
                continue
            cg = re.search(r"Grade\s+([678])", entry.get("course") or "")
            ours = "%s.%s.%s" % (cg.group(1) if cg else g, entry["unit"],
                                 entry["primaryLesson"])
            cited = {"%s.%s.%s" % (cg.group(1) if cg else g, entry["unit"], e["lesson"])
                     for e in entry.get("evidence") or []}
            stats["compared"] += 1
            if ours == want:
                stats["  same primary lesson"] += 1
            elif want in cited:
                stats["  NYCPS's lesson is among our evidence, not our primary"] += 1
                differ.append("%s: ours %s, NYCPS %s (cited as evidence)"
                              % (item["id"], ours, want))
            elif ours.split(".")[1] == want.split(".")[1]:
                stats["  same unit, different lesson"] += 1
                differ.append("%s %s: ours %s, NYCPS %s"
                              % (item["id"], item["standard"], ours, want))
            else:
                stats["  different unit"] += 1
                differ.append("%s %s: ours %s, NYCPS %s  <-- DIFFERENT UNIT"
                              % (item["id"], item["standard"], ours, want))

    print("entries written: %d    comparable against NYCPS: %d\n"
          % (len(align), stats["compared"]))
    for k, v in stats.most_common():
        if k not in ("compared", "no lesson claimed (not scored)"):
            print("%5d  %s" % (v, k))
    if stats["no lesson claimed (not scored)"]:
        print("\n%5d  items NYCPS cites that we deliberately leave at the unit,"
              " excluded from the rate" % stats["no lesson claimed (not scored)"])
    if stats["compared"]:
        agree = (stats["  same primary lesson"]
                 + stats["  NYCPS's lesson is among our evidence, not our primary"])
        print("\nour placement includes NYCPS's lesson: %d of %d (%.1f%%)"
              % (agree, stats["compared"], 100.0 * agree / stats["compared"]))
    if differ:
        print("\ndifferences to decide:")
        for d in differ:
            print("   %s" % d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
