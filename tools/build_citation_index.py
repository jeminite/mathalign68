#!/usr/bin/env python3
"""A portable record of what every published citation was verified against.

THE PROBLEM THIS SOLVES. Three of the checks that make data/alignment.json
trustworthy -- that every cited activity exists, that its page is the page the
index gives it, and that every quote really appears in that activity -- resolve
through data/im_ms_lessons_detail.json. That file reproduces Imagine Learning's
Student Task Statements verbatim, so it is gitignored and will never be
committed. The consequence was that on any machine but the author's those three
checks skipped, and a collaborator who cloned the repository got a preflight that
passed without having verified a single one of the 1,153 published citations.

WHAT THIS FILE CONTAINS, AND WHY IT DISCLOSES NOTHING NEW. For each of the 475
distinct activities that a published citation names: the grade, unit and lesson
it sits in, the lesson's title, the activity's name and its page. Every one of
those fields is already on the public site, on the question card of any item that
cites it. Plus, per citation, a digest over (course, lesson, activity, quote).
The quotes are published too. Nothing here is licensed text -- there is no task
statement, no narrative, no activity body of any kind. An activity that no
published citation names does not appear at all.

WHAT IT LETS A COLLABORATOR CHECK. Two of the three skipped checks become real
everywhere: the cited activity exists and its page is right. The third cannot be
made portable -- deciding whether a quote is a substring needs the text the quote
came from, and that text is the licensed part. What replaces it is weaker but not
nothing: the digest detects a quote EDITED AFTER it was verified, which is the
realistic failure, since the way a citation goes bad is that someone adjusts the
wording in alignment.json and never rebuilds on a machine that has the guides.

The file is generated, so preflight regenerates it where the guides are present
and fails on any difference -- the same rule items.json lives under. A hand edit
cannot hide here either.

    python3 tools/build_citation_index.py            # write data/alignment_citations.json
    python3 tools/build_citation_index.py --stdout   # print, write nothing
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "alignment_citations.json")


def norm(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


def squash(t):
    """Compare quotes on words alone, exactly as preflight does. The guides'
    typography and anything retyped from them differ on apostrophes and dashes:
    grade 7 Unit 3 Lesson 8 prints "A circle\u2019s circumference" with a curly
    apostrophe where the citation carries a straight one."""
    t = (t or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def norm_title(t):
    """The same rule preflight resolves activity names by, deliberately: a
    citation may spell an activity better than the index can. The guides set
    mathematics as artwork, so grade 7 Unit 3 Lesson 4's activity extracts as
    "Using" where the workbook prints "Using pi" -- and a citation carrying the
    real title must still resolve. Punctuation-insensitive matching is what lets
    it, and matching preflight exactly is what keeps this file and that gate
    from disagreeing about what verified."""
    t = (t or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def digest(course, lesson, activity, quote):
    """Stable across machines: normalised, joined with a character that cannot
    appear in any of the parts."""
    raw = "\x1f".join([norm(course), str(lesson), norm(activity), norm(quote)])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def build():
    align = json.load(open(os.path.join(DATA, "alignment.json")))["byItem"]
    detail = json.load(open(os.path.join(DATA, "im_ms_lessons_detail.json")))["grades"]

    activities, quotes, problems = {}, {}, []
    for item_id, entry in sorted(align.items()):
        course = entry.get("course") or ""
        m = re.search(r"Grade\s+([678])", course)
        if not m or entry.get("unit") is None:
            continue
        g, u = m.group(1), str(entry["unit"])
        for ev in entry.get("evidence") or []:
            l = str(ev.get("lesson"))
            try:
                rec = detail[g]["units"][u]["lessons"][l]
            except KeyError:
                problems.append("%s: no lesson %s.%s.%s" % (item_id, g, u, l))
                continue
            hit = [a for a in rec.get("activities") or []
                   if norm_title(a.get("name")) == norm_title(ev.get("activity"))]
            if not hit:
                problems.append("%s: no activity %r in %s.%s.%s"
                                % (item_id, ev.get("activity"), g, u, l))
                continue
            act = hit[0]
            # studentTaskAnswer is part of the body preflight quotes against:
            # the guides interleave the answers with the questions, so a
            # legitimate quote can land in it.
            body = norm(" ".join(filter(None, [act.get("studentTaskStatement"),
                                               act.get("activityNarrative"),
                                               act.get("studentTaskAnswer")])))
            if squash(ev.get("quote")) not in squash(body):
                problems.append("%s: quote not in %r" % (item_id, ev.get("activity")))
                continue
            key = "%s.%s.%s|%s" % (g, u, l, norm_title(ev["activity"]))
            activities[key] = {"lessonTitle": rec.get("title"),
                               "page": act.get("page"),
                               "sectionLetter": rec.get("sectionLetter")}
            quotes[digest(course, ev.get("lesson"), ev.get("activity"),
                          ev.get("quote"))] = True

    if problems:
        sys.stderr.write("REFUSING to build -- %d citation(s) do not verify:\n" % len(problems))
        for p in problems[:12]:
            sys.stderr.write("   %s\n" % p)
        sys.exit(1)

    return {"meta": {
                "schemaVersion": 1,
                "generatedBy": "tools/build_citation_index.py",
                "note": "Activity names, pages and quote digests for every PUBLISHED "
                        "citation. Every field here is already on the public site. No "
                        "licensed task text, narrative or activity body appears in this "
                        "file, and an activity no citation names is absent entirely.",
                "citedActivities": len(activities),
                "verifiedQuotes": len(quotes)},
            "activities": activities,
            "quoteDigests": sorted(quotes)}


def main(argv):
    doc = build()
    text = json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    if "--stdout" in argv:
        sys.stdout.write(text)
        return 0
    with open(OUT, "w") as fh:
        fh.write(text)
    sys.stderr.write("wrote %s -- %d cited activities, %d verified quotes\n"
                     % (OUT, doc["meta"]["citedActivities"], doc["meta"]["verifiedQuotes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
