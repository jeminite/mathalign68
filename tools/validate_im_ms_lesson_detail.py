#!/usr/bin/env python3
"""Exit gate for data/im_ms_lessons_detail.json.

WHY A SEPARATE GATE
The per-unit Teacher Guides and the Teacher Course Guide are independently
typeset documents that describe the same 295 lessons. That makes them two
readings of one fact, and the house rule is that two independent paths agreeing
is the only reason to trust a parse. This file joins them and refuses the result
if they disagree about what a lesson is called, where it sits, or how many there
are -- none of which a wrong-but-self-consistent PDF parse could satisfy.

RESOLVE BY TITLE, NEVER BY NUMBER. The title check is the load-bearing one. A
page-range bug that shifted every lesson by one would keep the numbering
perfectly contiguous and would be caught only by the titles disagreeing.

WHAT IT DELIBERATELY DOES NOT DO
It does not reconcile the standards. The guide tags each lesson Addressing /
Building On / Building Towards; the course guide's Standards by Lesson table is
a separate list. Where they differ, the difference is REPORTED and kept, not
resolved -- the course guide already disagrees with itself on six grade 7
lessons, so a third reading silently overwriting either one would destroy
evidence rather than add it.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETAIL = os.path.join(ROOT, "data", "im_ms_lessons_detail.json")
REF = os.path.join(ROOT, "data", "im_ms_reference.json")
PACING = os.path.join(ROOT, "data", "im_ms_pacing.json")

# Places where the two Imagine Learning documents genuinely disagree, each
# verified by opening both PDFs. Tolerated by name and reported; any OTHER
# disagreement is a failure, because the usual cause of a title mismatch is a
# page-range bug that has shifted a whole unit by one lesson.
#
# The preposition pair matters more than it looks: NYCPS's own alignment sheet
# cites "Points in the Coordinate Plane", matching the course guide, so the
# course guide's wording is the one in circulation. Resolve by title, and this
# is the kind of title that does not resolve.
KNOWN_TITLE_VARIANTS = {
    "6.7.11": ("Points in the Coordinate Plane", "Points on the Coordinate Plane"),
    "6.7.13": ("Interpreting Points in a Coordinate Plane",
               "Interpreting Points on a Coordinate Plane"),
}

# 6.3.2's lesson opener is a page of ilclass.com station links carrying its own
# bold "Activity 1" heading, so the lesson parses two. Pre-existing, unrelated to
# the split-word bug, and harmless: the phantom holds no task statement.
KNOWN_ACTIVITY_NUMBERING = {"6.3.2"}

# The three forms the guides print, and the only ones the extractor should
# ever store. Anything else means a heading arrived damaged.
CANON_KIND = re.compile(r"^(Warm-up|Activity \d+|Cool-down)(: Optional)?$")

# The unit guide titles grade 6 lesson 3.2 "(Optional)"; the pacing table lists
# only lessons 9 and 16 as optional in that unit. Verified in both PDFs. It has
# a real consequence -- the unit's minimum day count would be 16, not the 17 the
# pacing table prints -- so it is recorded rather than smoothed over.
KNOWN_OPTIONAL_VARIANTS = {"6.3.2"}

FAILED, PASSED, NOTES = [], [], []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append((name, detail))
    print("  %s %s" % ("PASS" if condition else "FAIL", name))
    if not condition and detail:
        for line in str(detail).splitlines()[:12]:
            print("       %s" % line)


def note(msg):
    NOTES.append(msg)
    print("  note %s" % msg)


def norm(t):
    """Titles differ only in typography between the two documents: curly vs
    straight apostrophes, en dashes, and stray double spaces."""
    t = (t or "").lower().replace("’", "'").replace("‘", "'")
    t = t.replace("–", "-").replace("—", "-")
    t = re.sub(r"\s*\(optional\)\s*$", "", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def main():
    if not os.path.exists(DETAIL):
        print("data/im_ms_lessons_detail.json does not exist -- run "
              "tools/extract_im_ms_lesson_detail.py first")
        sys.exit(1)
    detail = json.load(open(DETAIL))
    ref = json.load(open(REF))["grades"]

    print("\n1. The two documents describe the same lessons")
    missing, extra, mistitled, missection, variants = [], [], [], [], []
    total = 0
    for g, gd in sorted(detail["grades"].items()):
        for u, ud in sorted(gd["units"].items(), key=lambda kv: int(kv[0])):
            runit = ref[g]["units"].get(u, {})
            rlessons = runit.get("lessons", {})
            for n, rec in sorted(ud["lessons"].items(), key=lambda kv: int(kv[0])):
                total += 1
                code = "%s.%s.%s" % (g, u, n)
                if n not in rlessons:
                    extra.append(code)
                    continue
                want, got = rlessons[n], rec
                if norm(want["title"]) != norm(got["title"]):
                    known = KNOWN_TITLE_VARIANTS.get(code)
                    if known and norm(known[0]) == norm(want["title"]) \
                            and norm(known[1]) == norm(got["title"]):
                        variants.append("%s: course guide %r, unit guide %r"
                                        % (code, want["title"], got["title"]))
                    else:
                        mistitled.append("%s: course guide %r, unit guide %r"
                                         % (code, want["title"], got["title"]))
                if want.get("sectionLetter") and got.get("sectionLetter") \
                        and want["sectionLetter"] != got["sectionLetter"]:
                    missection.append("%s: course guide section %s, unit guide %s"
                                      % (code, want["sectionLetter"], got["sectionLetter"]))
            for n in rlessons:
                if n not in ud["lessons"]:
                    missing.append("%s.%s.%s" % (g, u, n))

    check("every lesson in the course guide was found in its unit guide",
          not missing, "%d missing: %s" % (len(missing), ", ".join(missing[:15])))
    check("every lesson found in a unit guide exists in the course guide",
          not extra, "%d unexpected: %s" % (len(extra), ", ".join(extra[:15])))
    check("every lesson title matches between the two guides, bar the known variants",
          not mistitled, "\n".join(mistitled[:12]))
    for v in variants:
        note("known title variant -- %s" % v)
    check("every lesson's section letter matches between the two guides",
          not missection, "\n".join(missection[:12]))
    note("%d lessons parsed" % total)

    print("\n2. Lesson counts agree with the course guide's own tally")
    bad = []
    for g, gd in sorted(detail["grades"].items()):
        per = ref[g]["counts"]["lessonsPerUnit"]
        for u, ud in sorted(gd["units"].items(), key=lambda kv: int(kv[0])):
            want, got = per.get(u), len(ud["lessons"])
            if want != got:
                bad.append("grade %s unit %s: course guide %s, unit guide %d"
                           % (g, u, want, got))
    check("each unit holds the number of lessons the course guide counts",
          not bad, "\n".join(bad))

    print("\n3. Every lesson carries what an alignment judgement needs")
    no_act, no_task, no_std, no_narr = [], [], [], []
    thin = []
    noncanon, gappy = [], []
    for g, gd in sorted(detail["grades"].items()):
        for u, ud in sorted(gd["units"].items(), key=lambda kv: int(kv[0])):
            for n, rec in sorted(ud["lessons"].items(), key=lambda kv: int(kv[0])):
                code = "%s.%s.%s" % (g, u, n)
                acts = rec.get("activities") or []
                if not acts:
                    no_act.append(code)
                    continue
                # "At least one" was too weak a bar. Aligning grade 7 found
                # grade 6 Unit 8's Lessons 9 and 13 carrying one and two
                # activities where the teacher guide has four or five, so an
                # item was being judged against a fraction of its lesson --
                # and this validator passed. Unit 9 lessons really are one or
                # two activities (they are projects), so they are excluded
                # rather than the bar being lowered for everyone.
                if len(acts) < 3 and u != "9":
                    thin.append("%s (%d)" % (code, len(acts)))
                # THE CHECK THAT WOULD HAVE CAUGHT THE MERGE BUG.
                # The text layer bakes a space inside the word ("Ac tivity 1"),
                # the heading was not recognised, no new activity opened, and
                # every following field was appended to the PREVIOUS activity.
                # 40 headings went that way across 24 lessons and the validator
                # passed clean, because "fewer than 3 activities" is a symptom
                # and saw only 10 of them. These two assert the STRUCTURE
                # instead: a lesson's activities are numbered 1..N with no gap,
                # and every kind is one of the three canonical forms.
                for a in acts:
                    k = (a.get("kind") or "").strip()
                    if not CANON_KIND.match(k):
                        noncanon.append("%s: %r" % (code, k))
                nums = [int(m.group(1)) for a in acts
                        for m in [re.match(r"^Activity\s*(\d+)$",
                                           (a.get("kind") or "").strip())] if m]
                if nums and sorted(nums) != list(range(1, max(nums) + 1)):
                    if code not in KNOWN_ACTIVITY_NUMBERING:
                        gappy.append("%s: %s" % (code, nums))
                if not any((a.get("studentTaskStatement") or "").strip() for a in acts):
                    no_task.append(code)
                if not rec.get("standards"):
                    no_std.append(code)
                if not (rec.get("lessonNarrative") or "").strip():
                    no_narr.append(code)
    check("every lesson has at least one activity",
          not no_act, "%d without: %s" % (len(no_act), ", ".join(no_act[:15])))
    check("every lesson has at least one student task statement",
          not no_task, "%d without: %s" % (len(no_task), ", ".join(no_task[:15])))
    if no_std:
        note("%d lessons carry no Alignments block: %s"
             % (len(no_std), ", ".join(no_std[:10])))
    if no_narr:
        note("%d lessons carry no Lesson Narrative: %s"
             % (len(no_narr), ", ".join(no_narr[:10])))
    # Reported, not failed: a genuinely short lesson is possible and the fix is
    # in the extractor, not here. But a reader placing an item at one of these
    # is working from less than the lesson contains and should know it.
    check("every activity's kind is one of the three canonical forms",
          not noncanon, "\n".join(noncanon[:10]))
    check("every lesson's activities are numbered 1..N with no gap",
          not gappy, "\n".join(gappy[:10]))
    note("%d heading(s) were recovered from a split word by the extractor"
         % (detail.get("meta", {}).get("headingsRecovered", 0)))
    if thin:
        note("%d non-project lessons carry fewer than 3 activities -- an item "
             "aligned to one of these was judged against part of the lesson: %s"
             % (len(thin), ", ".join(thin[:20])))

    print("\n4. Standards: a third reading, reported not reconciled")
    agree = disagree = 0
    samples = []
    for g, gd in sorted(detail["grades"].items()):
        l2s = ref[g]["lessonToStandards"]
        for u, ud in sorted(gd["units"].items(), key=lambda kv: int(kv[0])):
            if ud.get("edition") != "newYork":
                continue          # a different edition tags different standards
            for n, rec in sorted(ud["lessons"].items(), key=lambda kv: int(kv[0])):
                code = "%s.%s.%s" % (g, u, n)
                guide = {c.replace(".", "") for c
                         in (rec.get("standards") or {}).get("Addressing", [])}
                table = {c.replace(".", "") for c in l2s.get(code, [])
                         if "Cluster" not in c}
                if not guide or not table:
                    continue
                if guide & table:
                    agree += 1
                else:
                    disagree += 1
                    if len(samples) < 10:
                        samples.append("%s: unit guide %s, course guide %s"
                                       % (code, sorted(guide), sorted(table)))
    note("%d lessons where the two documents name an overlapping standard, "
         "%d where they name none in common" % (agree, disagree))
    for s in samples:
        note("  %s" % s)
    # A handful of disagreements is expected and is evidence. Wholesale
    # disagreement means the page ranges are wrong and the join is meaningless.
    check("the two documents agree about standards on most lessons",
          agree > 4 * max(disagree, 1) if (agree + disagree) else True,
          "%d agree vs %d disagree -- a page-range bug would look like this"
          % (agree, disagree))

    print("\n5. Optional lessons: the unit guides are a third reading")
    # The unit guide suffixes an optional lesson's title with "(Optional)"; the
    # pacing table lists optional lesson numbers per unit. Neither was written
    # with the other in mind, so agreement is real corroboration -- and the
    # pacing figures are themselves already read three times over.
    pacing = json.load(open(PACING))["grades"]
    mismatch = []
    for g, gd in sorted(detail["grades"].items()):
        for u, ud in sorted(gd["units"].items(), key=lambda kv: int(kv[0])):
            if ud.get("edition") != "newYork":
                continue
            block = pacing.get(g, {}).get(u, {})
            listed = block.get("optionalLessons")
            if listed == "all":
                continue
            want = set(str(n) for n in (listed or []))
            got = set(n for n, r in ud["lessons"].items() if r.get("optional"))
            allowed = {n for n in got
                       if "%s.%s.%s" % (g, u, n) in KNOWN_OPTIONAL_VARIANTS}
            for n in sorted(allowed, key=int):
                note("known optional variant -- %s.%s.%s is titled (Optional) in "
                     "the unit guide but is not in the pacing table" % (g, u, n))
            if want != (got - allowed):
                mismatch.append("grade %s unit %s: pacing %s, unit guide %s"
                                % (g, u, sorted(want, key=int) or "none",
                                   sorted(got, key=int) or "none"))
    check("the unit guides and the pacing table agree on which lessons are optional",
          not mismatch, "\n".join(mismatch[:12]))

    print("\n" + "-" * 68)
    print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
    if FAILED:
        print("\nVALIDATION FAILED. Do not align against this index:")
        for name, _ in FAILED:
            print("  %s" % name)
        sys.exit(1)
    print("\nthe lesson detail index is safe to build on")


if __name__ == "__main__":
    main()
