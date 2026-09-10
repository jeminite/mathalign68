#!/usr/bin/env python3
"""
Assemble data/items.json from the per-test extractions.

  python3 tools/build_items.py
  python3 tools/build_items.py --check     # build in memory and compare, write nothing

Reads  : provenance/itemmap_<testId>.json   (one per test)
         provenance/pagemap_<testId>.json   (one per test, optional)
         provenance/sources.json
         data/blueprint.json
         data/standards.json
Writes : data/items.json

data/items.json is GENERATED and must never be hand-edited. `--check` is what
preflight uses: it rebuilds from provenance/ and fails if the file on disk
differs, so a hand edit cannot survive unnoticed. If a value is wrong, fix the
extractor or fix data/blueprint.json.

The CCLS-era extractions (2022) are deliberately skipped. They exist as
regression coverage for the two-page map layout, not as published data -- their
codes are a different family with no crosswalk.
"""

import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROV = os.path.join(ROOT, "provenance")
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "items.json")

DOMAIN_RE = re.compile(r"^NY-(\d)\.([A-Z]{1,3})\.")


def load(path):
    with open(path) as fh:
        return json.load(fh)


def die(msg):
    sys.exit("build_items: " + msg)


def session_of(grade_bp, item):
    for number, spec in grade_bp["sessions"].items():
        lo, hi = spec["items"]
        if lo <= item <= hi:
            return int(number)
    return None


def expected_type(grade_bp, item):
    lo, hi = grade_bp["itemNumbering"]["multipleChoice"]
    return "Multiple Choice" if lo <= item <= hi else "Constructed Response"


def unreleased_credit_plan(grade_bp, released_items, released_credits_by_item):
    """Credits for each withheld constructed-response item.

    The blueprint says how many CR items of each credit value a test has; the
    released ones are known, so the rest is arithmetic. This matters because a
    teacher's results export can cover all 48 items even though only 42 are
    published, and the analyzer has to score the withheld ones to get a total
    right."""
    cr_lo, cr_hi = grade_bp["itemNumbering"]["constructedResponse"]
    planned = []
    for number, spec in grade_bp["sessions"].items():
        for credits in (1, 2, 3):
            planned += [credits] * spec["constructedResponse%dCredit" % credits]
    planned.sort()

    seen = sorted(released_credits_by_item[i] for i in released_items
                  if cr_lo <= i <= cr_hi)
    remaining = list(planned)
    for c in seen:
        if c in remaining:
            remaining.remove(c)
        else:
            die("a released constructed-response item carries %d credits, which the "
                "blueprint does not allow for this grade" % c)
    # Withheld CR items are assigned the remaining credit values in item order.
    # NYSED does not publish which is which, so this is an inference and is
    # labelled as one on every record.
    return sorted(remaining)


