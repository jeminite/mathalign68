#!/usr/bin/env python3
"""Grade 8's only outside opinion: does our lesson sit in the SECTION NYCPS names?

`measure_nycps_agreement.py` compares lesson citations, which grade 8 does not
have. Of the 93 rows in NYCPS's grade 8 sheet only five carry a Curriculum Note
and all five read "***in 7th grade", so the lesson-level check that grades 6 and
7 get is simply unavailable here -- and grade 8 would otherwise be published on
this project's own reading alone.

But every one of those 93 rows names a SECTION: "5.D: Cylinders and Cones",
"8.B: Pythagorean Theorem". That is coarser than a lesson and finer than a unit,
it was authored without reference to this project, and a grade 8 unit averages
four sections, so it is a real check rather than a formality. This script asks
of each aligned item: is the lesson we chose inside the section NYCPS named?

RESOLVE BY TITLE, NEVER BY NUMBER, for the usual reason and one more. NYCPS
records NATIONAL unit numbers and this project uses the New York edition, which
swaps Units 7 and 8 in both grades 7 and 8 -- so a third of these rows print a
unit number this project does not use. Resolving the section TITLE against the
index handles the swap by construction, and the rows where the resolved number
differs from the printed one are the swap showing itself.

The titles are typed by hand and are misspelt often enough that exact matching
throws away a fifth of the sheet ("Pythaogrean Thoerem", "Asociations in
Numerical Data", "Equivilent Equations", "Linear Relatinships"). Matching is
therefore fuzzy, with the winning score printed for every row so a bad match is
visible rather than quietly counted, and a row whose two best candidates are
within a hair of each other is reported unresolved rather than guessed.

Nine rows carry a grade 7 section, because a grade 8 test can examine a grade 7
standard; those resolve against the grade 7 index, which is the home-grade rule
the alignment itself follows.

Writes nothing.
"""
import collections
import csv
import difflib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETAIL = os.path.join(ROOT, "data", "im_ms_lessons_detail.json")
REF = os.path.join(ROOT, "data", "im_ms_reference.json")
ITEMS = os.path.join(ROOT, "data", "items.json")
ALIGN = os.path.join(ROOT, "data", "alignment.json")
NYCPS = os.path.join(ROOT, "sources", "nycps", "nycps-exam-im-alignment-g8.csv")

# "5.D: Cylinders and Cones", "6.B :Associations in Numerical Data",
# "8.3: Representing Linear Relationships" -- the letter is sometimes a digit.
SECTION_RE = re.compile(r"^\s*(\d+)\s*\.\s*([A-Z0-9])\s*:?\s*(.*?)\s*$")

# Two rows name two sections joined by "&". Both are recorded and the item
# counts as agreeing if our lesson is in either, because the row is telling us
# the author could not choose between them either.
SPLIT_RE = re.compile(r"\s+&\s+")

# Below this the best match is not a match. The worst TRUE match on this sheet
# is "Rational And Irrational Numbers" against "Decimal Representation of
# Rational and Irrational Numbers" at 0.74; the best FALSE one is "Slicing
# Solids" against "Solid Geometry" at 0.48, where NYCPS used the national
# section name and the New York edition renamed it.
FLOOR = 0.62
# A win by less than this over the runner-up is not a win: the sheet is typed by
# hand and a near-tie means the title cannot carry the decision.
MARGIN = 0.06
# Words that carry no identity. "Linear Equations" and "Linear Relationships"
# must stay distinguishable, so only true function words are dropped.
STOP = {"a", "an", "and", "in", "of", "the", "to", "with", "for", "on", "let",
        "s", "it", "work", "put", "this", "that"}


def norm(t):
    t = (t or "").lower().replace("’", "'").replace("‘", "'")
    t = t.replace("–", "-").replace("—", "-").replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def sections(detail):
    """(grade, unit, letter) -> {title, lessons} for grades 7 and 8."""
    out = {}
    for g in ("7", "8"):
        for u, ud in detail["grades"][g]["units"].items():
            for n, rec in ud["lessons"].items():
                key = (g, u, (rec.get("sectionLetter") or "?"))
                s = out.setdefault(key, {"title": rec.get("sectionTitle") or "",
                                         "lessons": set()})
                s["lessons"].add(int(n))
    return out


def tokens(t):
    return [w for w in norm(t).split() if w not in STOP]


def covers(a, b):
    """Fraction of a's words that appear in b, allowing a misspelling."""
    if not a:
        return 0.0
    hit = sum(1 for w in a
              if any(difflib.SequenceMatcher(None, w, v).ratio() >= 0.8 for v in b))
    return hit / float(len(a))


def score(title, candidate):
    """How well a hand-typed section name identifies an indexed section.

    Character similarity alone gets this wrong in both directions, which is why
    it is not used alone: "Rational And Irrational Numbers" is a closer string
    to "Adding and Subtracting Rational Numbers" than to its real match, and
    "Linear Relatinships" is closer to "Angle Relationships" than to "Representing
    Linear Relationships". Both are fixed by asking which WORDS the two names
    share -- in both directions, so that a title cannot win by being a prefix of
    a longer one ("Exponent Rules" must beat "More Exponent Rules") -- and
    keeping character similarity only as a tiebreak, where its tolerance for
    misspelling does the work it is good at."""
    a, b = tokens(title), tokens(candidate)
    fwd, rev = covers(a, b), covers(b, a)
    overlap = (2 * fwd * rev / (fwd + rev)) if fwd + rev else 0.0
    return 0.75 * overlap + 0.25 * difflib.SequenceMatcher(
        None, norm(title), norm(candidate)).ratio()


