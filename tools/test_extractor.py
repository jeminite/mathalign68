#!/usr/bin/env python3
"""
Test the item-map extractor.

  python3 tools/test_extractor.py
  python3 tools/test_extractor.py --update    # re-record the golden files

Three layers, because each catches something the others cannot:

1. GOLDEN FILES. Every extracted row, compared byte-for-byte against a committed
   fixture. Catches any change in behaviour, intended or not. Diffs are printed
   on the row's raw text so a failure reads as text rather than as JSON.

2. PROPERTY TESTS, which do not consult the goldens at all. A golden can be
   wrong -- it was recorded from the extractor, so a bug present at recording
   time is baked into it. The properties are checked against the blueprint and
   against arithmetic instead, so they would fail on a wrong golden.

3. A TEST THAT PROVES THE TESTS CAN FAIL. The extractor assigns each word to a
   column by its CENTRE x, because Cluster and Subscore are centre-aligned. That
   is exactly the kind of subtlety a later refactor "simplifies" to left-edge x
   without noticing. So the suite re-runs the assignment with left-edge x and
   asserts the property tests DO fail. If that ever passes, the properties have
   stopped testing anything.

The CCLS-era 2022 extractions are in the golden set deliberately, even though
that era is not published: they are the only coverage for a map spanning two
pages, for inheriting columns onto a page with no header, and for the layout
with no Subscore or Secondary columns.

A missing source PDF skips its case with a message rather than failing, so the
suite still runs somewhere without sources/.
"""

import argparse
import difflib
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(ROOT, "fixtures")
EXTRACTOR = os.path.join(HERE, "extract_item_map.py")

PASS, FAIL, SKIP = [], [], []


def ok(name):
    PASS.append(name)


def bad(name, detail):
    FAIL.append((name, detail))


def skip(name, why):
    SKIP.append((name, why))


def source_for(test_id):
    grade, year = test_id[1], test_id[3:]
    for candidate in (
        os.path.join(ROOT, "sources", "%s-released-items-math-g%s.pdf" % (year, grade)),
        os.path.join(ROOT, "sources", "ccls", "%s-released-items-math-g%s.pdf" % (year, grade)),
    ):
        if os.path.exists(candidate):
            return candidate
    return None