def build():
    blueprint = load(os.path.join(DATA, "blueprint.json"))
    standards = load(os.path.join(DATA, "standards.json"))["standards"]
    sources = load(os.path.join(PROV, "sources.json"))["files"]

    url_by_test = {}
    for rec in sources.values():
        if rec.get("kind") == "released" and rec.get("grade"):
            url_by_test["g%d-%d" % (rec["grade"], rec["year"])] = rec["url"]
    scoring_by_test = {}
    for rec in sources.values():
        if rec.get("kind") == "scoring" and rec.get("grade"):
            scoring_by_test["g%d-%d" % (rec["grade"], rec["year"])] = rec.get("url")

    tests, items, unreleased = [], [], []

    for test_id in sorted(blueprint["tests"]):
        spec = blueprint["tests"][test_id]
        grade, year = spec["grade"], spec["year"]
        grade_bp = blueprint["grades"][str(grade)]

        map_path = os.path.join(PROV, "itemmap_%s.json" % test_id)
        if not os.path.exists(map_path):
            die("missing %s -- run tools/extract_item_map.py for that test"
                % os.path.relpath(map_path, ROOT))
        extraction = load(map_path)
        meta, rows = extraction["meta"], extraction["items"]

        if meta["standardsEra"] != "nextgen":
            die("%s is a %s extraction; only the Next Generation era is published"
                % (test_id, meta["standardsEra"]))

        # The blueprint's count is the hand-confirmed figure. Disagreement means
        # the extractor changed behaviour, and that has to be noticed here
        # rather than shipped.
        if spec["expectedReleasedItems"] is None:
            die("%s has no expectedReleasedItems in data/blueprint.json. Record the "
                "extractor's count there and confirm it against the PDF." % test_id)
        for field, got in (("expectedReleasedItems", meta["releasedItems"]),
                           ("expectedMultipleChoice", meta["multipleChoice"]),
                           ("expectedConstructedResponse", meta["constructedResponse"]),
                           ("expectedCreditsReleased", meta["creditsReleased"])):
            if spec.get(field) != got:
                die("%s: blueprint says %s=%s, the extraction has %s"
                    % (test_id, field, spec.get(field), got))

        page_path = os.path.join(PROV, "pagemap_%s.json" % test_id)
        pagemap = load(page_path)["items"] if os.path.exists(page_path) else {}

        released_numbers = [r["item"] for r in rows]
        credits_by_item = {r["item"]: r["credits"] for r in rows}
        base_url = url_by_test.get(test_id)

        for row in rows:
            item = row["item"]
            code = row["standard"]
            dm = DOMAIN_RE.match(code)
            if not dm:
                die("%s item %d: code %r does not parse" % (test_id, item, code))
            code_grade, domain = int(dm.group(1)), dm.group(2)

            reg = standards.get(code)
            if reg is None:
                die("%s item %d: standard %s is not in data/standards.json"
                    % (test_id, item, code))
            if grade not in reg["assessedOnGrades"]:
                die("%s item %d cites %s, which the registry says is assessed on grade(s) %s"
                    % (test_id, item, code, reg["assessedOnGrades"]))

            # Two independent reads on post-test status: the code's own grade
            # digit, and the educator guide's tables. They must agree.
            by_digit = code_grade != grade
            if by_digit != reg["postTest"]:
                die("%s item %d: %s has a grade-%d code on a grade-%d test but the "
                    "registry says postTest=%s" % (test_id, item, code, code_grade,
                                                   grade, reg["postTest"]))

            blueprint_session = session_of(grade_bp, item)
            if row["session"] != blueprint_session:
                die("%s item %d: extracted session %s, blueprint says %s"
                    % (test_id, item, row["session"], blueprint_session))
            want_type = expected_type(grade_bp, item)
            if row["type"] != want_type:
                die("%s item %d: type %r but the blueprint's numbering puts it in %r"
                    % (test_id, item, row["type"], want_type))

            page = pagemap.get(str(item), {})
            pdf_page = page.get("pdfPage")

            items.append({
                "id": "%s-%03d" % (test_id, item),
                "testId": test_id,
                "grade": grade,
                "year": year,
                "item": item,
                "session": row["session"],
                "type": row["type"],
                "key": row["key"],
                "credits": row["credits"],
                "standard": code,
                "standardGrade": code_grade,
                "domain": domain,
                "domainLabel": row["domainLabel"],
                "subscore": row["subscore"],
                "secondaryStandards": row["secondaryStandards"],
                "pValue": row["pValue"],
                "avgPointsEarned": row["avgPointsEarned"],
                "postTest": reg["postTest"],
                "postTestFromGrade": code_grade if by_digit else None,
                "released": True,
                "pdfPage": pdf_page,
                "printedPage": page.get("printedPage"),
                "sourceUrl": ("%s#page=%d" % (base_url, pdf_page)
                              if base_url and pdf_page else base_url),
                "extraction": row["extraction"],
            })

        withheld = [n for n in range(1, grade_bp["designedItems"] + 1)
                    if n not in credits_by_item]
        cr_credits = unreleased_credit_plan(grade_bp, released_numbers, credits_by_item)
        cr_lo, cr_hi = grade_bp["itemNumbering"]["constructedResponse"]
        cr_withheld = [n for n in withheld if cr_lo <= n <= cr_hi]
        if len(cr_credits) != len(cr_withheld):
            die("%s: %d withheld constructed-response items but %d credit values left over"
                % (test_id, len(cr_withheld), len(cr_credits)))

        for n in withheld:
            kind = expected_type(grade_bp, n)
            if kind == "Multiple Choice":
                credits, basis = 1, "every multiple-choice item is worth 1 credit"
            else:
                credits = cr_credits[cr_withheld.index(n)]
                basis = ("inferred: the blueprint's credit mix for this grade minus the "
                         "released constructed-response items, assigned in item order. "
                         "NYSED does not publish which withheld item carries which credit "
                         "value, so this is the one inferred field in the dataset.")
            unreleased.append({
                "testId": test_id, "item": n, "session": session_of(grade_bp, n),
                "inferredType": kind, "inferredCredits": credits, "basis": basis,
            })

        tests.append({
            "testId": test_id,
            "grade": grade,
            "year": year,
            "label": "Grade %d, %d" % (grade, year),
            "standardsEra": "nextgen",
            "releasedItemsUrl": base_url,
            "scoringMaterialsUrl": scoring_by_test.get(test_id),
            "pdfPageCount": meta["pdfPageCount"],
            "mapPages": meta["mapPages"],
            "designedItems": grade_bp["designedItems"],
            "designedCredits": grade_bp["totalCredits"],
            "releasedItems": meta["releasedItems"],
            "releasedCredits": meta["creditsReleased"],
            "releasedMultipleChoice": meta["multipleChoice"],
            "releasedConstructedResponse": meta["constructedResponse"],
            "withheldItems": withheld,
            "itemsWithPageLink": sum(1 for i in items
                                     if i["testId"] == test_id and i["pdfPage"]),
            "repairs": meta["repairs"],
            "sessions": {n: {"items": s["items"], "calculator": s["calculator"]}
                         for n, s in grade_bp["sessions"].items()},
        })

    items.sort(key=lambda i: (i["grade"], i["year"], i["item"]))
    unreleased.sort(key=lambda u: (u["testId"], u["item"]))

    return {
        "meta": {
            "schemaVersion": "1.0",
            "generatedBy": "tools/build_items.py",
            "generated": datetime.date.today().isoformat(),
            "note": "GENERATED. Do not hand-edit -- preflight rebuilds this from "
                    "provenance/ and fails if it differs. Fix the extractor or "
                    "data/blueprint.json instead.",
            "standardsEra": "nextgen",
            "grades": sorted({t["grade"] for t in tests}),
            "years": sorted({t["year"] for t in tests}),
            "tests": len(tests),
            "releasedItems": len(items),
            "releasedCredits": sum(i["credits"] for i in items),
            "itemsWithPageLink": sum(1 for i in items if i["pdfPage"]),
            "withheldItems": len(unreleased),
            "postTestItems": sum(1 for i in items if i["postTest"]),
        },
        "tests": tests,
        "items": items,
        "unreleased": unreleased,
    }


