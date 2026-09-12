#!/usr/bin/env python3
"""Assemble everything needed to judge where one standard's items are taught.

Usage:
    python3 tools/alignment_packet.py NY-7.G.4 [--tier2] [--full]

WHY PER STANDARD
Items sharing a standard share a shortlist, so the expensive half of the work --
reading lessons -- is done once per standard rather than once per item. The cheap
half, deciding which lesson an individual item matches, is then done per item
against material already on screen. That is the same split data/alignment.json
already has in byStandard and byItem.

WHAT A READER IS LOOKING FOR
Not topical similarity. The question is whether a lesson ASKS STUDENTS TO DO
what the item asks them to do, and the answer has to be a named activity whose
task statement can be quoted. A lesson that covers the same topic without ever
asking students to do that thing is not evidence, and should be left out.

Cool-downs, checkpoints and end-of-unit assessments are marked [ASSESSED]: those
are where the curriculum itself tests the skill, which is the half of "where is
this taught and assessed" that nothing else in this project can answer.
"""
import json
import os
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import shortlist_lessons as S

TASK_CHARS = 260
ASSESSED = ("cool-down", "checkpoint", "end-of-unit")


def wrap(text, indent):
    return textwrap.fill(text or "", 96, initial_indent=indent,
                         subsequent_indent=indent) if text else ""


def brief_lesson(idx, code, src):
    rec = S.lesson(idx, code)
    if not rec:
        return
    tags = ", ".join((rec.get("standards") or {}).get("Addressing", [])) or "none"
    print("  %-8s %-46s [%s]" % (code, (rec.get("title") or "")[:46], src))
    print("           sec %s | addressing %s" % (rec.get("sectionLetter"), tags))
    for a in rec.get("activities", []):
        kind = (a.get("kind") or "").lower()
        mark = " [ASSESSED]" if any(k in kind for k in ASSESSED) else ""
        opt = " (opt)" if a.get("optional") else ""
        print("           - %-11s %s%s%s" % (a.get("kind"), a.get("name") or "?", opt, mark))


def show_lesson(idx, code, full=False):
    rec = S.lesson(idx, code)
    if not rec:
        print("  %s  (not in the index)" % code)
        return
    tags = (rec.get("standards") or {}).get("Addressing", [])
    flag = " (OPTIONAL)" if rec.get("optional") else ""
    print("\n  %s  %s%s" % (code, rec.get("title"), flag))
    print("      section %s: %s   |   addressing: %s"
          % (rec.get("sectionLetter"), rec.get("sectionTitle"),
             ", ".join(tags) or "none"))
    goal = rec.get("studentLearningGoal")
    if goal:
        print(wrap(goal, "      goal: "))
    for a in rec.get("activities", []):
        kind = (a.get("kind") or "").lower()
        mark = " [ASSESSED]" if any(k in kind for k in ASSESSED) else ""
        print("      - %s: %s%s  (p%s)"
              % (a.get("kind"), a.get("name") or "?", mark, a.get("page")))
        task = a.get("studentTaskStatement") or ""
        if task:
            t = task if full else task[:TASK_CHARS] + ("..." if len(task) > TASK_CHARS else "")
            print(wrap(t, "          "))
    if full:
        for p in rec.get("practiceProblems", []):
            print("      - %s (p%s)" % (p.get("problem"), p.get("page")))
            print(wrap((p.get("prompt") or "")[:TASK_CHARS], "          "))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    standard = argv[1]
    want_tier2 = "--tier2" in argv
    full = "--full" in argv

    idx = S.load()
    doc = json.load(open(os.path.join(ROOT, "data", "items.json")))
    items = doc["items"] if "items" in doc else doc
    content = json.load(open(os.path.join(ROOT, "data", "content.json")))["items"]

    mine = [i for i in items if i["standard"] == standard]
    if not mine:
        print("no items cite %s" % standard)
        return 1
    item_grade = str(mine[0]["grade"])
    grade = S.home_grade(standard, item_grade)

    print("=" * 100)
    print("STANDARD %s   (%d items, on the grade %s test%s)"
          % (standard, len(mine), item_grade,
             "; taught in the grade %s curriculum" % grade
             if grade != item_grade else ""))
    txt = " ".join(S.item_text(i, content) for i in mine)
    t = S.tiers(idx, grade, standard, txt, k=12)
    print("candidate units from the course guide table: %s" % (t["units"] or "none"))

    print("\n" + "-" * 100)
    print("ITEMS")
    for i in sorted(mine, key=lambda i: (i["year"], i["item"])):
        c = content.get(i["id"], {})
        print("\n  %s  (%s %s, %s)" % (i["id"], i["year"], i["type"],
                                       "p-value %s" % i.get("pValue")
                                       if i.get("pValue") is not None else "no p-value"))
        stem = c.get("stem")
        if stem:
            print(wrap(stem, "      "))
            for ch in c.get("choices", []) or []:
                print("        %s) %s%s" % (ch.get("label"), ch.get("text"),
                                            "  <-- correct" if ch.get("isCorrect") else ""))
            for f in c.get("figures", []) or []:
                print(wrap("[figure: %s -- %s]" % (f.get("type"), f.get("alt")), "      "))
        else:
            print("      (not transcribed)")

    if "--brief" in argv:
        print("\n" + "-" * 100)
        print("TIER 1 -- %d lessons" % len(t["tier1"]))
        for r in t["tier1"]:
            src = []
            if r["taggedByUnitGuide"]:
                src.append("unit tag")
            if r["inTable"]:
                src.append("table")
            brief_lesson(idx, r["lesson"], ", ".join(src) or "lexical")
        return 0

    print("\n" + "-" * 100)
    print("TIER 1 -- lessons to read (ranked; tagged by either guide first)")
    for r in t["tier1"]:
        src = []
        if r["taggedByUnitGuide"]:
            src.append("unit guide tag")
        if r["inTable"]:
            src.append("course guide table")
        print("\n[%s]" % (", ".join(src) or "lexical only"), end="")
        show_lesson(idx, r["lesson"], full)

    if want_tier2:
        print("\n" + "-" * 100)
        print("TIER 2 -- the rest of the candidate units (%d lessons)" % len(t["tier2"]))
        for code in t["tier2"]:
            show_lesson(idx, code, full)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
