#!/usr/bin/env python3
"""Exit gate for data/im_ms_reference.json.

Run this before anything is allowed to depend on the Imagine IM 6-8 New York
lesson numbering.

WHY A SEPARATE GATE RATHER THAN MORE ASSERTIONS IN THE EXTRACTOR
The extractor asserts what it expects to find while it is reading. This file
tests properties of the finished file, from the outside, without knowing how it
was produced -- so it still fires when the extractor's own expectations are the
thing that is wrong. The lesson counts are the clearest case: the extractor
checks them against a list it carries, which is exactly the list that would be
edited if a future guide revision moved a lesson. The checks here (sections
contiguous from A, lessons contiguous from 1, section assignment monotonic in
lesson number, the two standard maps exact inverses of each other) cannot be
satisfied by a wrong-but-self-consistent extraction.

RESOLVE BY TITLE, NEVER BY NUMBER. That rule is why this file checks titles as
hard as it checks numbers, and why cross-unit duplicate titles are reported: a
title that appears twice in a grade is not a usable address.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "data", "im_ms_reference.json")
REGISTRY = os.path.join(ROOT, "data", "standards.json")
PACING = os.path.join(ROOT, "data", "im_ms_pacing.json")

GRADES = ("6", "7", "8")
EXPECTED_UNITS = 9
CODE = re.compile(r"^NY-([3-8])\.([A-Z]{1,3})\.\d+[a-z]?$")
CLUSTER = re.compile(r"^NY-([3-8])\.([A-Z]{1,3})\.Cluster-\d+$")
LESSON_REF = re.compile(r"^([678])\.([1-9])\.([1-9]\d?)$")

# The unit swap is the single most dangerous fact about this data, so it is
# asserted rather than merely written down: grades 7 and 8 exchange Units 7 and
# 8 relative to the national edition. A future guide that silently reverted the
# swap would otherwise reassign twenty grade 7 lessons without a word.
UNIT_TITLE_MUST_CONTAIN = {
    ("7", "7"): "Probability",
    ("7", "8"): "Angles",
    ("8", "7"): "Pythagorean",
    ("8", "8"): "Exponents",
}

# Grade 8's guide contradicts itself on Unit 6: Standards by Lesson lists 11
# lessons, the Scope and Sequence box titles 9, because NY-8.SP.4 was removed
# under NGMLS and that table was not regenerated. Tolerated by name -- any
# OTHER untitled lesson is a failure.
KNOWN_UNTITLED = {"8.6.10", "8.6.11"}

FAILED = []
PASSED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("  ok    %s" % name)
    else:
        FAILED.append((name, detail))
        print("  FAIL  %s" % name)
        for line in str(detail).splitlines():
            if line.strip():
                print("        %s" % line)


def note(text):
    for line in str(text).splitlines():
        if line.strip():
            print("        %s" % line)


def main():
    if not os.path.exists(REF):
        sys.exit("validate: %s does not exist -- run tools/extract_im_ms_lessons.py"
                 % os.path.relpath(REF, ROOT))
    ref = json.load(open(REF))
    registry = json.load(open(REGISTRY))["standards"]

    print("Imagine IM 6-8 New York reference -- validation gate")
    print("=" * 68)

    # ---------------------------------------------------------- 1. shape
    print("\n1. Shape")
    check("all three grades are present",
          sorted(ref.get("grades", {})) == list(GRADES),
          "found %s" % sorted(ref.get("grades", {})))
    check("every grade declares New York numbering",
          all(ref["grades"][g].get("numbering") == "newYork" for g in GRADES),
          "; ".join("%s=%s" % (g, ref["grades"][g].get("numbering")) for g in GRADES))
    check("the numbering used by each source table is recorded",
          bool(ref["meta"].get("unitNumberingByTable")))
    check("the known hazards are carried with the data",
          len(ref["meta"].get("hazards", [])) >= 3,
          "%d recorded" % len(ref["meta"].get("hazards", [])))

    # ------------------------------------------------- 2. units and sections
    print("\n2. Units, sections and lessons")
    bad_units, bad_sections, bad_lessons, bad_monotonic, bad_sectitle = [], [], [], [], []
    for g in GRADES:
        units = ref["grades"][g]["units"]
        if sorted(int(u) for u in units) != list(range(1, EXPECTED_UNITS + 1)):
            bad_units.append("grade %s: units %s" % (g, sorted(units)))
        for u in sorted(units, key=int):
            spec = units[u]
            letters = sorted(spec["sections"])
            want = [chr(ord("A") + i) for i in range(len(letters))]
            if letters != want:
                bad_sections.append("grade %s unit %s: sections %s" % (g, u, letters))
            nums = sorted(int(n) for n in spec["lessons"])
            if nums != list(range(1, len(nums) + 1)):
                bad_lessons.append("grade %s unit %s: lessons %s" % (g, u, nums))
            seen = []
            for n in nums:
                lesson = spec["lessons"][str(n)]
                letter = lesson.get("sectionLetter")
                if letter not in spec["sections"]:
                    bad_sectitle.append("grade %s.%s.%s: section %r not in this unit"
                                        % (g, u, n, letter))
                elif lesson.get("sectionTitle") != spec["sections"][letter]:
                    bad_sectitle.append(
                        "grade %s.%s.%s: sectionTitle %r != unit's %r"
                        % (g, u, n, lesson.get("sectionTitle"), spec["sections"][letter]))
                if seen and letter and letter < seen[-1]:
                    bad_monotonic.append("grade %s unit %s: lesson %s is section %s "
                                         "after %s" % (g, u, n, letter, seen[-1]))
                if letter:
                    seen.append(letter)

    check("every grade has exactly nine units", not bad_units, "\n".join(bad_units))
    check("each unit's section letters run contiguously from A",
          not bad_sections, "\n".join(bad_sections))
    check("each unit's lessons run contiguously from 1",
          not bad_lessons, "\n".join(bad_lessons))
    check("each lesson's section title matches its unit's own section list",
          not bad_sectitle, "\n".join(bad_sectitle))
    check("section letters never go backwards as lesson number rises",
          not bad_monotonic, "\n".join(bad_monotonic))

    # The unit swap.
    swap = []
    for (g, u), word in sorted(UNIT_TITLE_MUST_CONTAIN.items()):
        title = ref["grades"][g]["units"][u]["title"]
        if word.lower() not in title.lower():
            swap.append("grade %s unit %s is %r, expected to contain %r"
                        % (g, u, title, word))
    check("grades 7 and 8 still carry the New York Unit 7/8 order",
          not swap, "\n".join(swap))

    # ------------------------------------------------------------ 3. titles
    print("\n3. Titles")
    kerned, empty, shouty, dupe_in_unit = [], [], [], []
    dupes_across = {}
    for g in GRADES:
        for u, spec in sorted(ref["grades"][g]["units"].items(), key=lambda kv: int(kv[0])):
            titles = {}
            for n, lesson in sorted(spec["lessons"].items(), key=lambda kv: int(kv[0])):
                t = (lesson.get("title") or "").strip()
                ref_id = "%s.%s.%s" % (g, u, n)
                if not t:
                    empty.append(ref_id)
                    continue
                # 'U nit 4' -- the guides kern a leading capital away from its
                # word, which once made Unit 4 overwrite Unit 3 wholesale.
                if re.match(r"^[A-Z]\s[a-z]", t):
                    kerned.append("%s: %r" % (ref_id, t))
                if t == t.upper() and len(t) > 4:
                    shouty.append("%s: %r" % (ref_id, t))
                if t.lower() in titles:
                    dupe_in_unit.append("%s and %s.%s.%s share %r"
                                        % (ref_id, g, u, titles[t.lower()], t))
                titles[t.lower()] = n
                dupes_across.setdefault((g, t.lower()), []).append(ref_id)

    check("every titled lesson has a non-empty title",
          not empty, "untitled: %s" % ", ".join(empty))
    check("no title carries a kerned leading capital",
          not kerned, "\n".join(kerned))
    check("no title was extracted as a heading in all capitals",
          not shouty, "\n".join(shouty))
    check("no unit repeats a lesson title within itself",
          not dupe_in_unit, "\n".join(dupe_in_unit))

    repeated = {k: v for k, v in dupes_across.items() if len(v) > 1}
    if repeated:
        print("  note  %d lesson titles repeat within a grade across units --" % len(repeated))
        note("resolve those by unit AND title, never by title alone:")
        for (g, t), where in sorted(repeated.items())[:8]:
            note("grade %s %r: %s" % (g, t, ", ".join(where)))
        if len(repeated) > 8:
            note("... and %d more" % (len(repeated) - 8))

    # ------------------------------------------------------ 4. standard maps
    print("\n4. Standard maps")
    bad_refs, bad_codes, untitled, mixed = [], [], [], []
    not_in_registry = {}
    for g in GRADES:
        G = ref["grades"][g]
        titled = {"%s.%s.%s" % (g, u, n)
                  for u, spec in G["units"].items() for n in spec["lessons"]}

        pairs = [("lessonToStandards", G["lessonToStandards"]),
                 ("lessonToClusters", G.get("lessonToClusters", {}))]
        for label, table in pairs:
            for lesson_id, codes in sorted(table.items()):
                if not LESSON_REF.match(lesson_id) or lesson_id.split(".")[0] != g:
                    bad_refs.append("grade %s: %s key %r" % (g, label, lesson_id))
                elif lesson_id not in titled:
                    untitled.append(lesson_id)
                for code in codes:
                    want = CLUSTER if label == "lessonToClusters" else CODE
                    if not want.match(code):
                        mixed.append("%s %s cites %r" % (label, lesson_id, code))
                    elif want is CODE and code not in registry:
                        not_in_registry.setdefault(g, set()).add(code)

        for label, table, want in (("standardToLessons", G["standardToLessons"], CODE),
                                   ("clusterToLessons", G.get("clusterToLessons", {}), CLUSTER)):
            for code, spec in sorted(table.items()):
                if not want.match(code):
                    mixed.append("grade %s %s key %r" % (g, label, code))
                refs = spec["lessons"] if isinstance(spec, dict) else spec
                for lesson_id in refs:
                    if not LESSON_REF.match(lesson_id) or lesson_id.split(".")[0] != g:
                        bad_refs.append("%s cites %r" % (code, lesson_id))

    check("every lesson reference is a well-formed <grade>.<unit>.<lesson>",
          not bad_refs, "\n".join(bad_refs))
    check("every standard code is in NYSED's own normalised form",
          not bad_codes, "\n".join(bad_codes))
    # Cluster citations must stay out of the standard maps. Mixed in, they join
    # to nothing in data/standards.json and look like missing standards.
    check("cluster citations and standard codes are never mixed in one map",
          not mixed, "\n".join(mixed))
    check("no lesson carries standards but no title, beyond the documented "
          "grade 8 Unit 6 defect",
          set(untitled) <= KNOWN_UNTITLED,
          "undocumented: %s" % ", ".join(sorted(set(untitled) - KNOWN_UNTITLED)))
    if set(untitled) & KNOWN_UNTITLED:
        note("expected, and recorded as a hazard: %s listed in grade 8's Standards "
             "by Lesson table but absent from its Scope and Sequence box"
             % ", ".join(sorted(set(untitled) & KNOWN_UNTITLED)))

    # The two tables are authored separately and are NOT exact inverses -- six
    # pairs differ in grade 7. So the check is not "they agree" but "they
    # disagree in exactly the places the file says they do". That fails on a new
    # disagreement AND on one that quietly went away, which a tolerance would
    # not. Grades 6 and 8 are exact inverses, which is what makes six a fact
    # about the guide rather than about the parser.
    drift = []
    for g in GRADES:
        G = ref["grades"][g]
        forward = {(lid, c) for lid, cs in G["lessonToStandards"].items() for c in cs}
        forward |= {(lid, c) for lid, cs in G.get("lessonToClusters", {}).items() for c in cs}
        back = {(lid, c) for c, v in G["standardToLessons"].items() for lid in v["lessons"]}
        back |= {(lid, c) for c, lids in G.get("clusterToLessons", {}).items() for lid in lids}
        computed = {(d["lesson"], d["standard"]) for d in G.get("tableDisagreements", [])}
        actual = (forward - back) | (back - forward)
        for pair in sorted(actual - computed):
            drift.append("grade %s: %s -> %s disagrees but is not recorded" % (g, pair[0], pair[1]))
        for pair in sorted(computed - actual):
            drift.append("grade %s: %s -> %s recorded as a disagreement but agrees" % (g, pair[0], pair[1]))
    check("the two tables disagree in exactly the places the file records",
          not drift, "\n".join(drift))

    for g in GRADES:
        rows = ref["grades"][g].get("tableDisagreements", [])
        if rows:
            note("grade %s: %d disagreement(s) between the guide's own tables --" % (g, len(rows)))
            for d in rows:
                note("  %s / %s: %s" % (d["lesson"], d["standard"], d["citedBy"]))

    # Not a failure: the guides index every NGMLS code, while data/standards.json
    # holds only what NYSED's own chart puts on a test. Reported so the gap is
    # visible rather than discovered later during a join.
    # Split into the two kinds, because they need opposite handling in a join.
    # A PARENT code (NY-7.RP.2, whose 2a-2d are all in the registry) should be
    # expanded to its children; a genuinely ABSENT code has no counterpart at
    # all and a join must drop it knowingly. Reported as one undifferentiated
    # list this is just noise.
    if not_in_registry:
        parents, absent = {}, {}
        for g, codes in not_in_registry.items():
            for code in sorted(codes):
                kids = sorted(c for c in registry
                              if c.startswith(code) and len(c) == len(code) + 1
                              and c[-1].isalpha())
                (parents if kids else absent).setdefault(g, []).append(
                    "%s -> %s" % (code, ", ".join(kids)) if kids else code)
        total = sum(len(v) for v in not_in_registry.values())
        print("  note  %d codes cited by the guides are not in data/standards.json" % total)
        note("(the guides index every NGMLS standard; the registry holds the "
             "tested ones)")
        if parents:
            note("PARENT codes -- expand to their sub-standards when joining:")
            for g, rows in sorted(parents.items()):
                for row in rows:
                    note("  grade %s: %s" % (g, row))
        if absent:
            note("ABSENT from the registry -- a join must drop these knowingly:")
            for g, rows in sorted(absent.items()):
                note("  grade %s: %s" % (g, ", ".join(rows)))

    # ------------------------------------------------------------ 5. counts
    print("\n5. Counts as published in the file")
    bad_counts = []
    for g in GRADES:
        G = ref["grades"][g]
        c = G["counts"]
        titled = sum(len(spec["lessons"]) for spec in G["units"].values())
        sections = sum(len(spec["sections"]) for spec in G["units"].values())
        if c["lessonsTitled"] != titled:
            bad_counts.append("grade %s: counts.lessonsTitled %d != %d titled"
                              % (g, c["lessonsTitled"], titled))
        if c["sections"] != sections:
            bad_counts.append("grade %s: counts.sections %d != %d sections"
                              % (g, c["sections"], sections))
        if c["units"] != len(G["units"]):
            bad_counts.append("grade %s: counts.units %d != %d"
                              % (g, c["units"], len(G["units"])))
        per = {int(k): v for k, v in c["lessonsPerUnit"].items()}
        real = {int(u): len(spec["lessons"]) for u, spec in G["units"].items()}
        if per != real:
            bad_counts.append("grade %s: lessonsPerUnit %s != %s" % (g, per, real))
        if c.get("clustersCited") != len(G.get("clusterToLessons", {})):
            bad_counts.append("grade %s: counts.clustersCited %s != %d"
                              % (g, c.get("clustersCited"), len(G.get("clusterToLessons", {}))))
        if c.get("tableDisagreements") != len(G.get("tableDisagreements", [])):
            bad_counts.append("grade %s: counts.tableDisagreements %s != %d"
                              % (g, c.get("tableDisagreements"), len(G.get("tableDisagreements", []))))
        if c["standards"] != len(G["standardToLessons"]):
            bad_counts.append("grade %s: counts.standards %d != %d"
                              % (g, c["standards"], len(G["standardToLessons"])))
    check("every published count matches what the file actually contains",
          not bad_counts, "\n".join(bad_counts))

    for g in GRADES:
        c = ref["grades"][g]["counts"]
        note("grade %s: %d units, %d sections, %d lessons %s"
             % (g, c["units"], c["sections"], c["lessonsTitled"],
                [c["lessonsPerUnit"][str(i)] for i in range(1, 10)]))

    # ------------------------------------------------------------ 6. pacing
    print("\n6. Pacing against the lesson counts")
    if not os.path.exists(PACING):
        print("  --    data/im_ms_pacing.json absent; run tools/extract_pacing.py")
    else:
        pacing = json.load(open(PACING))["grades"]
        bad_weeks, bad_days, bad_ma = [], [], []
        for g in GRADES:
            units = ref["grades"][g]["units"]
            pace = pacing.get(g, {})
            last_week = 0
            for u in sorted(pace, key=int):
                spec, block = units.get(u), pace[u]
                if not spec:
                    continue
                lessons = len(spec["lessons"])
                optional = block["optionalLessons"]
                n_opt = lessons if optional == "all" else len(optional)

                # THE ARITHMETIC IDENTITY. The pacing table's day range is
                # exactly predictable from three other things, each read from a
                # different table by different code: the lesson count from the
                # Scope and Sequence boxes, the (MA) mark, and the optional
                # lesson list. The guide's own footnote states the formula --
                # "number of days = Lessons + Assessments - Optional Lessons" --
                # and it resolves to two assessment days per unit plus one more
                # where there is a Mid-Unit Assessment.
                #
                # Unit 9 is the documented exception: it is optional in its
                # entirety and carries no assessment days, so it runs [0,
                # lessons].
                if int(u) == EXPECTED_UNITS:
                    want = [0, lessons]
                else:
                    hi = lessons + 2 + (1 if block["midUnitAssessment"] else 0)
                    want = [hi - n_opt, hi]
                if block["days"] != want:
                    bad_days.append(
                        "grade %s unit %s: table says %s, but %d lessons + %d "
                        "assessment days - %d optional predicts %s"
                        % (g, u, block["days"], lessons,
                           2 + (1 if block["midUnitAssessment"] else 0), n_opt, want))

                if block["startWeek"] <= last_week:
                    bad_weeks.append("grade %s unit %s starts week %d, not after "
                                     "unit %d's week %d"
                                     % (g, u, block["startWeek"], int(u) - 1, last_week))
                last_week = block["startWeek"]
                if block["startWeek"] > 35:
                    bad_weeks.append("grade %s unit %s starts week %d, past week 35"
                                     % (g, u, block["startWeek"]))
        check("every unit's printed day range equals lessons + assessments - optional",
              not bad_days, "\n".join(bad_days))
        check("unit start weeks run forwards and fit inside the 35-week year",
              not bad_weeks, "\n".join(bad_weeks))
        for g in GRADES:
            pace = pacing.get(g, {})
            lo = sum(pace[u]["days"][0] for u in pace)
            hi = sum(pace[u]["days"][1] for u in pace)
            ma = [u for u in sorted(pace, key=int) if pace[u]["midUnitAssessment"]]
            note("grade %s: %d-%d days, mid-unit assessments in units %s"
                 % (g, lo, hi, ", ".join(ma) or "none"))
        check("no grade's maximum pacing exceeds a 35-week year (175 days)",
              all(sum(pacing[g][u]["days"][1] for u in pacing[g]) <= 175 for g in GRADES),
              "; ".join("grade %s: %d" % (g, sum(pacing[g][u]["days"][1] for u in pacing[g]))
                        for g in GRADES))

    print("\n" + "-" * 68)
    print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
    if FAILED:
        print("\nVALIDATION FAILED. Do not build on this numbering:")
        for name, _ in FAILED:
            print("  %s" % name)
        sys.exit(1)
    print("\nthe Imagine IM 6-8 New York numbering is safe to build on")


if __name__ == "__main__":
    main()