def main():
    ap = argparse.ArgumentParser(description="Assemble data/items.json.")
    ap.add_argument("--check", action="store_true",
                    help="rebuild and compare against the file on disk; write nothing")
    args = ap.parse_args()

    payload = build()
    text = json.dumps(payload, indent=2) + "\n"

    if args.check:
        if not os.path.exists(OUT):
            sys.exit("data/items.json does not exist; run tools/build_items.py")
        on_disk = open(OUT).read()
        # `generated` is a date and would differ on any later day.
        strip = lambda s: re.sub(r'"generated": "[^"]*"', '"generated": "-"', s)
        if strip(on_disk) != strip(text):
            sys.exit("data/items.json does not match a fresh build from provenance/.\n"
                     "It is a generated file -- re-run tools/build_items.py rather than "
                     "editing it, or fix the extractor if the new build is wrong.")
        print("data/items.json matches a fresh build from provenance/")
        return

    with open(OUT, "w") as fh:
        fh.write(text)
    m = payload["meta"]
    print("wrote data/items.json")
    print("  %d tests, grades %s, %d-%d"
          % (m["tests"], m["grades"], m["years"][0], m["years"][-1]))
    print("  %d released items carrying %d credits; %d have a page link; %d post-test"
          % (m["releasedItems"], m["releasedCredits"], m["itemsWithPageLink"],
             m["postTestItems"]))
    print("  %d withheld items with inferred type and credits" % m["withheldItems"])


if __name__ == "__main__":
    main()