def extract(pdf):
    out = subprocess.run([sys.executable, EXTRACTOR, pdf, "--stdout"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None, (out.stderr or out.stdout).strip()
    return json.loads(out.stdout), None


def as_golden(payload):
    meta = payload["meta"]
    return {
        "testId": meta["testId"], "grade": meta["grade"], "year": meta["year"],
        "standardsEra": meta["standardsEra"], "mapPages": meta["mapPages"],
        "columns": meta["columns"], "releasedItems": meta["releasedItems"],
        "multipleChoice": meta["multipleChoice"],
        "constructedResponse": meta["constructedResponse"],
        "creditsReleased": meta["creditsReleased"], "repairs": meta["repairs"],
        "rows": [dict({k: v for k, v in i.items() if k != "extraction"},
                      raw=i["extraction"]["raw"])
                 for i in payload["items"]],
    }


# ------------------------------------------------------------------- goldens

def test_goldens(update):
    for path in sorted(glob.glob(os.path.join(FIXTURES, "itemmap_*.golden.json"))):
        test_id = re.search(r"itemmap_(g\d-\d{4})\.golden", path).group(1)
        pdf = source_for(test_id)
        name = "golden %s" % test_id
        if pdf is None:
            skip(name, "source PDF not on disk")
            continue
        payload, err = extract(pdf)
        if payload is None:
            bad(name, "the extractor failed:\n    " + err.replace("\n", "\n    "))
            continue
        got = as_golden(payload)
        if update:
            with open(path, "w") as fh:
                json.dump(got, fh, indent=2)
                fh.write("\n")
            ok(name + " (re-recorded)")
            continue
        want = json.load(open(path))
        if got == want:
            ok(name)
            continue
        # Diff the raw row strings, which read as text.
        a = [r["raw"] for r in want["rows"]]
        b = [r["raw"] for r in got["rows"]]
        detail = "\n".join(list(difflib.unified_diff(
            a, b, fromfile="golden", tofile="extracted", lineterm="", n=1))[:24])
        if not detail:
            differing = sorted(k for k in set(list(got) + list(want))
                               if got.get(k) != want.get(k))
            detail = "row text is identical but these differ: %s" % ", ".join(differing)
        bad(name, detail)


# ---------------------------------------------------------------- properties

def test_properties():
    blueprint = json.load(open(os.path.join(ROOT, "data", "blueprint.json")))
    for path in sorted(glob.glob(os.path.join(FIXTURES, "itemmap_*.golden.json"))):
        test_id = re.search(r"itemmap_(g\d-\d{4})\.golden", path).group(1)
        pdf = source_for(test_id)
        if pdf is None:
            skip("properties %s" % test_id, "source PDF not on disk")
            continue
        payload, err = extract(pdf)
        if payload is None:
            bad("properties %s" % test_id, err)
            continue
        for name, detail in properties_of(payload, blueprint):
            if detail:
                bad("%s %s" % (name, test_id), detail)
            else:
                ok("%s %s" % (name, test_id))


def properties_of(payload, blueprint):
    """[(property name, failure detail or None)] -- no golden consulted."""
    meta, items = payload["meta"], payload["items"]
    test_id, grade = meta["testId"], meta["grade"]
    results = []

    mc = [i for i in items if i["type"] == "Multiple Choice"]
    cr = [i for i in items if i["type"] == "Constructed Response"]

    bad_keys = [i["item"] for i in mc if i["key"] not in ("A", "B", "C", "D")]
    results.append(("keys are A-D", "items %s" % bad_keys if bad_keys else None))

    # A shifted Key column reads as a constant. This is the single most
    # important property in the suite.
    detail = None
    if mc:
        counts = {}
        for i in mc:
            counts[i["key"]] = counts.get(i["key"], 0) + 1
        top, n = max(counts.items(), key=lambda kv: kv[1])
        if n / float(len(mc)) > 0.6:
            detail = "%d of %d keys are %r" % (n, len(mc), top)
    results.append(("key spread is not degenerate", detail))

    numbers = [i["item"] for i in items]
    results.append(("items strictly increasing",
                    None if numbers == sorted(set(numbers)) else str(numbers)))

    results.append(("multiple-choice items are 1 credit",
                    None if all(i["credits"] == 1 for i in mc)
                    else str([i["item"] for i in mc if i["credits"] != 1])))
    results.append(("constructed-response credits in 1-3",
                    None if all(i["credits"] in (1, 2, 3) for i in cr)
                    else str([i["item"] for i in cr if i["credits"] not in (1, 2, 3)])))
    results.append(("every constructed response has average points earned",
                    None if all(i["avgPointsEarned"] is not None for i in cr)
                    else str([i["item"] for i in cr if i["avgPointsEarned"] is None])))
    results.append(("average points never exceeds credits",
                    None if all(i["avgPointsEarned"] <= i["credits"] for i in cr)
                    else str([i["item"] for i in cr if i["avgPointsEarned"] > i["credits"]])))
    results.append(("every P-value in (0,1]",
                    None if all(0 < i["pValue"] <= 1 for i in items)
                    else str([(i["item"], i["pValue"]) for i in items
                              if not 0 < i["pValue"] <= 1])))

    spec = blueprint["tests"].get(test_id)
    if spec and spec.get("expectedReleasedItems") is not None:
        mismatch = [f for f, got in
                    (("expectedReleasedItems", meta["releasedItems"]),
                     ("expectedMultipleChoice", meta["multipleChoice"]),
                     ("expectedConstructedResponse", meta["constructedResponse"]),
                     ("expectedCreditsReleased", meta["creditsReleased"]))
                    if spec.get(f) != got]
        results.append(("counts match the blueprint",
                        None if not mismatch else
                        "; ".join("%s: blueprint %s, extracted %s"
                                  % (f, spec.get(f), meta[f[8].lower() + f[9:]] if False else "-")
                                  for f in mismatch) or str(mismatch)))

        grade_bp = blueprint["grades"][str(grade)]
        wrong_session = []
        for i in items:
            for number, session in grade_bp["sessions"].items():
                lo, hi = session["items"]
                if lo <= i["item"] <= hi and i["session"] != int(number):
                    wrong_session.append((i["item"], i["session"], int(number)))
        results.append(("sessions match the blueprint's item ranges",
                        None if not wrong_session else str(wrong_session)))

        lo, hi = grade_bp["itemNumbering"]["multipleChoice"]
        wrong_type = [(i["item"], i["type"]) for i in items
                      if (lo <= i["item"] <= hi) != (i["type"] == "Multiple Choice")]
        results.append(("type matches the blueprint's numbering",
                        None if not wrong_type else str(wrong_type)))
    else:
        results.append(("counts match the blueprint", None))

    return results


# ----------------------------------------------- the test that must be able to fail

def test_left_edge_assignment_breaks_it():
    """Re-run one extraction with left-edge x instead of centre x, and require
    the property tests to fail.

    Cluster and Subscore are centre-aligned, so the same column's words start at
    different x on different rows. If left-edge assignment still satisfies every
    property, the properties are not testing column assignment and this suite
    gives false confidence."""
    name = "left-edge x assignment is caught by the property tests"
    pdf = source_for("g7-2026")
    if pdf is None:
        skip(name, "source PDF not on disk")
        return

    src = open(EXTRACTOR).read()
    broken = src.replace(
        'return " ".join(t for cx, x0, x1, t in row_cells if lo <= cx < hi).strip()',
        'return " ".join(t for cx, x0, x1, t in row_cells if lo <= x0 < hi).strip()')
    if broken == src:
        bad(name, "could not find the centre-x assignment line to break -- this test "
                  "has silently stopped testing anything, fix it before trusting the suite")
        return

    tmp = os.path.join(ROOT, "provenance", "_left_edge_probe.py")
    try:
        with open(tmp, "w") as fh:
            fh.write(broken)
        out = subprocess.run([sys.executable, tmp, pdf, "--stdout"],
                             capture_output=True, text=True)
        if out.returncode != 0:
            ok(name + " (it fails outright)")
            return
        blueprint = json.load(open(os.path.join(ROOT, "data", "blueprint.json")))
        failures = [n for n, d in properties_of(json.loads(out.stdout), blueprint) if d]
        if failures:
            ok(name + " (properties that caught it: %s)" % ", ".join(failures[:3]))
        else:
            bad(name, "left-edge assignment passed every property test. The properties are "
                      "not testing column assignment, so the suite cannot catch the most "
                      "likely regression in this extractor.")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------- known data defects

def test_known_defects():
    """The two real NYSED defects must stay handled, and stay visible."""
    pdf = source_for("g8-2024")
    name = "the 2024 grade 8 duplicated NY- prefix is repaired and recorded"
    if pdf is None:
        skip(name, "source PDF not on disk")
    else:
        payload, err = extract(pdf)
        if payload is None:
            bad(name, err)
        else:
            codes = [i["standard"] for i in payload["items"]]
            repairs = payload["meta"]["repairs"]
            if "NY-8.EE.6" not in codes:
                bad(name, "NY-8.EE.6 is missing from the extraction entirely")
            elif any("NY-NY" in c for c in codes):
                bad(name, "a doubled prefix survived: %s"
                    % [c for c in codes if "NY-NY" in c])
            elif not repairs:
                bad(name, "the code was repaired but the repair was not recorded, so the "
                          "source defect becomes invisible")
            else:
                ok(name)

    name = "no extracted code carries stray whitespace"
    problems = []
    for path in sorted(glob.glob(os.path.join(FIXTURES, "itemmap_*.golden.json"))):
        golden = json.load(open(path))
        for row in golden["rows"]:
            if row["standard"] != row["standard"].strip():
                problems.append((golden["testId"], row["item"], repr(row["standard"])))
    if problems:
        bad(name, str(problems))
    else:
        ok(name)


# -------------------------------------------------------------- CCLS coverage

def test_ccls_coverage():
    """The 2022 extractions are the only coverage for three things."""
    for test_id in ("g6-2022", "g7-2022"):
        name = "CCLS-era layout %s" % test_id
        path = os.path.join(FIXTURES, "itemmap_%s.golden.json" % test_id)
        if not os.path.exists(path):
            skip(name, "no golden recorded")
            continue
        g = json.load(open(path))
        problems = []
        if len(g["mapPages"]) < 2:
            problems.append("expected a map spanning two pages, got %s" % g["mapPages"])
        if "Subscore" in g["columns"] or "Secondary" in g["columns"]:
            problems.append("expected no Subscore/Secondary columns, got %s" % g["columns"])
        if g["standardsEra"] != "ccls":
            problems.append("expected era 'ccls', got %r" % g["standardsEra"])
        if any(r["standard"].startswith("NY-") for r in g["rows"]):
            problems.append("a CCLS extraction produced NY- codes")
        bad(name, "; ".join(problems)) if problems else ok(name)


def main():
    ap = argparse.ArgumentParser(description="Test the item-map extractor.")
    ap.add_argument("--update", action="store_true",
                    help="re-record the golden files from the current extractor")
    args = ap.parse_args()

    test_goldens(args.update)
    if not args.update:
        test_properties()
        test_left_edge_assignment_breaks_it()
        test_known_defects()
        test_ccls_coverage()

    for name, why in SKIP:
        print("SKIP  %s -- %s" % (name, why))
    for name, detail in FAIL:
        print("FAIL  %s\n      %s" % (name, detail.replace("\n", "\n      ")))
    print("\n%d passed, %d failed, %d skipped" % (len(PASS), len(FAIL), len(SKIP)))
    if FAIL:
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
