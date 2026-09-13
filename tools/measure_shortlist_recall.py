#!/usr/bin/env python3
"""Does the shortlist contain the lesson an independent reader actually chose?

tools/shortlist_lessons.py exists to make a reading tractable. The only way it
can do harm is by leaving the right lesson out, because then no amount of care
in the reading can recover it. So the property to measure is RECALL against a
source that was written without reference to this project: NYCPS's per-item
citations for 2023-2025, resolved by title.

Precision is deliberately not measured. A shortlist of eight that usually
contains the answer is doing its job; picking between the eight is the reading's
job, not this file's.
"""
import collections
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import shortlist_lessons as S

NYCPS = os.path.join(ROOT, "sources", "nycps")
# "Lessons?" with the optional s: three grade 6 rows read "Unit 7, Lessons 8"
# for a single lesson. The singular-only pattern silently dropped them, and a
# citation that does not parse is indistinguishable from one that does not
# exist -- it just makes the sheet look 3 rows thinner than it is.
CITE = re.compile(r"Grade\s+(\d),\s*Unit\s+(\d+),\s*Lessons?\s+(\d+)\s*:?\s*[\"“]?([^\"”\n]*)")
KS = (1, 3, 5, 8, 12, 20)


def norm(t):
    t = (t or "").lower().replace("’", "'").replace("‘", "'")
    t = t.replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def main():
    idx = S.load()
    doc = json.load(open(os.path.join(ROOT, "data", "items.json")))
    items = doc["items"] if "items" in doc else doc
    content = json.load(open(os.path.join(ROOT, "data", "content.json")))["items"]
    by_key = {(str(i["grade"]), i["year"], i["item"]): i for i in items}

    titles = {}
    for g, spec in idx.ref.items():
        d = collections.defaultdict(list)
        for u, unit in spec["units"].items():
            for n, l in unit["lessons"].items():
                d[norm(l["title"])].append("%s.%s.%s" % (g, u, n))
        titles[g] = d

    hits = collections.Counter()
    total = 0
    misses = []
    sizes = []
    kmax = max(KS)
    for g in ("6", "7", "8"):
        path = os.path.join(NYCPS, "nycps-exam-im-alignment-g%s.csv" % g)
        if not os.path.exists(path):
            continue
        for row in csv.DictReader(open(path)):
            notes = next((v for k, v in row.items() if k and "Notes" in k), "") or ""
            m = CITE.search(notes)
            if not m:
                continue
            item = by_key.get((g, int(re.sub(r"\D", "", row["Exam"])), int(row["Q#"])))
            if not item or m.group(1) != g:
                continue
            hit = titles[g].get(norm(m.group(4).strip()), [])
            if len(hit) != 1:
                continue
            want = hit[0]
            text = S.item_text(item, content)
            if not text.strip():
                continue
            total += 1
            ranked = [r["lesson"] for r in
                      idx.rank(g, item["standard"], text, k=kmax)]
            pos = ranked.index(want) + 1 if want in ranked else None
            for k in KS:
                if pos and pos <= k:
                    hits[k] += 1
            t = S.tiers(idx, g, item["standard"], text, k=12)
            if want in [r["lesson"] for r in t["tier1"]] or want in t["tier2"]:
                hits["tier1+tier2"] += 1
                sizes.append(len(t["tier1"]) + len(t["tier2"]))
            if not pos:
                misses.append("%s %s: wanted %s %r"
                              % (item["id"], item["standard"], want,
                                 idx.docs[want]["rec"].get("title")))

    print("NYCPS citations with item text available: %d\n" % total)
    for k in KS:
        bar = "#" * int(40.0 * hits[k] / max(total, 1))
        print("  recall@%-3d %4d / %-4d  %5.1f%%  %s"
              % (k, hits[k], total, 100.0 * hits[k] / max(total, 1), bar))
    if total:
        print("\n  tier 1 + tier 2  %4d / %-4d  %5.1f%%   (median %d lessons to read)"
              % (hits["tier1+tier2"], total,
                 100.0 * hits["tier1+tier2"] / total,
                 sorted(sizes)[len(sizes) // 2] if sizes else 0))
    print("\nnever retrieved at all: %d" % len(misses))
    for s in misses[:20]:
        print("   %s" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