def resolve(title, cat):
    """Best section whose title matches, with its score and the runner-up."""
    if not norm(title):
        return None, 0.0, 0.0
    scored = sorted(((score(title, v["title"]), k) for k, v in cat.items()),
                    reverse=True)
    best, second = scored[0], (scored[1] if len(scored) > 1 else (0.0, None))
    return best[1], best[0], second[0]


def main():
    detail = json.load(open(DETAIL))
    ref = json.load(open(REF))["grades"]
    items = json.load(open(ITEMS))["items"]
    by_item = json.load(open(ALIGN))["byItem"]

    by_key = {(i["year"], i["item"]): i for i in items if i["grade"] == 8}
    placed = {}
    for item_id, e in by_item.items():
        # The course string carries the home grade: a grade 8 item on a grade 7
        # standard is aligned in the grade 7 curriculum, and comparing it
        # against a grade 8 section would score the home-grade rule as an error.
        m = re.search(r"Grade\s+(\d)", e.get("course") or "")
        if m and e.get("unit") and e.get("primaryLesson"):
            placed[item_id] = (m.group(1), str(e["unit"]), int(e["primaryLesson"]))

    cat = sections(detail)
    unit_titles = {(g, u): ud.get("title")
                   for g in ("7", "8") for u, ud in ref[g]["units"].items()}

    stats = collections.Counter()
    inside, outside, swaps, unresolved, unplaced = [], [], [], [], []

    for row in csv.DictReader(open(NYCPS)):
        stats["rows read"] += 1
        year = int(re.sub(r"\D", "", row["Exam"]))
        item = by_key.get((year, int(row["Q#"])))
        if not item:
            stats["row matches no item"] += 1
            continue

        cited, misses = [], []
        for piece in SPLIT_RE.split(row["Section"] or ""):
            m = SECTION_RE.match(piece)
            title = m.group(3) if m else piece.strip()
            num = m.group(1) if m else None
            key, sc, runner = resolve(title, cat)
            if key and sc >= FLOOR and sc - runner >= MARGIN:
                cited.append((key, sc, num, title))
            else:
                # Printed with its near-miss rather than as a bare failure. A
                # threshold tuned until every row passes is measuring itself;
                # showing what was rejected and by how much lets a reader judge
                # the two that fall short without the tool deciding for them.
                misses.append("%r (best %s %r at %.2f)"
                              % (title, key, cat[key]["title"] if key else None, sc))
        if not cited:
            stats["section did not resolve"] += 1
            unresolved.append("%s: %s" % (item["id"], "; ".join(misses)))
            continue
        stats["section resolved by title"] += 1

        for (g, u, letter), score, num, title in cited:
            if num and num != u:
                swaps.append("%s: printed %s.%s %r -> grade %s Unit %s %s (%s)"
                             % (item["id"], num, letter, title, g, u, letter,
                                unit_titles.get((g, u))))

        ours = placed.get(item["id"])
        if not ours:
            stats["item not aligned yet"] += 1
            unplaced.append(item["id"])
            continue

        stats["comparable"] += 1
        hit = any(ours[0] == g and ours[1] == u and ours[2] in cat[(g, u, l)]["lessons"]
                  for (g, u, l), _, _, _ in cited)
        unit_hit = any(ours[0] == g and ours[1] == u for (g, u, l), _, _, _ in cited)
        names = " or ".join("%s.%s%s %s" % (g, u, l, cat[(g, u, l)]["title"])
                            for (g, u, l), _, _, _ in cited)
        line = "%s %s: ours %s.%s.%s, NYCPS %s" % (item["id"], item["standard"],
                                                   ours[0], ours[1], ours[2], names)
        if hit:
            stats["  our lesson is INSIDE the cited section"] += 1
            inside.append(line)
        elif unit_hit:
            stats["  same unit, different section"] += 1
            outside.append(line)
        else:
            stats["  different unit"] += 1
            outside.append(line)

    width = max(len(k) for k in stats)
    for k, v in stats.most_common():
        print("%5d  %s" % (v, k.ljust(width)))

    n = stats["comparable"]
    if n:
        sect = stats["  our lesson is INSIDE the cited section"]
        unit = sect + stats["  same unit, different section"]
        print("\nsection-level agreement: %d of %d (%.1f%%)" % (sect, n, 100.0 * sect / n))
        print("unit-level agreement:    %d of %d (%.1f%%)" % (unit, n, 100.0 * unit / n))

    print("\nprinted unit number differs from the resolved one (the edition swap): %d"
          % len(swaps))
    for s in swaps:
        print("   %s" % s)
    print("\nwhere we differ from NYCPS: %d" % len(outside))
    for s in outside:
        print("   %s" % s)
    if unresolved:
        print("\nsections that did not resolve: %d" % len(unresolved))
        for s in unresolved:
            print("   %s" % s)
    if unplaced:
        print("\nrows whose item is not aligned yet: %d (%s)"
              % (len(unplaced), ", ".join(sorted(unplaced)[:12])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
